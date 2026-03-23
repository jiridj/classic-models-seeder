"""Logging configuration for Classic Models CLI."""

import logging
import sys
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler


def setup_logging(verbose: bool = False, quiet: bool = False) -> logging.Logger:
    """Configure logging for the CLI.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        quiet: Suppress all but ERROR messages
    
    Returns:
        Configured logger instance
    """
    # Determine log level
    if quiet:
        level = logging.ERROR
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                rich_tracebacks=True,
                tracebacks_show_locals=verbose,
            )
        ],
    )
    
    # Get logger for our package
    logger = logging.getLogger("cmcli")
    logger.setLevel(level)
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance.
    
    Args:
        name: Logger name. If None, returns root cmcli logger.
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"cmcli.{name}")
    return logging.getLogger("cmcli")

# Made with Bob
