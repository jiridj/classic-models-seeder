"""Salesforce CRM commands (MVP version)."""

import click
import sys

from cmcli.config import get_config
from cmcli.salesforce.auth import SalesforceAuth, SalesforceAuthError
from cmcli.salesforce.client import SalesforceClient
from cmcli.salesforce.seeder import SalesforceSeeder
from cmcli.data.loader import DataLoader
from cmcli.utils.logging import get_logger

logger = get_logger("commands.salesforce")


@click.group()
def salesforce():
    """Salesforce CRM commands."""
    pass


@salesforce.command()
@click.pass_context
def verify(ctx):
    """Verify Salesforce credentials and permissions."""
    try:
        click.echo("Verifying Salesforce access...")
        click.echo("Using Username-Password OAuth flow...")
        
        # Load config
        config = get_config()
        sf_config = config.salesforce
        
        # Create auth and client
        auth = SalesforceAuth(sf_config)
        client = SalesforceClient(auth)
        
        # Test authentication
        if auth.validate_token():
            click.echo("✓ Authentication successful")
            click.echo(f"  Instance URL: {auth.get_instance_url()}")
        else:
            click.echo("✗ Authentication failed", err=True)
            sys.exit(1)
        
        # Test API access
        try:
            # Try to describe Account object
            account_desc = client.describe_object("Account")
            click.echo("✓ API access confirmed")
            click.echo(f"  Can access Account object")
        except Exception as e:
            click.echo(f"✗ API access failed: {e}", err=True)
            sys.exit(1)
        
        # Show API usage
        usage = client.get_api_usage()
        if usage['calls_limit'] > 0:
            click.echo(f"\nAPI Usage:")
            click.echo(f"  Daily limit: {usage['calls_limit']}")
            click.echo(f"  Remaining: {usage['calls_remaining']}")
            click.echo(f"  Used: {usage['percentage_used']:.1f}%")
        
        click.echo("\n✓ Salesforce verification complete!")
        
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except SalesforceAuthError as e:
        click.echo(f"Authentication error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if ctx.obj.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


@salesforce.command(name='setup-fields')
@click.pass_context
def setup_fields(ctx):
    """Create custom fields in Salesforce for Classic Models integration."""
    try:
        click.echo("Setting up custom fields in Salesforce...")
        click.echo("Using Username-Password OAuth flow...")
        
        # Load config
        config = get_config()
        sf_config = config.salesforce
        
        # Create auth and client
        auth = SalesforceAuth(sf_config)
        client = SalesforceClient(auth)
        
        # Import field definitions
        from cmcli.salesforce.fields import get_all_custom_fields
        
        all_fields = get_all_custom_fields()
        
        click.echo("\nCreating custom fields...")
        
        for sobject, fields in all_fields.items():
            click.echo(f"\n{sobject}:")
            for field in fields:
                field_name = field['fullName']
                try:
                    # Check if field already exists
                    desc = client.describe_object(sobject)
                    existing_fields = [f['name'] for f in desc['fields']]
                    
                    if field_name in existing_fields:
                        click.echo(f"  ✓ {field_name} (already exists)")
                    else:
                        # Note: Creating fields via API requires Metadata API
                        # For now, we'll just show what needs to be created
                        click.echo(f"  ⚠ {field_name} (needs manual creation)")
                        click.echo(f"    Type: {field['type']}")
                        click.echo(f"    Label: {field['label']}")
                        if field.get('externalId'):
                            click.echo(f"    External ID: Yes")
                        if field.get('unique'):
                            click.echo(f"    Unique: Yes")
                except Exception as e:
                    click.echo(f"  ✗ Error checking {field_name}: {e}", err=True)
        
        click.echo("\n" + "="*60)
        click.echo("IMPORTANT: Custom fields must be created manually")
        click.echo("="*60)
        click.echo("\nTo create these fields in Salesforce:")
        click.echo("1. Go to Setup → Object Manager")
        click.echo("2. Select the object (Account, Contact, or Opportunity)")
        click.echo("3. Go to 'Fields & Relationships'")
        click.echo("4. Click 'New' and create each field with the specifications above")
        click.echo("\nFor detailed instructions, see: specs/setup/SALESFORCE.md")
        
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except SalesforceAuthError as e:
        click.echo(f"Authentication error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if ctx.obj.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


@salesforce.command()
@click.option(
    '--accounts-only',
    is_flag=True,
    help='Seed only accounts (customers)'
)
@click.option(
    '--contacts-only',
    is_flag=True,
    help='Seed only contacts (employees)'
)
@click.option(
    '--products-only',
    is_flag=True,
    help='Seed only products'
)
@click.option(
    '--opportunities-only',
    is_flag=True,
    help='Seed only opportunities (orders)'
)
@click.pass_context
def seed(ctx, accounts_only, contacts_only, products_only, opportunities_only):
    """Seed Salesforce with Classic Models data."""
    try:
        # Load config
        config = get_config()
        sf_config = config.salesforce
        
        # Create auth and client
        click.echo("Connecting to Salesforce...")
        click.echo("Using Username-Password OAuth flow...")
        auth = SalesforceAuth(sf_config)
        client = SalesforceClient(auth)
        
        # Create data loader and seeder
        data_loader = DataLoader(config.json_dir)
        seeder = SalesforceSeeder(client, data_loader)
        
        # Determine what to seed
        seed_all = not (accounts_only or contacts_only or products_only or opportunities_only)
        
        if seed_all:
            # Seed everything
            results = seeder.seed_all()
        else:
            # Seed specific objects
            results = {}
            
            if accounts_only:
                account_count, contact_count = seeder.seed_accounts()
                results['accounts'] = account_count
                results['contacts'] = contact_count
            
            if contacts_only:
                results['contacts'] = seeder.seed_contacts()
            
            if products_only:
                results['products'] = seeder.seed_products()
            
            if opportunities_only:
                results['opportunities'] = seeder.seed_opportunities()
        
        # Show API usage
        usage = client.get_api_usage()
        click.echo(f"\nAPI Usage:")
        click.echo(f"  Calls made: {usage['calls_made']}/{usage['calls_limit']}")
        click.echo(f"  Remaining: {usage['calls_remaining']}")
        
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        click.echo("\nMake sure you have set up your .env file with Salesforce credentials.", err=True)
        sys.exit(1)
    except SalesforceAuthError as e:
        click.echo(f"Authentication error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if ctx.obj.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


# Made with Bob