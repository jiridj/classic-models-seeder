"""Update command - Update timestamps in Classic Models dataset."""

import click
import sys
from pathlib import Path

from cmcli.utils.logging import get_logger

logger = get_logger("commands.update")


@click.command()
@click.pass_context
def update(ctx):
    """Update timestamps in the Classic Models dataset to current dates.
    
    This command updates all date fields in the SQL and JSON data files
    to make the demo data current. Historical orders are mapped to the
    last 18 months, and future orders to the next 3 months.
    """
    try:
        # Import the existing timestamp updater
        script_dir = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(script_dir))
        
        from update_timestamps import TimestampUpdater
        
        # Get base path (project root)
        base_path = Path(__file__).parent.parent.parent
        
        logger.info("Starting timestamp update...")
        
        # Run the updater
        updater = TimestampUpdater(base_path)
        updater.run()
        
        logger.info("✓ Timestamp update completed successfully!")
        
    except ImportError as e:
        logger.error(f"Could not import timestamp updater: {e}")
        logger.error("Make sure scripts/update_timestamps.py exists")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error updating timestamps: {e}")
        if ctx.obj.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)

# Made with Bob
