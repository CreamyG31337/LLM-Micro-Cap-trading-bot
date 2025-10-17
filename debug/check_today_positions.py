#!/usr/bin/env python3
"""Check today's positions in Supabase."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
# Use environment variable instead of hardcoded key
    # # Use environment variable instead of hardcoded key
    # os.environ["SUPABASE_ANON_KEY"] = "your-key-here"  # REMOVED FOR SECURITY  # REMOVED FOR SECURITY

from supabase import create_client

def check_today_positions():
    """Check today's positions in Supabase."""
    print("Checking today's positions in Supabase...")
    
    # Initialize Supabase client
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"]
    )
    
    # Get positions from today
    result = supabase.table('portfolio_positions') \
        .select('ticker, date, company, shares, price') \
        .eq('fund', 'TEST') \
        .gte('date', '2025-10-06T00:00:00Z') \
        .order('date', desc=True) \
        .execute()
    
    print(f"Found {len(result.data)} positions from today")
    
    # Group by ticker to see duplicates
    ticker_counts = {}
    for record in result.data:
        ticker = record['ticker']
        if ticker not in ticker_counts:
            ticker_counts[ticker] = []
        ticker_counts[ticker].append(record)
    
    print("\nPositions by ticker:")
    for ticker, positions in ticker_counts.items():
        print(f"\n{ticker} ({len(positions)} entries):")
        for pos in positions:
            print(f"  {pos['date']}: {pos['shares']} shares @ ${pos['price']} - {pos['company']}")

if __name__ == "__main__":
    check_today_positions()
