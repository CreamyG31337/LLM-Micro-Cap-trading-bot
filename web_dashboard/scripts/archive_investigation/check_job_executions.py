#!/usr/bin/env python3
"""
Check recent job executions in the database to see if scheduler is running.
"""

import sys
from pathlib import Path

# Add web_dashboard to path
web_dashboard_path = Path(__file__).resolve().parent / "web_dashboard"
sys.path.insert(0, str(web_dashboard_path))

from supabase_client import SupabaseClient
from datetime import datetime, timedelta

print("=" * 70)
print("CHECKING JOB EXECUTIONS IN DATABASE")
print("=" * 70)
print()

try:
    client = SupabaseClient(use_service_role=True)
    
    # Get today's date
    today = datetime.utcnow().date()
    print(f"Today's date (UTC): {today}")
    print()
    
    # Query recent job executions (last 7 days)
    cutoff_time = datetime.utcnow() - timedelta(days=7)
    
    print(f"Querying job executions since {cutoff_time.isoformat()}...")
    print()
    
    result = client.supabase.table("job_executions")\
        .select("job_name, status, started_at, completed_at")\
        .gte("completed_at", cutoff_time.isoformat())\
        .order("completed_at", desc=True)\
        .limit(50)\
        .execute()
    
    if result.data:
        print(f"Found {len(result.data)} job executions in last 7 days")
        print()
        
        # Group by job name
        jobs_by_name = {}
        for record in result.data:
            job_name = record.get('job_name', 'Unknown')
            if job_name not in jobs_by_name:
                jobs_by_name[job_name] = []
            jobs_by_name[job_name].append(record)
        
        print("Summary by job:")
        print("-" * 70)
        for job_name, executions in sorted(jobs_by_name.items()):
            latest = executions[0]
            completed_at = latest.get('completed_at', 'Unknown')
            status = latest.get('status', 'Unknown')
            
            print(f"  {job_name}:")
            print(f"    Last execution: {completed_at}")
            print(f"    Status: {status}")
            print(f"    Total executions (7d): {len(executions)}")
            print()
        
        # Check for today specifically
        print()
        print("Executions TODAY (UTC):")
        print("-" * 70)
        
        today_start = datetime.combine(today, datetime.min.time())
        today_executions = [r for r in result.data 
                           if r.get('completed_at', '').startswith(str(today))]
        
        if today_executions:
            print(f"Found {len(today_executions)} executions today:")
            for record in today_executions[:10]:
                job_name = record.get('job_name', 'Unknown')
                status = record.get('status', 'Unknown')
                completed_at = record.get('completed_at', 'Unknown')
                print(f"  [{status}] {job_name}: {completed_at}")
        else:
            print("  [WARNING] NO EXECUTIONS TODAY!")
            print("  This confirms the bug - jobs are not running!")
        
    else:
        print("[WARNING] No job executions found in last 7 days!")
        print("This confirms the bug - scheduler is likely not running or jobs are not registered.")
    
    print()
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 70)
print("DIAGNOSIS COMPLETE")
print("=" * 70)
