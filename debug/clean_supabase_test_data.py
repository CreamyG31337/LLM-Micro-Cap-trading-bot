"""
Clean up test data from Supabase to fix FIFO P&L calculation bug.
"""

import os
import sys
sys.path.append('.')

from dotenv import load_dotenv
from data.repositories.supabase_repository import SupabaseRepository

# Load Supabase credentials
load_dotenv("web_dashboard/.env")

def clean_test_data():
    """Clean up test data from Supabase."""
    print("=== CLEANING SUPABASE TEST DATA ===")
    
    # Create Supabase repository
    supabase_repo = SupabaseRepository(fund="TEST")
    
    # Get all trades
    trades = supabase_repo.get_trade_history()
    print(f"Found {len(trades)} trades in TEST fund")
    
    # List all trades
    for trade in trades:
        print(f"  {trade.ticker} {trade.action} {trade.shares} @ {trade.price} on {trade.timestamp}")
    
    # Delete all trades (this is a test fund, so it's safe)
    print("\nDeleting all trades from TEST fund...")
    
    # Note: We need to implement a delete method in the repository
    # For now, let's just document what needs to be cleaned
    test_tickers = ["FIFO", "TEST", "DUAL", "COORD", "FACTORY", "STOCK1", "STOCK2", "STOCK3", "COMPLEX", "DAILY"]
    
    print(f"Test tickers that should be cleaned: {test_tickers}")
    print("Manual cleanup required in Supabase dashboard or implement delete method")

if __name__ == "__main__":
    clean_test_data()
