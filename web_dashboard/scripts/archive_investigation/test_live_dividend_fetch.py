"""
Live test of dividend fetching with actual tickers from holdings.
"""
import sys
from pathlib import Path

# Setup paths
web_dashboard_path = str(Path(__file__).resolve().parent / "web_dashboard")
if web_dashboard_path not in sys.path:
    sys.path.insert(0, web_dashboard_path)

from supabase_client import SupabaseClient
from scheduler.jobs_dividends import fetch_dividend_data

print("🔍 Fetching your current holdings...")
client = SupabaseClient(use_service_role=True)

# Get unique tickers
result = client.supabase.table("portfolio_positions")\
    .select("ticker")\
    .gt("shares", 0)\
    .execute()

unique_tickers = list(set(row['ticker'] for row in result.data))[:5]  # Test first 5

print(f"\n📊 Testing {len(unique_tickers)} tickers from your portfolio:\n")

for ticker in unique_tickers:
    print(f"{'='*60}")
    print(f"Ticker: {ticker}")
    print(f"{'='*60}")
    
    events = fetch_dividend_data(ticker)
    
    if events:
        # Show most recent
        recent = sorted(events, key=lambda e: e.pay_date, reverse=True)[0]
        print(f"✅ Found {len(events)} dividend events")
        print(f"   Most Recent:")
        print(f"   - Ex-Date: {recent.ex_date}")
        print(f"   - Pay-Date: {recent.pay_date}")
        print(f"   - Amount: ${recent.amount:.4f}")
        print(f"   - Source: {recent.source}")
    else:
        print(f"⚠️  No dividend data found (stock may not pay dividends)")
    print()
