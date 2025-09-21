#!/usr/bin/env python3
"""
Debug script to investigate timestamp timezone issue.
"""

import tempfile
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from data.repositories.csv_repository import CSVRepository
from data.models.trade import Trade

def debug_timestamp_issue():
    """Debug the timestamp conversion issue."""
    print("=== Timestamp Debug Session ===")
    
    # Create temporary repository
    data_dir = Path(tempfile.mkdtemp())
    repo = CSVRepository(data_directory=str(data_dir))
    
    # Create test timestamp
    test_timestamp = datetime(2025, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
    print(f"Original timestamp: {test_timestamp}")
    print(f"Original timezone: {test_timestamp.tzinfo}")
    
    # Create trade
    trade = Trade(
        ticker="MSFT",
        action="BUY",
        shares=Decimal('100'),
        price=Decimal('300.00'),
        timestamp=test_timestamp,
        cost_basis=Decimal('30000.00')
    )
    
    print(f"\nTrade timestamp before save: {trade.timestamp}")
    print(f"Trade timezone before save: {trade.timestamp.tzinfo}")
    
    # Check what to_csv_dict produces
    csv_dict = trade.to_csv_dict()
    print(f"\nCSV dict Date field: {csv_dict['Date']}")
    
    # Save trade
    repo.save_trade(trade)
    
    # Manually check what's in the CSV file
    csv_file = data_dir / "llm_trade_log.csv"
    if csv_file.exists():
        with open(csv_file, 'r') as f:
            content = f.read()
            print(f"\nCSV file content:\n{content}")
    
    # Read back trades
    trades = repo.get_trade_history()
    print(f"\nLoaded {len(trades)} trades")
    
    if trades:
        loaded_trade = trades[0]
        print(f"Loaded timestamp: {loaded_trade.timestamp}")
        print(f"Loaded timezone: {loaded_trade.timestamp.tzinfo}")
        
        # Calculate difference
        time_diff = abs((loaded_trade.timestamp - test_timestamp).total_seconds())
        print(f"Time difference: {time_diff} seconds")
        
        # Show both in UTC for comparison
        print(f"\nOriginal in UTC: {test_timestamp.astimezone(timezone.utc)}")
        print(f"Loaded in UTC: {loaded_trade.timestamp.astimezone(timezone.utc)}")
    
    # Cleanup
    import shutil
    shutil.rmtree(data_dir)
    
    print("\n=== Debug Session Complete ===")

if __name__ == "__main__":
    debug_timestamp_issue()