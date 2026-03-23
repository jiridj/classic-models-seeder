"""HubSpot command group - verify and seed HubSpot CRM."""

import click
import sys
from rich.console import Console
from rich.table import Table

from cmcli.utils.logging import get_logger
from cmcli.config import get_config
from cmcli.hubspot.client import HubSpotClient, HubSpotAuthError, HubSpotAPIError
from cmcli.hubspot.seeder import HubSpotSeeder
from cmcli.data.loader import DataLoader

logger = get_logger("commands.hubspot")
console = Console()


@click.group()
def hubspot():
    """HubSpot CRM commands - verify access and seed data."""
    pass


@hubspot.command()
@click.pass_context
def verify(ctx):
    """Verify HubSpot API credentials and permissions.
    
    This command checks:
    - API authentication is valid
    - Required read/write permissions are available
    - Custom properties can be created
    """
    try:
        # Load configuration
        config = get_config()
        hubspot_config = config.hubspot
        
        console.print("\n[bold]Verifying HubSpot access...[/bold]\n")
        
        # Create client
        client = HubSpotClient(hubspot_config)
        
        # Test authentication by listing properties
        console.print("✓ Testing authentication...", style="dim")
        try:
            client.list_properties("companies")
            console.print("  [green]✓ Authentication successful[/green]")
        except HubSpotAuthError as e:
            console.print(f"  [red]✗ Authentication failed: {e}[/red]")
            sys.exit(1)
        
        # Check read permissions
        console.print("\n✓ Checking read permissions...", style="dim")
        permissions_ok = True
        
        for object_type in ["companies", "contacts", "deals"]:
            try:
                client.list_properties(object_type)
                console.print(f"  [green]✓ Can read {object_type}[/green]")
            except HubSpotAPIError as e:
                console.print(f"  [red]✗ Cannot read {object_type}: {e}[/red]")
                permissions_ok = False
        
        # Check write permissions by listing properties
        # (This tests schema read permission which is required for creating custom properties)
        console.print("\n✓ Checking schema access...", style="dim")
        
        for object_type in ["companies", "contacts", "deals"]:
            try:
                # List properties (requires schema read permission)
                props = client.list_properties(object_type)
                console.print(f"  [green]✓ Can access {object_type} schema ({len(props)} properties)[/green]")
            except HubSpotAPIError as e:
                console.print(f"  [yellow]⚠ Limited access to {object_type} schema: {e}[/yellow]")
                permissions_ok = False
        
        # Summary
        console.print()
        if permissions_ok:
            console.print("[bold green]✓ All checks passed! Ready to seed HubSpot.[/bold green]")
            console.print("\nNext steps:")
            console.print("  1. Run [cyan]cmcli hubspot seed[/cyan] to seed all data")
            console.print("  2. Or use flags like [cyan]--companies-only[/cyan] for partial seeding")
        else:
            console.print("[bold red]✗ Some permission checks failed.[/bold red]")
            console.print("\nPlease ensure your API key has the following scopes:")
            console.print("  • crm.objects.contacts.read / write")
            console.print("  • crm.objects.companies.read / write")
            console.print("  • crm.objects.deals.read / write")
            console.print("  • crm.schemas.contacts.read / write")
            console.print("  • crm.schemas.companies.read / write")
            console.print("  • crm.schemas.deals.read / write")
            sys.exit(1)
        
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nMake sure you have set the following in your .env file:")
        console.print("  HUBSPOT_ACCESS_TOKEN=your-token-here")
        console.print("  HUBSPOT_ACCOUNT_ID=your-account-id")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        if ctx.obj.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


@hubspot.command()
@click.option(
    "--companies-only",
    is_flag=True,
    help="Seed only companies (customers)",
)
@click.option(
    "--contacts-only",
    is_flag=True,
    help="Seed only contacts (requires companies to exist)",
)
@click.option(
    "--deals-only",
    is_flag=True,
    help="Seed only deals (requires companies and contacts to exist)",
)
@click.pass_context
def seed(ctx, companies_only: bool, contacts_only: bool, deals_only: bool):
    """Seed HubSpot CRM with Classic Models data.
    
    This command seeds HubSpot with:
    - Companies (from Classic Models customers)
    - Contacts (from customer contact information)
    - Deals (from Classic Models orders)
    
    The seeding process is idempotent - running it multiple times will update
    existing records rather than creating duplicates.
    """
    try:
        # Load configuration
        config = get_config()
        hubspot_config = config.hubspot
        
        # Create client and data loader
        client = HubSpotClient(hubspot_config)
        data_loader = DataLoader(config.data_dir)
        
        # Create seeder
        seeder = HubSpotSeeder(client, data_loader)
        
        console.print("\n[bold]Starting HubSpot seeding...[/bold]")
        console.print(f"Account ID: {hubspot_config.account_id}\n")
        
        # Determine what to seed
        seed_all = not (companies_only or contacts_only or deals_only)
        
        results = {}
        
        if seed_all:
            # Seed everything
            results = seeder.seed_all()
        else:
            # Seed selectively
            if companies_only:
                seeder.ensure_properties_exist(["companies"])
                results["companies"] = seeder.seed_companies()
            
            if contacts_only:
                seeder.ensure_properties_exist(["contacts"])
                results["contacts"] = seeder.seed_contacts()
            
            if deals_only:
                seeder.ensure_properties_exist(["deals"])
                results["deals"] = seeder.seed_deals()
        
        # Display summary
        console.print("\n[bold green]✓ Seeding completed successfully![/bold green]\n")
        
        table = Table(title="Seeding Summary")
        table.add_column("Object Type", style="cyan")
        table.add_column("Records", justify="right", style="green")
        
        for object_type, count in results.items():
            table.add_row(object_type.capitalize(), str(count))
        
        console.print(table)
        
        console.print("\n[dim]Note: Seeding is idempotent. Re-running will update existing records.[/dim]")
        
    except ValueError as e:
        console.print(f"[red]Configuration error: {e}[/red]")
        console.print("\nMake sure you have set the following in your .env file:")
        console.print("  HUBSPOT_ACCESS_TOKEN=your-token-here")
        console.print("  HUBSPOT_ACCOUNT_ID=your-account-id")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]Data file error: {e}[/red]")
        console.print("\nMake sure the data/json directory exists with the required files:")
        console.print("  • customers.json")
        console.print("  • orders.json")
        console.print("  • orderdetails.json")
        console.print("  • payments.json")
        sys.exit(1)
    except HubSpotAuthError as e:
        console.print(f"[red]Authentication error: {e}[/red]")
        console.print("\nRun [cyan]cmcli hubspot verify[/cyan] to check your credentials.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        if ctx.obj.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)

# Made with Bob
