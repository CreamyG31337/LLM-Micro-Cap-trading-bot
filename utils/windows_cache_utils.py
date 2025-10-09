"""Windows-specific cache utilities for handling file permissions and access denied errors.

This module provides Windows-specific utilities for cache management that handle
common Windows file permission issues like access denied errors.
"""

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def is_windows() -> bool:
    """Check if running on Windows."""
    return os.name == 'nt' or sys.platform.startswith('win')


def remove_readonly_attributes(path: Path) -> bool:
    """Remove read-only attributes from a file or directory on Windows.
    
    Args:
        path: Path to file or directory
        
    Returns:
        True if successful, False otherwise
    """
    if not is_windows():
        return True
        
    try:
        # Use attrib command to remove read-only attribute
        result = subprocess.run(
            ['attrib', '-R', str(path), '/S', '/D'],
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
        logger.warning(f"Failed to remove readonly attributes from {path}: {e}")
        return False


def force_delete_directory(path: Path) -> bool:
    """Force delete a directory on Windows, handling permission issues.
    
    Args:
        path: Directory path to delete
        
    Returns:
        True if successful, False otherwise
    """
    if not path.exists():
        return True
        
    try:
        # First, try to remove readonly attributes
        remove_readonly_attributes(path)
        
        # Try standard deletion first
        import shutil
        shutil.rmtree(path)
        return True
        
    except PermissionError:
        # If standard deletion fails, try Windows-specific methods
        try:
            # Method 1: Use rmdir with /s /q flags
            result = subprocess.run(
                ['rmdir', '/s', '/q', str(path)],
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )
            if result.returncode == 0:
                return True
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
            
        try:
            # Method 2: Use PowerShell Remove-Item with Force
            powershell_cmd = f'Remove-Item -Path "{path}" -Recurse -Force -ErrorAction SilentlyContinue'
            result = subprocess.run(
                ['powershell', '-Command', powershell_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            logger.error(f"Failed to force delete {path}: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error deleting {path}: {e}")
        return False


def force_delete_file(file_path: Path) -> bool:
    """Force delete a file on Windows, handling permission issues.
    
    Args:
        file_path: File path to delete
        
    Returns:
        True if successful, False otherwise
    """
    if not file_path.exists():
        return True
        
    try:
        # First, try to remove readonly attributes
        remove_readonly_attributes(file_path)
        
        # Try standard deletion
        file_path.unlink()
        return True
        
    except PermissionError:
        # If standard deletion fails, try Windows-specific methods
        try:
            # Method 1: Use del command with /f flag
            result = subprocess.run(
                ['del', '/f', str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                shell=True
            )
            if result.returncode == 0:
                return True
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
            
        try:
            # Method 2: Use PowerShell Remove-Item with Force
            powershell_cmd = f'Remove-Item -Path "{file_path}" -Force -ErrorAction SilentlyContinue'
            result = subprocess.run(
                ['powershell', '-Command', powershell_cmd],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
            
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, Exception) as e:
            logger.error(f"Failed to force delete {file_path}: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Unexpected error deleting {file_path}: {e}")
        return False


def clear_cache_directory_windows(cache_dir: Path) -> Tuple[bool, str]:
    """Clear a cache directory on Windows with proper permission handling.
    
    Args:
        cache_dir: Cache directory to clear
        
    Returns:
        Tuple of (success, message)
    """
    if not cache_dir.exists():
        return True, f"{cache_dir} does not exist"
        
    try:
        # Get list of files before deletion for reporting
        files = list(cache_dir.rglob("*"))
        file_count = len([f for f in files if f.is_file()])
        
        # Try to remove readonly attributes from all files first
        for file_path in files:
            if file_path.is_file():
                remove_readonly_attributes(file_path)
        
        # Try standard deletion first
        import shutil
        shutil.rmtree(cache_dir)
        
        # Recreate the directory
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        return True, f"Cleared {file_count} files from {cache_dir.name}"
        
    except PermissionError as e:
        # Try force deletion methods
        logger.warning(f"Permission denied for {cache_dir}, trying force deletion: {e}")
        
        try:
            # Get file count before force deletion
            files = list(cache_dir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            
            # Try force deletion
            if force_delete_directory(cache_dir):
                # Recreate the directory
                cache_dir.mkdir(parents=True, exist_ok=True)
                return True, f"Force cleared {file_count} files from {cache_dir.name}"
            else:
                return False, f"Failed to force delete {cache_dir}: Access denied"
                
        except Exception as force_error:
            return False, f"Force deletion failed for {cache_dir}: {force_error}"
            
    except Exception as e:
        return False, f"Failed to clear {cache_dir}: {e}"


def get_cache_file_permissions(cache_dir: Path) -> List[Tuple[str, str, str]]:
    """Get permission information for cache files.
    
    Args:
        cache_dir: Cache directory to check
        
    Returns:
        List of tuples (file_path, permissions, status)
    """
    permissions = []
    
    if not cache_dir.exists():
        return permissions
        
    try:
        for file_path in cache_dir.rglob("*"):
            if file_path.is_file():
                try:
                    # Get file stats
                    stat_info = file_path.stat()
                    mode = stat_info.st_mode
                    
                    # Check if file is readonly
                    readonly = not (mode & stat.S_IWRITE)
                    
                    # Get permission string
                    perm_str = oct(mode)[-3:] if hasattr(stat, 'filemode') else "unknown"
                    
                    # Get access status
                    try:
                        with open(file_path, 'r') as f:
                            f.read(1)  # Try to read
                        access_status = "readable"
                    except PermissionError:
                        access_status = "no_read_access"
                    except Exception:
                        access_status = "other_error"
                    
                    permissions.append((
                        str(file_path),
                        perm_str,
                        f"readonly={readonly}, access={access_status}"
                    ))
                    
                except Exception as e:
                    permissions.append((
                        str(file_path),
                        "error",
                        f"stat_error: {e}"
                    ))
                    
    except Exception as e:
        logger.error(f"Error checking permissions for {cache_dir}: {e}")
        
    return permissions


def diagnose_cache_permissions(cache_dir: Path) -> str:
    """Diagnose cache directory permission issues.
    
    Args:
        cache_dir: Cache directory to diagnose
        
    Returns:
        Diagnostic information string
    """
    if not cache_dir.exists():
        return f"Cache directory {cache_dir} does not exist"
        
    permissions = get_cache_file_permissions(cache_dir)
    
    if not permissions:
        return f"No files found in {cache_dir}"
        
    # Analyze permission issues
    readonly_files = [p for p in permissions if "readonly=True" in p[2]]
    no_access_files = [p for p in permissions if "no_read_access" in p[2]]
    error_files = [p for p in permissions if "error" in p[1]]
    
    diagnosis = f"Cache directory analysis for {cache_dir}:\n"
    diagnosis += f"Total files: {len(permissions)}\n"
    diagnosis += f"Read-only files: {len(readonly_files)}\n"
    diagnosis += f"No access files: {len(no_access_files)}\n"
    diagnosis += f"Error files: {len(error_files)}\n"
    
    if readonly_files:
        diagnosis += "\nRead-only files:\n"
        for file_path, perm, status in readonly_files[:5]:  # Show first 5
            diagnosis += f"  {Path(file_path).name}: {status}\n"
            
    if no_access_files:
        diagnosis += "\nNo access files:\n"
        for file_path, perm, status in no_access_files[:5]:  # Show first 5
            diagnosis += f"  {Path(file_path).name}: {status}\n"
            
    return diagnosis
