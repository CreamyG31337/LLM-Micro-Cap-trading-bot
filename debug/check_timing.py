#!/usr/bin/env python3
"""Calculate NAV over time correctly - check contribution times vs portfolio times"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd
from datetime import datetime, timedelta, time

client = SupabaseClient(use_service_role=True)
fund_name = 'Project Chimera'

# Get contributions with full timestamps
contribs = client.supabase.table('fund_contributions').select(
    'timestamp, amount, contribution_type, contributor'
).eq('fund', fund_name).order('timestamp').execute()

print("Contributions with times:")
for record in contribs.data:
    ts = pd.to_datetime(record['timestamp'])
    print(f"  {ts} | {record['contributor'][:15]:15s} | ${float(record['amount']):,.2f}")

# Get portfolio snapshot times
result = client.supabase.table("portfolio_positions").select(
    "date"
).eq("fund", fund_name).gte("date", '2025-09-08').order("date").limit(5).execute()

print("\nPortfolio snapshot times:")
for row in result.data[:5]:
    ts = pd.to_datetime(row['date'])
    print(f"  {ts}")
