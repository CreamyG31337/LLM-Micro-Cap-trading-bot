#!/usr/bin/env python3
"""
Trade Log Backup Utility

This script creates regular backups of the trade log file, which is critical data.
It can be run manually or scheduled to run automatically.

Usage:
    python utils/backup_trade_log.py
    python utils/backup_trade_log.py "trading_data/funds/RRSP Lance Webull"
    python utils/backup_trade_log.py "trading_data/funds/TEST"
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

def backup_trade_log(data_dir: str) -> bool:
    """
    Create a backup of the trade log file.
    
    Args:
        data_dir: Directory containing the trade log file
        
    Returns:
        bool: True if backup was successful, False otherwise
    """
    data_path = Path(data_dir)
    trade_log_file = data_path / "llm_trade_log.csv"
    
    if not trade_log_file.exists():
        print(f"❌ Trade log not found: {trade_log_file}")
        return False
    
    # Create backup directory
    backup_dir = data_path / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    # Create timestamped backup
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f"llm_trade_log.csv.backup_{timestamp}"
    
    try:
        shutil.copy2(trade_log_file, backup_file)
        print(f"✅ Trade log backed up to: {backup_file}")
        
        # Show backup size
        backup_size = backup_file.stat().st_size
        print(f"   Backup size: {backup_size:,} bytes")
        
        # List recent backups
        recent_backups = list(backup_dir.glob("llm_trade_log.csv.backup_*"))
        recent_backups.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        print(f"\n📁 Recent trade log backups ({len(recent_backups)} total):")
        for i, backup in enumerate(recent_backups[:5]):  # Show last 5
            backup_time = datetime.fromtimestamp(backup.stat().st_mtime)
            size = backup.stat().st_size
            print(f"   {i+1}. {backup.name} ({backup_time.strftime('%Y-%m-%d %H:%M:%S')}) - {size:,} bytes")
        
        if len(recent_backups) > 5:
            print(f"   ... and {len(recent_backups) - 5} more")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to backup trade log: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("❌ Error: Data directory required")
        print("Usage: python backup_trade_log.py <data_directory>")
        print("Example: python backup_trade_log.py 'trading_data/funds/TEST'")
        sys.exit(1)
    
    data_dir = sys.argv[1]
    
    print(f"🔄 Backing up trade log from: {data_dir}")
    print("=" * 50)
    
    success = backup_trade_log(data_dir)
    
    if success:
        print("\n🎉 Trade log backup completed successfully!")
    else:
        print("\n❌ Trade log backup failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
