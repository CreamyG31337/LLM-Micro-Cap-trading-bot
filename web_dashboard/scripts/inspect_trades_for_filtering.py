
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / 'web_dashboard' / '.env')

from supabase_client import SupabaseClient

def main():
    client = SupabaseClient(use_service_role=True)
    
    print("Fetching sample trades to analyze asset types and descriptions...\n")
    
    # Fetch some trades
    response = client.supabase.table("congress_trades")\
        .select("*")\
        .limit(50)\
        .execute()
        
    trades = response.data
    
    print(f"{'Ticker':<10} | {'Asset Type':<15} | {'Issue Type':<15} | {'Description/Notes'}")
    print("-" * 100)
    
    for trade in trades:
        ticker = trade.get('ticker', '')
        asset_type = trade.get('asset_type', '') or 'N/A'
        
        # Try to get issue type from securities if possible (not joined here, but we can infer)
        notes = trade.get('notes', '') or ''
        
        print(f"{ticker:<10} | {asset_type:<15} | {'N/A':<15} | {notes[:50]}")

    print("\n\nChecking 'securities' table for ETF indicators...")
    # Fetch securities that might be ETFs
    response = client.supabase.table("securities")\
        .select("*")\
        .ilike("company_name", "%ETF%")\
        .limit(10)\
        .execute()
        
    print(f"\n{'Ticker':<10} | {'Company Name'}")
    print("-" * 50)
    for sec in response.data:
        print(f"{sec.get('ticker'):<10} | {sec.get('company_name')}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
