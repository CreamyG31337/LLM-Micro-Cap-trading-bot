#!/usr/bin/env python3
"""Check job_executions table to see what dates were recorded"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

# Get all portfolio price update executions
result = client.supabase.table('job_executions').select('*').eq('job_name', 'update_portfolio_prices').order('target_date').execute()

df = pd.DataFrame(result.data)

if len(df) > 0:
    print(f"Total job execution records: {len(df)}")
    print(f"Date range: {df['target_date'].min()} to {df['target_date'].max()}")
    print(f"\nFirst 20 executions:")
    print(df.head(20)[['target_date', 'status', 'funds_processed']].to_string(index=False))
    
    # Check for any before October
    early = df[df['target_date'] < '2025-10-01']
    if len(early) > 0:
        print(f"\n\nExecutions before October 2025: {len(early)}")
        print(early[['target_date', 'status']].to_string(index=False))
    else:
        print("\n\nNO EXECUTIONS BEFORE OCTOBER 2025!")
        print("This explains why August-September portfolio_positions are missing.")
else:
    print("NO job_executions records found for 'update_portfolio_prices'!")
