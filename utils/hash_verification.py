"""Script integrity verification utilities.

This module provides timestamp-based integrity checking to ensure no Python files
have been modified since the trading script was launched, preventing mid-session
code changes that could compromise security.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional, Set
from datetime import datetime

from display.console_output import print_error, print_warning, print_info, print_success

logger = logging.getLogger(__name__)


class ScriptIntegrityError(Exception):
    """Exception raised when script integrity verification fails."""
    pass


# Global variable to store the launch time
_LAUNCH_TIME: Optional[float] = None


def initialize_launch_time() -> None:
    """Initialize the launch time for integrity checking.
    
    This should be called once when the script starts up.
    """
    global _LAUNCH_TIME
    _LAUNCH_TIME = datetime.now().timestamp()
    logger.info(f"Launch time initialized: {datetime.fromtimestamp(_LAUNCH_TIME)}")


def get_python_files(project_root: Path) -> Set[Path]:
    """Get all Python files in the project.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Set[Path]: Set of Python file paths
    """
    python_files = set()
    
    # Directories to include
    include_dirs = [
        'config', 'data', 'display', 'financial', 'market_data', 
        'portfolio', 'utils', 'debug', 'tests'
    ]
    
    # Files to include in root directory
    include_files = [
        'trading_script.py', 'run.py', 'simple_automation.py', 
        'prompt_generator.py', 'show_prompt.py', 'update_cash.py',
        'dual_currency.py', 'market_config.py', 'experiment_config.py'
    ]
    
    # Add root directory Python files
    for filename in include_files:
        file_path = project_root / filename
        if file_path.exists():
            python_files.add(file_path)
    
    # Add Python files from include directories
    for dir_name in include_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists() and dir_path.is_dir():
            for py_file in dir_path.rglob('*.py'):
                python_files.add(py_file)
    
    return python_files


def check_file_modification_times(project_root: Path) -> Optional[Path]:
    """Check if any Python files have been modified since launch.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        Optional[Path]: Path to the first modified file found, or None if none modified
    """
    if _LAUNCH_TIME is None:
        logger.warning("Launch time not initialized - skipping integrity check")
        return None
    
    python_files = get_python_files(project_root)
    modified_files = []
    
    for file_path in python_files:
        try:
            if file_path.exists():
                file_mtime = file_path.stat().st_mtime
                if file_mtime > _LAUNCH_TIME:
                    modified_files.append((file_path, file_mtime))
                    logger.warning(f"File modified since launch: {file_path} (mtime: {datetime.fromtimestamp(file_mtime)})")
        except Exception as e:
            logger.warning(f"Could not check modification time for {file_path}: {e}")
    
    if modified_files:
        # Return the most recently modified file
        most_recent = max(modified_files, key=lambda x: x[1])
        return most_recent[0]
    
    return None


def verify_script_integrity(project_root: Path) -> bool:
    """Verify that no Python files have been modified since launch.
    
    Args:
        project_root: Root directory of the project
        
    Returns:
        bool: True if no files have been modified, False otherwise
    """
    try:
        modified_file = check_file_modification_times(project_root)
        
        if modified_file:
            logger.error(f"Script integrity check failed: {modified_file} was modified after launch")
            return False
        
        logger.debug("Script integrity check passed - no files modified since launch")
        return True
        
    except Exception as e:
        logger.error(f"Script integrity check failed: {e}")
        return False


def require_script_integrity(project_root: Path) -> None:
    """Require script integrity verification before allowing sensitive operations.
    
    This function should be called before each sensitive operation to ensure
    no Python files have been modified since the script was launched.
    
    Args:
        project_root: Root directory of the project
        
    Raises:
        ScriptIntegrityError: If script integrity cannot be verified
    """
    try:
        if not verify_script_integrity(project_root):
            modified_file = check_file_modification_times(project_root)
            error_msg = f"Script integrity verification failed - files have been modified since launch"
            if modified_file:
                error_msg += f" (most recent: {modified_file.name})"
            
            print_error(error_msg)
            print_error("For security reasons, trading operations are disabled")
            print_error("Please restart the application to continue")
            raise ScriptIntegrityError(error_msg)
        
        logger.debug("Script integrity verified successfully")
        
    except ScriptIntegrityError:
        # Re-raise integrity errors
        raise
    except Exception as e:
        error_msg = f"Script integrity check failed: {e}"
        logger.error(error_msg)
        raise ScriptIntegrityError(error_msg) from e


def get_launch_time() -> Optional[datetime]:
    """Get the launch time as a datetime object.
    
    Returns:
        Optional[datetime]: Launch time, or None if not initialized
    """
    if _LAUNCH_TIME is None:
        return None
    return datetime.fromtimestamp(_LAUNCH_TIME)


def get_launch_time_string() -> str:
    """Get the launch time as a formatted string.
    
    Returns:
        str: Formatted launch time string
    """
    launch_time = get_launch_time()
    if launch_time is None:
        return "Not initialized"
    return launch_time.strftime("%Y-%m-%d %H:%M:%S")