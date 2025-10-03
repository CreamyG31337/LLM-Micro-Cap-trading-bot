#!/usr/bin/env python3
"""
Simple Data Verification Script
Verify data integrity between CSV and Supabase without emojis
"""

import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

try:
    from web_dashboard.supabase_client import SupabaseClient
    print("OK: Supabase client imported successfully")
except ImportError as e:
    print(f"ERROR: Failed to import Supabase client: {e}")
    sys.exit(1)

def load_csv_data(data_directory: str):
    """Load CSV data from the specified directory."""
    print(f"Loading CSV data from: {data_directory}")
    
    data_dir = Path(data_directory)
    
    # Load portfolio data
    portfolio_file = data_dir / "llm_portfolio_update.csv"
    if not portfolio_file.exists():
        print(f"ERROR: Portfolio file not found: {portfolio_file}")
        return None, None
    
    try:
        portfolio_df = pd.read_csv(portfolio_file)
        print(f"OK: Loaded {len(portfolio_df)} portfolio records from CSV")
    except Exception as e:
        print(f"ERROR: Failed to load portfolio data: {e}")
        return None, None
    
    # Load trade log
    trade_log_file = data_dir / "llm_trade_log.csv"
    if not trade_log_file.exists():
        print(f"ERROR: Trade log file not found: {trade_log_file}")
        return None, None
    
    try:
        trade_log_df = pd.read_csv(trade_log_file)
        print(f"OK: Loaded {len(trade_log_df)} trade records from CSV")
    except Exception as e:
        print(f"ERROR: Failed to load trade log: {e}")
        return None, None
    
    return portfolio_df, trade_log_df

def load_supabase_data():
    """Load data from Supabase."""
    print("Loading data from Supabase...")
    
    try:
        client = SupabaseClient()
        print("OK: Supabase client initialized")
    except Exception as e:
        print(f"ERROR: Failed to initialize Supabase client: {e}")
        return None, None
    
    # Load portfolio data
    try:
        result = client.supabase.table("portfolio_positions").select("*").execute()
        portfolio_data = result.data
        print(f"OK: Loaded {len(portfolio_data)} portfolio records from Supabase")
    except Exception as e:
        print(f"ERROR: Failed to load portfolio data from Supabase: {e}")
        return None, None
    
    # Load trade log
    try:
        result = client.supabase.table("trade_log").select("*").execute()
        trade_data = result.data
        print(f"OK: Loaded {len(trade_data)} trade records from Supabase")
    except Exception as e:
        print(f"ERROR: Failed to load trade data from Supabase: {e}")
        return None, None
    
    return portfolio_data, trade_data

def compare_portfolio_data(csv_df, supabase_data):
    """Compare portfolio data between CSV and Supabase."""
    print("\nComparing portfolio data...")
    
    if csv_df is None or supabase_data is None:
        print("ERROR: Cannot compare - missing data")
        return False
    
    # Convert Supabase data to DataFrame for easier comparison
    supabase_df = pd.DataFrame(supabase_data)
    
    print(f"CSV portfolio records: {len(csv_df)}")
    print(f"Supabase portfolio records: {len(supabase_df)}")
    
    # Check if we have the same number of records (approximately)
    if abs(len(csv_df) - len(supabase_df)) > 5:  # Allow for some variance
        print(f"WARNING: Record count mismatch - CSV: {len(csv_df)}, Supabase: {len(supabase_df)}")
        return False
    
    # Check for common tickers
    csv_tickers = set(csv_df['Ticker'].dropna().unique())
    supabase_tickers = set(supabase_df['ticker'].dropna().unique())
    
    print(f"CSV unique tickers: {len(csv_tickers)}")
    print(f"Supabase unique tickers: {len(supabase_tickers)}")
    
    common_tickers = csv_tickers.intersection(supabase_tickers)
    print(f"Common tickers: {len(common_tickers)}")
    
    if len(common_tickers) < len(csv_tickers) * 0.8:  # At least 80% overlap
        print("WARNING: Significant ticker mismatch between CSV and Supabase")
        return False
    
    print("OK: Portfolio data comparison passed")
    return True

def compare_trade_data(csv_df, supabase_data):
    """Compare trade data between CSV and Supabase."""
    print("\nComparing trade data...")
    
    if csv_df is None or supabase_data is None:
        print("ERROR: Cannot compare - missing data")
        return False
    
    # Convert Supabase data to DataFrame for easier comparison
    supabase_df = pd.DataFrame(supabase_data)
    
    print(f"CSV trade records: {len(csv_df)}")
    print(f"Supabase trade records: {len(supabase_df)}")
    
    # Check if we have the same number of records (approximately)
    if abs(len(csv_df) - len(supabase_df)) > 2:  # Allow for small variance
        print(f"WARNING: Record count mismatch - CSV: {len(csv_df)}, Supabase: {len(supabase_df)}")
        return False
    
    # Check for common tickers
    csv_tickers = set(csv_df['Ticker'].dropna().unique())
    supabase_tickers = set(supabase_df['ticker'].dropna().unique())
    
    print(f"CSV unique tickers: {len(csv_tickers)}")
    print(f"Supabase unique tickers: {len(supabase_tickers)}")
    
    common_tickers = csv_tickers.intersection(supabase_tickers)
    print(f"Common tickers: {len(common_tickers)}")
    
    if len(common_tickers) < len(csv_tickers) * 0.8:  # At least 80% overlap
        print("WARNING: Significant ticker mismatch between CSV and Supabase")
        return False
    
    print("OK: Trade data comparison passed")
    return True

def main():
    """Main verification function."""
    print("DATA VERIFICATION SCRIPT")
    print("=" * 40)
    
    # Check environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("ERROR: Supabase credentials not found")
        print("Please set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
        return False
    
    # Load CSV data
    data_directory = "trading_data/funds/Project Chimera"
    csv_portfolio, csv_trades = load_csv_data(data_directory)
    
    if csv_portfolio is None or csv_trades is None:
        print("ERROR: Failed to load CSV data")
        return False
    
    # Load Supabase data
    supabase_portfolio, supabase_trades = load_supabase_data()
    
    if supabase_portfolio is None or supabase_trades is None:
        print("ERROR: Failed to load Supabase data")
        return False
    
    # Compare data
    portfolio_match = compare_portfolio_data(csv_portfolio, supabase_portfolio)
    trade_match = compare_trade_data(csv_trades, supabase_trades)
    
    if portfolio_match and trade_match:
        print("\n" + "=" * 40)
        print("VERIFICATION COMPLETED SUCCESSFULLY")
        print("Data integrity between CSV and Supabase is good")
        print("=" * 40)
        return True
    else:
        print("\n" + "=" * 40)
        print("VERIFICATION COMPLETED WITH WARNINGS")
        print("Some data mismatches detected - check details above")
        print("=" * 40)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
