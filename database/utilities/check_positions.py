#!/usr/bin/env python3
"""
Quick script to check portfolio positions in database
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv(project_root / 'web_dashboard' / '.env')

from supabase_client import SupabaseClient

# Connect to database
client = SupabaseClient()

print("Checking portfolio positions for 'RRSP Lance Webull'...")
print("=" * 70)

# Get all positions ordered by date
result = client.supabase.table("portfolio_positions") \
    .select("date, ticker") \
    .eq("fund", "RRSP Lance Webull") \
    .order("date", desc=True) \
    .limit(100) \
    .execute()

if result.data:
    # Group by date
    from collections import defaultdict
    by_date = defaultdict(list)
    
    for pos in result.data:
        date_str = pos['date']
        # Parse the date
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            date_only = dt.date()
            by_date[date_only].append(pos['ticker'])
        except:
            by_date[date_str[:10]].append(pos['ticker'])
    
    print(f"\nFound positions across {len(by_date)} different dates:\n")
    for date_key in sorted(by_date.keys(), reverse=True)[:10]:
        tickers = by_date[date_key]
        print(f"  Date: {date_key}")
        print(f"    Positions: {len(tickers)}")
        print(f"    Tickers: {len(set(tickers))} unique")
        print()
    
    # Show latest timestamp
    latest = result.data[0]['date']
    print(f"Latest timestamp in DB: {latest}")
    print(f"Current time:          {datetime.now()}")
else:
    print("No positions found!")

# Get total count
total_result = client.supabase.table("portfolio_positions") \
    .select("id", count="exact") \
    .eq("fund", "RRSP Lance Webull") \
    .execute()

print(f"\nTotal positions: {total_result.count}")
