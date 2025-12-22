#!/usr/bin/env python3
"""Check how many rows get_historical_fund_values actually fetches"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

fund_name = 'Project Chimera'

# Check what the query returns
result = client.supabase.table('portfolio_positions')\
    .select('date, shares, price, currency')\
    .eq('fund', fund_name)\
    .gte('date', '2025-09-01')\
    .order('date')\
    .execute()

print(f"Rows returned: {len(result.data)}")
if result.data:
    dates = sorted(set(r['date'][:10] for r in result.data))
    print(f"Unique dates: {len(dates)}")
    print(f"Date range: {dates[0]} to {dates[-1]}")
    print(f"\nLast 5 dates:")
    for d in dates[-5:]:
        print(f"  {d}")
