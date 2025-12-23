#!/usr/bin/env python3
"""Check trade log around Sept 7-15"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

r = client.supabase.table('trade_log').select(
    'date, ticker, shares, price, cost_basis, reason'
).eq('fund', 'Project Chimera').gte('date', '2025-09-07').lte('date', '2025-09-15').order('date').execute()

print(f"Trades Sept 7-15: {len(r.data)}")
print("-" * 100)
for t in r.data:
    date = str(t['date'])[:10]
    shares = float(t.get('shares', 0))
    ticker = t.get('ticker', '???')
    price = float(t.get('price', 0))
    cost = float(t.get('cost_basis', 0))
    reason = str(t.get('reason', 'N/A'))[:40]
    print(f"{date}: {shares:>10.2f} {ticker:10} at ${price:>8.2f}  (cost: ${cost:>10.2f}) - {reason}")
