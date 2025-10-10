#!/usr/bin/env python3
"""
Quick debug script to check Supabase data.
Usage: python debug_supabase.py "Project Chimera"
"""

import sys
import os
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env from current directory
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables only.")

from data.repositories.supabase_repository import SupabaseRepository

def debug_fund(fund_name: str):
    """Debug a specific fund's data."""
    
    print(f"🔍 Debugging fund: {fund_name}")
    print("=" * 50)
    
    # Check if Supabase credentials are available
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_ANON_KEY"):
        print("❌ Error: Supabase credentials not found")
        print("   Make sure your .env file contains:")
        print("   SUPABASE_URL=your-project-url")
        print("   SUPABASE_ANON_KEY=your-anon-key")
        return 1
    
    try:
        # Initialize repository
        repo = SupabaseRepository(fund_name)
        
        # Get fund summary
        print("📊 Fund Summary:")
        summary = repo.get_fund_summary()
        print(f"   Total trades: {summary['total_trades']}")
        print(f"   Unique tickers: {summary['unique_tickers']}")
        print(f"   Total value: ${summary['total_value']:,.2f}")
        if summary['date_range']:
            print(f"   Date range: {summary['date_range']['first']} to {summary['date_range']['last']}")
        print()
        
        # Get recent trades
        print("📈 Recent Trades (last 10):")
        recent_trades = repo.get_recent_trades(days=30, limit=10)
        
        if not recent_trades:
            print("   No recent trades found")
        else:
            for trade in recent_trades:
                print(f"   {trade.timestamp.strftime('%Y-%m-%d %H:%M')} | {trade.ticker} | {trade.action} | {trade.shares} @ ${trade.price}")
        print()
        
        # Show tickers
        if summary['tickers']:
            print(f"📋 Tickers in fund ({len(summary['tickers'])}):")
            for i, ticker in enumerate(summary['tickers'], 1):
                print(f"   {i:2d}. {ticker}")
        print()
        
        # Check for specific ticker if provided
        if len(sys.argv) > 2:
            ticker = sys.argv[2]
            print(f"🔍 Trades for {ticker}:")
            ticker_trades = repo.get_trades_by_ticker(ticker, limit=20)
            
            if not ticker_trades:
                print(f"   No trades found for {ticker}")
            else:
                for trade in ticker_trades:
                    print(f"   {trade.timestamp.strftime('%Y-%m-%d %H:%M')} | {trade.action} | {trade.shares} @ ${trade.price} | {trade.reason}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python debug_supabase.py <fund_name> [ticker]")
        print("Example: python debug_supabase.py 'Project Chimera'")
        print("Example: python debug_supabase.py 'Project Chimera' GD")
        return 1
    
    fund_name = sys.argv[1]
    return debug_fund(fund_name)

if __name__ == "__main__":
    sys.exit(main())
