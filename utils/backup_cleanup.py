#!/usr/bin/env python3
"""Backup cleanup utility for removing old backup files.

This utility provides age-based cleanup of backup files across all funds,
removing backups older than a specified number of days.
"""

import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple, Dict
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.backup_manager import BackupManager
from config.settings import Settings

logger = logging.getLogger(__name__)


class BackupCleanupUtility:
    """Utility for cleaning up old backup files across all funds."""
    
    def __init__(self, data_base_dir: Path = None):
        """Initialize the cleanup utility.
        
        Args:
            data_base_dir: Base directory containing funds. If None, uses default.
        """
        if data_base_dir is None:
            # Use the trading_data directory directly
            data_base_dir = Path("trading_data")
        
        self.data_base_dir = Path(data_base_dir)
        self.funds_dir = self.data_base_dir / "funds"
        
        if not self.funds_dir.exists():
            raise FileNotFoundError(f"Funds directory not found: {self.funds_dir}")
    
    def get_all_fund_backup_dirs(self) -> List[Tuple[Path, str]]:
        """Get all fund backup directories.
        
        Returns:
            List of tuples containing (backup_dir_path, fund_name)
        """
        backup_dirs = []
        
        for fund_dir in self.funds_dir.iterdir():
            if fund_dir.is_dir():
                backup_dir = fund_dir / "backups"
                if backup_dir.exists():
                    backup_dirs.append((backup_dir, fund_dir.name))
        
        return backup_dirs
    
    def cleanup_old_backups_by_age(self, days_old: int = 7, dry_run: bool = False) -> Dict[str, int]:
        """Clean up backups older than specified days across all funds.
        
        Args:
            days_old: Remove backups older than this many days
            dry_run: If True, only show what would be deleted without actually deleting
            
        Returns:
            Dictionary mapping fund names to number of backups deleted
        """
        cutoff_date = datetime.now() - timedelta(days=days_old)
        results = {}
        
        print(f"🧹 Cleaning up backups older than {days_old} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
        if dry_run:
            print("🔍 DRY RUN MODE - No files will be deleted")
        print()
        
        backup_dirs = self.get_all_fund_backup_dirs()
        
        if not backup_dirs:
            print("❌ No fund backup directories found")
            return results
        
        total_deleted = 0
        total_size_freed = 0
        
        for backup_dir, fund_name in backup_dirs:
            print(f"📁 Processing fund: {fund_name}")
            
            deleted_count, size_freed = self._cleanup_fund_backups(
                backup_dir, fund_name, cutoff_date, dry_run
            )
            
            results[fund_name] = deleted_count
            total_deleted += deleted_count
            total_size_freed += size_freed
            
            if deleted_count > 0:
                print(f"   ✅ {deleted_count} backups removed ({self._format_size(size_freed)})")
            else:
                print(f"   ℹ️  No old backups found")
            print()
        
        # Summary
        print("=" * 60)
        if dry_run:
            print(f"🔍 DRY RUN SUMMARY:")
            print(f"   Would delete {total_deleted} backup files")
            print(f"   Would free up {self._format_size(total_size_freed)}")
        else:
            print(f"✅ CLEANUP SUMMARY:")
            print(f"   Deleted {total_deleted} backup files")
            print(f"   Freed up {self._format_size(total_size_freed)}")
        
        return results
    
    def _cleanup_fund_backups(self, backup_dir: Path, fund_name: str, 
                            cutoff_date: datetime, dry_run: bool) -> Tuple[int, int]:
        """Clean up backups for a specific fund.
        
        Args:
            backup_dir: Path to the fund's backup directory
            fund_name: Name of the fund
            cutoff_date: Remove backups older than this date
            dry_run: If True, only show what would be deleted
            
        Returns:
            Tuple of (deleted_count, size_freed_bytes)
        """
        deleted_count = 0
        size_freed = 0
        
        # Find all backup files
        backup_files = list(backup_dir.glob("*.backup_*"))
        
        for backup_file in backup_files:
            try:
                # Get file modification time
                file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                file_size = backup_file.stat().st_size
                
                # Check if file is older than cutoff
                if file_mtime < cutoff_date:
                    if dry_run:
                        print(f"   🔍 Would delete: {backup_file.name} ({self._format_size(file_size)})")
                    else:
                        backup_file.unlink()
                        print(f"   🗑️  Deleted: {backup_file.name} ({self._format_size(file_size)})")
                    
                    deleted_count += 1
                    size_freed += file_size
                    
            except Exception as e:
                logger.warning(f"Error processing {backup_file.name}: {e}")
                print(f"   ⚠️  Error processing {backup_file.name}: {e}")
        
        return deleted_count, size_freed
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format.
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        size = float(size_bytes)
        
        while size >= 1024.0 and i < len(size_names) - 1:
            size /= 1024.0
            i += 1
        
        return f"{size:.1f} {size_names[i]}"
    
    def list_backup_stats(self) -> None:
        """List backup statistics for all funds."""
        print("📊 BACKUP STATISTICS")
        print("=" * 60)
        
        backup_dirs = self.get_all_fund_backup_dirs()
        
        if not backup_dirs:
            print("❌ No fund backup directories found")
            return
        
        total_files = 0
        total_size = 0
        
        for backup_dir, fund_name in backup_dirs:
            backup_files = list(backup_dir.glob("*.backup_*"))
            fund_size = sum(f.stat().st_size for f in backup_files if f.exists())
            
            print(f"📁 {fund_name}:")
            print(f"   Files: {len(backup_files)}")
            print(f"   Size: {self._format_size(fund_size)}")
            print()
            
            total_files += len(backup_files)
            total_size += fund_size
        
        print("=" * 60)
        print(f"📊 TOTAL: {total_files} files, {self._format_size(total_size)}")


def main():
    """Main entry point for the backup cleanup utility."""
    parser = argparse.ArgumentParser(
        description="Clean up old backup files across all funds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Clean up backups older than 7 days (default)
  python utils/backup_cleanup.py

  # Clean up backups older than 14 days
  python utils/backup_cleanup.py --days 14

  # Dry run to see what would be deleted
  python utils/backup_cleanup.py --dry-run

  # Show backup statistics
  python utils/backup_cleanup.py --stats

  # Clean up with verbose output
  python utils/backup_cleanup.py --days 30 --verbose
        """
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=7,
        help='Remove backups older than this many days (default: 7)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show backup statistics for all funds'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--data-dir',
        type=str,
        help='Override data directory path'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    try:
        # Initialize cleanup utility
        data_dir = Path(args.data_dir) if args.data_dir else None
        cleanup_util = BackupCleanupUtility(data_dir)
        
        if args.stats:
            # Show statistics
            cleanup_util.list_backup_stats()
        else:
            # Clean up old backups
            results = cleanup_util.cleanup_old_backups_by_age(
                days_old=args.days,
                dry_run=args.dry_run
            )
            
            # Exit with appropriate code
            total_deleted = sum(results.values())
            if total_deleted > 0:
                print(f"\n🎉 Cleanup completed successfully!")
            else:
                print(f"\nℹ️  No old backups found to clean up.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
