#!/usr/bin/env python3
"""
Data synchronization script for web dashboard
Copies trading data from production to web dashboard data directory
"""

import shutil
import os
from pathlib import Path
import json
from datetime import datetime

def sync_trading_data():
    """Sync trading data from production to web dashboard"""
    
    # Define paths
    source_dir = Path("../trading_data/prod")
    target_dir = Path("trading_data/prod")
    
    # Create target directory if it doesn't exist
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # Files to sync
    files_to_sync = [
        "llm_portfolio_update.csv",
        "llm_trade_log.csv", 
        "cash_balances.json"
    ]
    
    synced_files = []
    
    for filename in files_to_sync:
        source_file = source_dir / filename
        target_file = target_dir / filename
        
        if source_file.exists():
            shutil.copy2(source_file, target_file)
            synced_files.append(filename)
            print(f"✅ Synced {filename}")
        else:
            print(f"⚠️  Source file not found: {source_file}")
    
    # Create a sync log
    sync_log = {
        "last_sync": datetime.now().isoformat(),
        "files_synced": synced_files,
        "source_dir": str(source_dir),
        "target_dir": str(target_dir)
    }
    
    with open("sync_log.json", "w") as f:
        json.dump(sync_log, f, indent=2)
    
    print(f"\n📊 Data sync complete! Synced {len(synced_files)} files.")
    print(f"🕒 Last sync: {sync_log['last_sync']}")

if __name__ == "__main__":
    sync_trading_data()
