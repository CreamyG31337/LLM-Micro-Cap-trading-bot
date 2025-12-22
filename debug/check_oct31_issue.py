#!/usr/bin/env python3
"""Check why rebuild stopped at Oct 31"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.market_holidays import MarketHolidays
from market_data.market_hours import MarketHours
from datetime import date, timedelta

holidays = MarketHolidays()
hours = MarketHours()

print("="*80)
print("MARKET STATUS FOR OCT 31 - NOV 4")
print("="*80)

for i in range(5):
    d = date(2025, 10, 31) + timedelta(days=i)
    is_trading = holidays.is_trading_day(d, market='any')
    us_open = holidays.is_trading_day(d, market='us')
    ca_open = holidays.is_trading_day(d, market='canadian')
    print(f"{d} ({d.strftime('%A')[:3]}): Trading={is_trading}, US={us_open}, CA={ca_open}")

# Check if there was a trade after Oct 31
print("\n\n" + "="*80)
print("CHECKING IF ANY TRADES EXIST AFTER OCT 31")
print("="*80)

sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))
from supabase_client import SupabaseClient
client = SupabaseClient(use_service_role=True)

trades = client.supabase.table('trade_log')\
    .select('date, ticker, fund')\
    .eq('fund', 'Project Chimera')\
    .gt('date', '2025-10-31')\
    .order('date')\
    .execute()

if trades.data:
    print(f"Found {len(trades.data)} trades after Oct 31:")
    for t in trades.data[:10]:
        print(f"  {t['date'][:10]} | {t['ticker']}")
else:
    print("NO trades after Oct 31!")
    print("\nThis is why rebuild stopped - it only generates snapshots up to last trade date!")
