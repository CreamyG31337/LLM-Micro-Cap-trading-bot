#!/usr/bin/env python3
"""Check all job executions to find which job created October data"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
import pandas as pd

client = SupabaseClient(use_service_role=True)

# Get ALL job executions
result = client.supabase.table('job_executions').select('*').order('target_date').execute()

print("="*80)
print("ALL JOB EXECUTIONS")
print("="*80)

df = pd.DataFrame(result.data)

if len(df) > 0:
    print(f"\nTotal: {len(df)} records")
    print(f"\nUnique job names:")
    print(df['job_name'].value_counts())
    
    print(f"\n\nAll records:")
    print(df[['job_name', 'target_date', 'status', 'funds_processed']].to_string(index=False))
    
    # Check for October-related jobs
    oct_jobs = df[df['target_date'].str.startswith('2025-10')]
    if len(oct_jobs) > 0:
        print(f"\n\nOctober 2025 job executions: {len(oct_jobs)}")
        print(oct_jobs[['job_name', 'target_date', 'status']].to_string(index=False))
else:
    print("NO job_executions records found!")

# Also check portfolio_positions created_at to see when October data was inserted
print("\n\n" + "="*80)
print("PORTFOLIO_POSITIONS CREATION TIMES (October)")
print("="*80)

pos_result = client.supabase.table('portfolio_positions').select('date, created_at').eq('fund', 'Project Chimera').like('date', '2025-10%').order('created_at').execute()

if pos_result.data:
    pos_df = pd.DataFrame(pos_result.data)
    pos_df['created_date'] = pd.to_datetime(pos_df['created_at']).dt.date
    
    print(f"\nOctober positions: {len(pos_df)}")
    print(f"Created on dates: {sorted(pos_df['created_date'].unique())}")
    print(f"\nFirst 5 records:")
    print(pos_df.head()[['date', 'created_at']].to_string(index=False))
