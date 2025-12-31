
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from supabase_client import SupabaseClient

def check_job_history():
    client = SupabaseClient(use_service_role=True)
    
    print("Fetching recent job executions...")
    
    # Get running jobs
    running = client.supabase.table("job_executions")\
        .select("job_name, started_at, status")\
        .eq("status", "running")\
        .execute()
        
    print("\nRUNNING JOBS:")
    print(f"{'Job Name':<35} | {'Started At':<25}")
    print("-" * 65)
    if running.data:
        for job in running.data:
            print(f"{job.get('job_name'):<35} | {job.get('started_at')}")
    else:
        print("No running jobs.")

    print("\nCOMPLETED JOBS (Last 20):")
    # Get last 20 executions
    result = client.supabase.table("job_executions")\
        .select("job_name, completed_at, status, duration_ms, error_message")\
        .neq("status", "running")\
        .order("completed_at", desc=True)\
        .limit(20)\
        .execute()
        
    print(f"{'Job Name':<35} | {'Completed At':<25} | {'Status':<10} | {'Duration':<10} | {'Message'}")
    print("-" * 120)
    
    if result.data:
        for job in result.data:
            job_name = job.get('job_name') or 'Unknown'
            completed_at = job.get('completed_at') or 'N/A'
            status = job.get('status') or 'Unknown'
            duration = f"{job.get('duration_ms', 0)}ms"
            message = (job.get('error_message') or '')[:40]
            
            print(f"{job_name:<35} | {completed_at:<25} | {status:<10} | {duration:<10} | {message}")
    else:
        print("No completed jobs found.")

if __name__ == "__main__":
    check_job_history()
