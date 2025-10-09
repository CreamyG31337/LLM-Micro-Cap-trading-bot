#!/usr/bin/env python3
"""Check what company names are actually in the database."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set environment variables
os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImluanFieGRxeXhmdmFubnlnYWR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNjY1MjEsImV4cCI6MjA3Mzg0MjUyMX0.gcR-dNuW8zFd9werFRhM90Z3QvRdmjyPVlmIcQo_9fo"

from supabase import create_client

def check_database_company_names():
    """Check what company names are actually in the database."""
    print("Checking database company names...")
    
    # Initialize Supabase client
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"]
    )
    
    # Check for the problematic tickers
    problematic_tickers = ["XMA", "DRX", "VEE", "CTRN"]
    
    for ticker in problematic_tickers:
        print(f"\n=== {ticker} ===")
        
        # Get all records for this ticker
        result = supabase.table("portfolio_positions") \
            .select("ticker, company, date") \
            .eq("fund", "TEST") \
            .eq("ticker", ticker) \
            .order("date", desc=True) \
            .limit(5) \
            .execute()
        
        if result.data:
            print(f"Found {len(result.data)} records:")
            for record in result.data:
                print(f"  {record['date']}: '{record['company']}'")
        else:
            print("No records found")
            
        # Also check for .TO variants
        to_ticker = f"{ticker}.TO"
        result_to = supabase.table("portfolio_positions") \
            .select("ticker, company, date") \
            .eq("fund", "TEST") \
            .eq("ticker", to_ticker) \
            .order("date", desc=True) \
            .limit(5) \
            .execute()
        
        if result_to.data:
            print(f"Found {len(result_to.data)} records for {to_ticker}:")
            for record in result_to.data:
                print(f"  {record['date']}: '{record['company']}'")

if __name__ == "__main__":
    check_database_company_names()
