"""
Dry-run simulation of dividend job to show what WOULD happen.
This doesn't insert anything into the DB - just shows the logic.
"""
import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

# Setup paths
web_dashboard_path = str(Path(__file__).resolve().parent / "web_dashboard")
if web_dashboard_path not in sys.path:
    sys.path.insert(0, web_dashboard_path)

from supabase_client import SupabaseClient
from scheduler.jobs_dividends import (
    fetch_dividend_data,
    calculate_eligible_shares,
    calculate_withholding_tax,
    get_fund_type,
    get_price_on_date
)

print("🧪 DRY RUN - Dividend Processing Job Simulation")
print("=" * 70)

client = SupabaseClient(use_service_role=True)

# Get holdings
result = client.supabase.table("portfolio_positions")\
    .select("fund, ticker, shares")\
    .gt("shares", 0)\
    .execute()

# Group by (fund, ticker)
holdings_dict = {}
for row in result.data:
    key = (row['fund'], row['ticker'])
    if key not in holdings_dict:
        holdings_dict[key] = row['shares']

print(f"\n📊 Found {len(holdings_dict)} unique (fund, ticker) pairs")

# Check last 7 days
today = date.today()
lookback = today - timedelta(days=7)

print(f"🔍 Looking for dividends paid between {lookback} and {today}\n")

found_count = 0
would_process = []

for (fund, ticker), shares in list(holdings_dict.items())[:10]:  # Test first 10
    events = fetch_dividend_data(ticker)
    
    if not events:
        continue
    
    # Filter to recent pay dates
    recent_events = [e for e in events if lookback <= e.pay_date <= today]
    
    if not recent_events:
        continue
    
    found_count += 1
    
    for evt in recent_events:
        print(f"\n{'='*70}")
        print(f"🎯 DIVIDEND FOUND: {ticker} in {fund}")
        print(f"{'='*70}")
        print(f"  Ex-Date: {evt.ex_date}")
        print(f"  Pay-Date: {evt.pay_date}")
        print(f"  Amount per share: ${evt.amount:.4f}")
        print(f"  Data Source: {evt.source}")
        
        # Check eligibility
        eligible = calculate_eligible_shares(fund, ticker, evt.ex_date, client)
        print(f"\n  📈 Eligible Shares: {eligible}")
        
        if eligible <= 0:
            print(f"  ❌ SKIP: No shares held before ex-date")
            continue
        
        # Calculate amounts
        fund_type = get_fund_type(fund, client)
        gross = eligible * Decimal(str(evt.amount))
        tax = calculate_withholding_tax(gross, fund_type, ticker)
        net = gross - tax
        
        print(f"\n  💰 Financial:")
        print(f"     Gross Dividend: ${gross:.2f}")
        print(f"     Withholding Tax ({fund_type}): ${tax:.2f}")
        print(f"     Net Amount: ${net:.2f}")
        
        # Get DRIP price
        drip_price = get_price_on_date(ticker, evt.pay_date)
        if drip_price:
            drip_shares = net / drip_price
            print(f"\n  🔄 DRIP Reinvestment:")
            print(f"     Price on {evt.pay_date}: ${drip_price}")
            print(f"     Shares to buy: {drip_shares:.4f}")
            print(f"\n  ✅ WOULD CREATE DRIP TRANSACTION")
            would_process.append((fund, ticker, evt.pay_date))
        else:
            print(f"\n  ❌ SKIP: Could not get price for {evt.pay_date}")

print(f"\n{'='*70}")
print(f"📊 SUMMARY")
print(f"{'='*70}")
print(f"Dividends found in date range: {found_count}")
print(f"Would process: {len(would_process)} DRIP transactions")
if would_process:
    print("\nTransactions that would be created:")
    for fund, ticker, pay_date in would_process:
        print(f"  - {fund}/{ticker} on {pay_date}")
