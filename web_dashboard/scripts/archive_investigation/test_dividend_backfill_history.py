"""
Dry-run simulation of dividend job with 6 MONTH BACKFILL (August+).
"""
import sys
from pathlib import Path
from datetime import date, timedelta
from decimal import Decimal

# Setup paths
current_dir = Path(__file__).resolve().parent
project_root = current_dir

# 1. Add web_dashboard
web_dashboard_path = str(project_root / 'web_dashboard')
if web_dashboard_path not in sys.path:
    sys.path.append(web_dashboard_path)

# 2. Add root (FORCE to front)
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
elif sys.path[0] != str(project_root):
    sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))

from supabase_client import SupabaseClient
from scheduler.jobs_dividends import (
    fetch_dividend_data,
    calculate_eligible_shares,
    calculate_withholding_tax,
    get_fund_type,
    get_price_on_date
)

print("🧪 DRY RUN - 180 DAY (6 MONTH) BACKFILL Simulation")
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

# Check last 180 days (approx 6 months)
today = date.today()
lookback = today - timedelta(days=180)

print(f"🔍 Looking for dividends paid between {lookback} and {today}\n")

found_count = 0
would_process = []

for (fund, ticker), shares in list(holdings_dict.items()):
    events = fetch_dividend_data(ticker)
    
    if not events:
        continue
    
    # Filter to recent pay dates
    recent_events = [e for e in events if lookback <= e.pay_date <= today]
    
    if not recent_events:
        continue
    
    found_count += len(recent_events)
    
    print(f"\n-> {ticker} ({len(recent_events)} events):")
    
    for evt in recent_events:
        # Check eligibility
        eligible = calculate_eligible_shares(fund, ticker, evt.ex_date, client)
        
        if eligible <= 0:
            continue
            
        print(f"   ✅ [DIV FOUND] {evt.ex_date} | Pay: {evt.pay_date} | ${evt.amount:.4f} | Src: {evt.source}")
        
        # Calculate amounts
        fund_type = get_fund_type(fund, client)
        gross = eligible * Decimal(str(evt.amount))
        tax = calculate_withholding_tax(gross, fund_type, ticker)
        net = gross - tax
        
        # Get DRIP price
        drip_price = get_price_on_date(ticker, evt.pay_date)
        if drip_price:
            drip_shares = net / drip_price
            would_process.append((fund, ticker, evt.pay_date))
        else:
            print(f"      ❌ SKIP: No price for {evt.pay_date}")

print(f"\n{'='*70}")
print(f"📊 SUMMARY")
print(f"{'='*70}")
print(f"Eligible Dividends found in last 180 days: {len(would_process)}")
print(f"Total events found (raw): {found_count}")
