#!/usr/bin/env python3
"""Check what company names are in the database for the latest timestamp."""

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

def check_latest_db_company_names():
    """Check what company names are in the database for the latest timestamp."""
    print("Checking latest database company names...")
    
    # Initialize Supabase client
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"]
    )
    
    # Get the latest timestamp
    max_date_query = supabase.table("portfolio_positions") \
        .select("date") \
        .eq("fund", "TEST") \
        .order("date", desc=True) \
        .limit(1) \
        .execute()
    
    if not max_date_query.data:
        print("No data found")
        return
    
    latest_timestamp = max_date_query.data[0]["date"]
    print(f"Latest timestamp: {latest_timestamp}")
    
    # Get all positions for the latest timestamp (EXACT timestamp, not date)
    positions_query = supabase.table("portfolio_positions") \
        .select("ticker, company, date") \
        .eq("fund", "TEST") \
        .eq("date", latest_timestamp) \
        .execute()
    
    print(f"Found {len(positions_query.data)} positions for latest timestamp")
    
    # Check for problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "CTRN", "XMA.TO", "DRX.TO", "VEE.TO"]
    
    print("\nCompany names for problematic tickers:")
    for record in positions_query.data:
        if record['ticker'] in problematic_tickers:
            print(f"  {record['ticker']}: '{record['company']}'")

if __name__ == "__main__":
    check_latest_db_company_names()
