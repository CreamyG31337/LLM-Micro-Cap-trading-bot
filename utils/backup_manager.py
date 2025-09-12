"""Backup management utilities for the trading system.

This module provides backup and restore functionality that works with both CSV files
and future database backends. It supports timestamped backups, selective restoration,
and data export capabilities.
"""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import pandas as pd


logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup and restore operations for trading data.
    
    This class is designed to work with both CSV-based storage (current)
    and future database backends through a repository pattern.
    """
    
    def __init__(self, data_dir: Path, backup_dir: Optional[Path] = None):
        """Initialize the backup manager.
        
        Args:
            data_dir: Directory containing the data files to backup
            backup_dir: Directory to store backups. If None, uses data_dir/backups
        """
        self.data_dir = Path(data_dir)
        self.backup_dir = backup_dir or (self.data_dir / "backups")
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, backup_name: Optional[str] = None) -> str:
        """Create a timestamped backup of all trading data files.
        
        Args:
            backup_name: Optional custom name for the backup. If None, uses timestamp.
        
        Returns:
            str: The backup timestamp/name that was created
        
        Raises:
            BackupError: If backup creation fails
        """
        if backup_name is None:
            backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Files to backup (CSV-based storage)
        csv_files_to_backup = [
            "llm_trade_log.csv",
            "llm_portfolio_update.csv", 
            "fund_contributions.csv",
            "exchange_rates.csv"
        ]
        
        # JSON files to backup
        json_files_to_backup = [
            "cash_balances.json"
        ]
        
        backed_up_files = []
        
        # Backup CSV files
        for filename in csv_files_to_backup:
            source_file = self.data_dir / filename
            if source_file.exists():
                backup_file = self.backup_dir / f"{filename}.backup_{backup_name}"
                try:
                    shutil.copy2(source_file, backup_file)
                    backed_up_files.append(filename)
                except Exception as e:
                    logger.warning(f"Failed to backup {filename}: {e}")
        
        # Backup JSON files
        for filename in json_files_to_backup:
            source_file = self.data_dir / filename
            if source_file.exists():
                backup_file = self.backup_dir / f"{filename}.backup_{backup_name}"
                try:
                    shutil.copy2(source_file, backup_file)
                    backed_up_files.append(filename)
                except Exception as e:
                    logger.warning(f"Failed to backup {filename}: {e}")
        
        if backed_up_files:
            logger.info(f"Created backup '{backup_name}' with {len(backed_up_files)} files: {', '.join(backed_up_files)}")
        else:
            logger.warning("No files found to backup")
        
        return backup_name
    
    def restore_from_backup(self, backup_name: Optional[str] = None) -> bool:
        """Restore trading files from a specific backup.
        
        Args:
            backup_name: Specific backup name/timestamp to restore. If None, restores latest.
        
        Returns:
            bool: True if restore was successful, False otherwise
        """
        if backup_name is None:
            backup_name = self.get_latest_backup()
            if not backup_name:
                logger.error("No backups found to restore")
                return False
            logger.info(f"Using latest backup: {backup_name}")
        
        # Find backup files for this backup
        backup_files = list(self.backup_dir.glob(f"*.backup_{backup_name}"))
        if not backup_files:
            logger.error(f"No backup files found for backup: {backup_name}")
            return False
        
        # Restore files
        restored_files = []
        for backup_file in backup_files:
            original_name = backup_file.name.split(f".backup_{backup_name}")[0]
            target_file = self.data_dir / original_name
            try:
                shutil.copy2(backup_file, target_file)
                restored_files.append(original_name)
            except Exception as e:
                logger.error(f"Failed to restore {original_name}: {e}")
                return False
        
        if restored_files:
            logger.info(f"✅ Restored backup '{backup_name}' with {len(restored_files)} files: {', '.join(restored_files)}")
            return True
        else:
            logger.error("No files were restored")
            return False
    
    def list_backups(self) -> List[str]:
        """List available backup timestamps.
        
        Returns:
            List[str]: List of backup names/timestamps sorted by creation time (newest first)
        """
        if not self.backup_dir.exists():
            return []
        
        backup_files = list(self.backup_dir.glob("*.backup_*"))
        timestamps = set()
        for backup_file in backup_files:
            parts = backup_file.name.split(".backup_")
            if len(parts) >= 2:
                timestamp = parts[1]
                timestamps.add(timestamp)
        
        # Sort by creation time (newest first)
        try:
            timestamps = sorted(timestamps, 
                              key=lambda x: datetime.strptime(x, "%Y%m%d_%H%M%S"), 
                              reverse=True)
        except ValueError:
            # If timestamps don't match expected format, sort alphabetically
            timestamps = sorted(timestamps, reverse=True)
        
        return timestamps
    
    def get_latest_backup(self) -> Optional[str]:
        """Get the name of the most recent backup.
        
        Returns:
            Optional[str]: The name of the latest backup, or None if no backups exist
        """
        backups = self.list_backups()
        return backups[0] if backups else None
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a specific backup.
        
        Args:
            backup_name: The name/timestamp of the backup to delete
        
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        backup_files = list(self.backup_dir.glob(f"*.backup_{backup_name}"))
        if not backup_files:
            logger.warning(f"No backup files found for backup: {backup_name}")
            return False
        
        deleted_files = []
        for backup_file in backup_files:
            try:
                backup_file.unlink()
                deleted_files.append(backup_file.name)
            except Exception as e:
                logger.error(f"Failed to delete {backup_file.name}: {e}")
                return False
        
        logger.info(f"✅ Deleted backup '{backup_name}' ({len(deleted_files)} files)")
        return True
    
    def get_backup_info(self, backup_name: str) -> Dict[str, Any]:
        """Get information about a specific backup.
        
        Args:
            backup_name: The name/timestamp of the backup
        
        Returns:
            Dict[str, Any]: Information about the backup including files and sizes
        """
        backup_files = list(self.backup_dir.glob(f"*.backup_{backup_name}"))
        if not backup_files:
            return {"exists": False, "files": [], "total_size": 0}
        
        files_info = []
        total_size = 0
        
        for backup_file in backup_files:
            try:
                stat = backup_file.stat()
                original_name = backup_file.name.split(f".backup_{backup_name}")[0]
                files_info.append({
                    "original_name": original_name,
                    "backup_name": backup_file.name,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime)
                })
                total_size += stat.st_size
            except Exception as e:
                logger.warning(f"Could not get info for {backup_file.name}: {e}")
        
        return {
            "exists": True,
            "backup_name": backup_name,
            "files": files_info,
            "total_size": total_size,
            "file_count": len(files_info)
        }
    
    def export_to_csv(self, export_dir: Path, backup_name: Optional[str] = None) -> bool:
        """Export data to CSV format (useful for database-to-CSV migration).
        
        This method is designed to work with future database backends by
        accepting data through the repository pattern and exporting to CSV.
        
        Args:
            export_dir: Directory to export CSV files to
            backup_name: Specific backup to export, or None for current data
        
        Returns:
            bool: True if export was successful, False otherwise
        """
        export_dir = Path(export_dir)
        export_dir.mkdir(exist_ok=True)
        
        if backup_name:
            # Export from backup
            source_dir = self.backup_dir
            file_pattern = f"*.backup_{backup_name}"
        else:
            # Export current data
            source_dir = self.data_dir
            file_pattern = "*.csv"
        
        exported_files = []
        
        # Find and copy CSV files
        for source_file in source_dir.glob(file_pattern):
            if backup_name:
                # Remove backup suffix for export
                export_name = source_file.name.split(f".backup_{backup_name}")[0]
            else:
                export_name = source_file.name
            
            if export_name.endswith('.csv'):
                export_file = export_dir / export_name
                try:
                    shutil.copy2(source_file, export_file)
                    exported_files.append(export_name)
                except Exception as e:
                    logger.error(f"Failed to export {export_name}: {e}")
                    return False
        
        # Handle JSON files by converting to CSV if needed
        json_files = ["cash_balances.json"]
        for json_filename in json_files:
            if backup_name:
                source_file = source_dir / f"{json_filename}.backup_{backup_name}"
            else:
                source_file = source_dir / json_filename
            
            if source_file.exists():
                try:
                    with open(source_file, 'r') as f:
                        data = json.load(f)
                    
                    # Convert JSON to CSV format
                    csv_filename = json_filename.replace('.json', '.csv')
                    export_file = export_dir / csv_filename
                    
                    if isinstance(data, dict):
                        # Convert dict to DataFrame
                        df = pd.DataFrame([data])
                        df.to_csv(export_file, index=False)
                        exported_files.append(csv_filename)
                    
                except Exception as e:
                    logger.warning(f"Failed to export {json_filename} to CSV: {e}")
        
        if exported_files:
            logger.info(f"✅ Exported {len(exported_files)} files to {export_dir}: {', '.join(exported_files)}")
            return True
        else:
            logger.error("No files were exported")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """Clean up old backups, keeping only the most recent ones.
        
        Args:
            keep_count: Number of recent backups to keep
        
        Returns:
            int: Number of backups deleted
        """
        backups = self.list_backups()
        if len(backups) <= keep_count:
            return 0
        
        backups_to_delete = backups[keep_count:]
        deleted_count = 0
        
        for backup_name in backups_to_delete:
            if self.delete_backup(backup_name):
                deleted_count += 1
        
        if deleted_count > 0:
            logger.info(f"✅ Cleaned up {deleted_count} old backups, kept {keep_count} most recent")
        
        return deleted_count


class BackupError(Exception):
    """Exception raised for backup-related errors."""
    pass


# Convenience functions for backward compatibility
def backup_data(data_dir: Path = None, backup_name: Optional[str] = None) -> str:
    """Create a backup of trading data files.
    
    Args:
        data_dir: Directory containing data files. If None, uses current directory.
        backup_name: Optional custom backup name. If None, uses timestamp.
    
    Returns:
        str: The backup name that was created
    """
    if data_dir is None:
        data_dir = Path.cwd()
    
    manager = BackupManager(data_dir)
    return manager.create_backup(backup_name)


def restore_from_backup(data_dir: Path = None, backup_name: Optional[str] = None) -> bool:
    """Restore data from a backup.
    
    Args:
        data_dir: Directory containing data files. If None, uses current directory.
        backup_name: Specific backup to restore. If None, uses latest.
    
    Returns:
        bool: True if restore was successful, False otherwise
    """
    if data_dir is None:
        data_dir = Path.cwd()
    
    manager = BackupManager(data_dir)
    return manager.restore_from_backup(backup_name)


def list_backups(data_dir: Path = None) -> List[str]:
    """List available backups.
    
    Args:
        data_dir: Directory containing data files. If None, uses current directory.
    
    Returns:
        List[str]: List of backup names sorted by creation time (newest first)
    """
    if data_dir is None:
        data_dir = Path.cwd()
    
    manager = BackupManager(data_dir)
    return manager.list_backups()