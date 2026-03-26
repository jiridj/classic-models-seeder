"""Main CLI entry point for Classic Models Seeder."""

import click
import sys
from pathlib import Path
from typing import Optional

from cmcli import __version__
from cmcli.utils.logging import setup_logging, get_logger
from cmcli.config import get_config


# Global context object to share state between commands
class Context:
    """CLI context object."""
    
    def __init__(self):
        self.verbose = False
        self.quiet = False
        self.config = None
        self.logger = None


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.group()
@click.version_option(version=__version__, prog_name="cmcli")
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output (DEBUG level)",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Suppress all output except errors",
)
@click.pass_context
def cli(ctx, verbose: bool, quiet: bool):
    """Classic Models CLI - Seed applications with Classic Models demo data.
    
    This tool helps you populate various applications (CRM, ERP, etc.) with
    the Classic Models demo dataset for integration demonstrations.
    """
    # Initialize context
    ctx.obj = Context()
    ctx.obj.verbose = verbose
    ctx.obj.quiet = quiet
    
    # Setup logging
    ctx.obj.logger = setup_logging(verbose=verbose, quiet=quiet)
    
    # Load configuration (will be done lazily when needed)
    try:
        ctx.obj.config = get_config()
    except Exception as e:
        if not quiet:
            click.echo(f"Warning: Could not load configuration: {e}", err=True)


# Import and register command groups
from cmcli.commands.update import update
from cmcli.commands.hubspot import hubspot
from cmcli.commands.salesforce import salesforce

cli.add_command(update)
cli.add_command(hubspot)
cli.add_command(salesforce)


if __name__ == "__main__":
    cli()

# Made with Bob
