#!/usr/bin/env python3
"""Utility to rename existing backup files to follow the new naming pattern.

This script renames all existing backup files to use the new pattern:
- Old: filename.backup_timestamp
- New: filename.backup_timestamp.csv

It handles both CSV and JSON files, converting JSON backups to CSV format.
"""

import logging
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import sys
import shutil
import json
import pandas as pd

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings

logger = logging.getLogger(__name__)


class BackupRenamer:
    """Utility for renaming backup files to follow the new naming pattern."""
    
    def __init__(self, data_base_dir: Path = None):
        """Initialize the renamer.
        
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
    
    def rename_backups_in_fund(self, backup_dir: Path, fund_name: str, dry_run: bool = False) -> Tuple[int, int]:
        """Rename backup files in a specific fund directory.
        
        Args:
            backup_dir: Path to the fund's backup directory
            fund_name: Name of the fund
            dry_run: If True, only show what would be renamed without actually renaming
            
        Returns:
            Tuple of (renamed_count, error_count)
        """
        renamed_count = 0
        error_count = 0
        
        print(f"📁 Processing fund: {fund_name}")
        
        # Find all backup files with old pattern (no .csv extension)
        old_pattern_files = []
        for file_path in backup_dir.iterdir():
            if file_path.is_file() and '.backup_' in file_path.name and not file_path.name.endswith('.csv'):
                old_pattern_files.append(file_path)
        
        if not old_pattern_files:
            print(f"   ℹ️  No old pattern backup files found")
            return renamed_count, error_count
        
        print(f"   Found {len(old_pattern_files)} old pattern backup files")
        
        for old_file in old_pattern_files:
            try:
                # Extract timestamp from filename
                parts = old_file.name.split('.backup_')
                if len(parts) >= 2:
                    base_name = parts[0]
                    timestamp = parts[1]
                    
                    # Determine if this should be a JSON or CSV file
                    if base_name in ['cash_balances']:
                        # This should be a JSON file, convert to CSV
                        new_name = f"{base_name}.backup_{timestamp}.csv"
                        new_path = backup_dir / new_name
                        
                        if dry_run:
                            print(f"   🔍 Would convert: {old_file.name} -> {new_name}")
                        else:
                            # Convert JSON to CSV
                            with open(old_file, 'r') as f:
                                data = json.load(f)
                            
                            if isinstance(data, dict):
                                df = pd.DataFrame([data])
                                df.to_csv(new_path, index=False)
                                old_file.unlink()  # Remove old file
                                print(f"   ✅ Converted: {old_file.name} -> {new_name}")
                            else:
                                print(f"   ⚠️  Skipping {old_file.name}: Unexpected JSON structure")
                                error_count += 1
                                continue
                    else:
                        # This should be a CSV file, just rename
                        new_name = f"{base_name}.backup_{timestamp}.csv"
                        new_path = backup_dir / new_name
                        
                        if dry_run:
                            print(f"   🔍 Would rename: {old_file.name} -> {new_name}")
                        else:
                            shutil.move(str(old_file), str(new_path))
                            print(f"   ✅ Renamed: {old_file.name} -> {new_name}")
                    
                    renamed_count += 1
                else:
                    print(f"   ⚠️  Skipping {old_file.name}: Could not parse filename")
                    error_count += 1
                    
            except Exception as e:
                print(f"   ❌ Error processing {old_file.name}: {e}")
                error_count += 1
        
        return renamed_count, error_count
    
    def rename_all_backups(self, dry_run: bool = False) -> Dict[str, Tuple[int, int]]:
        """Rename all backup files across all funds.
        
        Args:
            dry_run: If True, only show what would be renamed without actually renaming
            
        Returns:
            Dictionary mapping fund names to (renamed_count, error_count) tuples
        """
        print(f"🔄 Renaming backup files to new pattern...")
        if dry_run:
            print("🔍 DRY RUN MODE - No files will be renamed")
        print()
        
        backup_dirs = self.get_all_fund_backup_dirs()
        
        if not backup_dirs:
            print("❌ No fund backup directories found")
            return {}
        
        results = {}
        total_renamed = 0
        total_errors = 0
        
        for backup_dir, fund_name in backup_dirs:
            renamed_count, error_count = self.rename_backups_in_fund(
                backup_dir, fund_name, dry_run
            )
            
            results[fund_name] = (renamed_count, error_count)
            total_renamed += renamed_count
            total_errors += error_count
            
            if renamed_count > 0 or error_count > 0:
                print(f"   📊 {fund_name}: {renamed_count} renamed, {error_count} errors")
            print()
        
        # Summary
        print("=" * 60)
        if dry_run:
            print(f"🔍 DRY RUN SUMMARY:")
            print(f"   Would rename {total_renamed} backup files")
            print(f"   Would encounter {total_errors} errors")
        else:
            print(f"✅ RENAME SUMMARY:")
            print(f"   Renamed {total_renamed} backup files")
            print(f"   Encountered {total_errors} errors")
        
        return results


def main():
    """Main entry point for the backup renamer utility."""
    parser = argparse.ArgumentParser(
        description="Rename existing backup files to follow the new naming pattern",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be renamed
  python utils/rename_backups.py --dry-run

  # Actually rename the files
  python utils/rename_backups.py

  # Rename with verbose output
  python utils/rename_backups.py --verbose
        """
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be renamed without actually renaming'
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
        # Initialize renamer
        data_dir = Path(args.data_dir) if args.data_dir else None
        renamer = BackupRenamer(data_dir)
        
        # Rename backups
        results = renamer.rename_all_backups(dry_run=args.dry_run)
        
        # Exit with appropriate code
        total_renamed = sum(count[0] for count in results.values())
        total_errors = sum(count[1] for count in results.values())
        
        if total_errors > 0:
            print(f"\n⚠️  Completed with {total_errors} errors")
            sys.exit(1)
        elif total_renamed > 0:
            print(f"\n🎉 Rename completed successfully!")
        else:
            print(f"\nℹ️  No old pattern backup files found to rename.")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
