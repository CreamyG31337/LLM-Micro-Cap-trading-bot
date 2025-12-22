#!/usr/bin/env python3
"""Check true count of portfolio positions for Dec 2025"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

print("="*80)
print("CHECKING DECEMBER DATA")
print("="*80)

# Count records in December
dec_res = client.supabase.table('portfolio_positions')\
    .select('date', count='exact')\
    .eq('fund', 'Project Chimera')\
    .gte('date', '2025-12-01')\
    .execute()

print(f"Total December records: {len(dec_res.data)}")
if len(dec_res.data) > 0:
    dates = sorted(set(r['date'][:10] for r in dec_res.data))
    print(f"Dates found: {dates}")

# Check latest date
latest = client.supabase.table('portfolio_positions')\
    .select('date')\
    .eq('fund', 'Project Chimera')\
    .order('date', desc=True)\
    .limit(1)\
    .execute()

if latest.data:
    print(f"\nLatest position date: {latest.data[0]['date']}")
