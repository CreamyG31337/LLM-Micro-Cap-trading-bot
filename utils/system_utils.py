"""System utilities for the trading system."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

from display.console_output import print_error, print_warning

logger = logging.getLogger(__name__)


class InitializationError(Exception):
    """Exception raised during system initialization."""
    pass


def setup_error_handlers() -> None:
    """Setup global error handlers for uncaught exceptions."""
    def handle_exception(exc_type, exc_value, exc_traceback):
        """Handle uncaught exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Handle Ctrl+C gracefully
            print_warning("\nOperation cancelled by user")
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the exception
        logger.critical(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Display user-friendly error message
        print_error("An unexpected error occurred. Please check the log file for details.")
        print_error(f"Error: {exc_value}")
        
        # Call the default handler
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    
    # Set the exception handler
    sys.excepthook = handle_exception


def validate_system_requirements() -> None:
    """Validate system requirements and environment."""
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            raise InitializationError(
                f"Python 3.8+ required, found {sys.version_info.major}.{sys.version_info.minor}"
            )
        
        # Check for required packages
        required_packages = ['pandas', 'numpy', 'yfinance']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            raise InitializationError(
                f"Required packages missing: {', '.join(missing_packages)}. "
                "Please install with: pip install -r requirements.txt"
            )
        
        logger.info("System requirements validation passed")
        
    except Exception as e:
        logger.error(f"System requirements validation failed: {e}")
        raise


def log_system_info(version: str = "1.0.0") -> None:
    """Log system information for debugging.
    
    Args:
        version: Version string to log
    """
    import platform
    
    logger.info(f"Trading System {version} starting up")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {platform.platform()}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Script path: {Path(__file__).absolute()}")