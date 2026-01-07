#!/usr/bin/env python3
"""
Read Job Execution Logs
=======================

Query and display job execution logs from the job_executions table.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add web_dashboard to path
web_dashboard_path = Path(__file__).resolve().parent.parent
if str(web_dashboard_path) not in sys.path:
    sys.path.insert(0, str(web_dashboard_path))

from supabase_client import SupabaseClient


def read_job_logs(
    job_name: Optional[str] = None,
    status: Optional[str] = None,
    days_back: int = 1,
    limit: int = 50
) -> None:
    """Read and display job execution logs.
    
    Args:
        job_name: Filter by job name (e.g., 'update_portfolio_prices'). If None, shows all jobs.
        status: Filter by status ('running', 'success', 'failed'). If None, shows all statuses.
        days_back: Number of days to look back (default: 1)
        limit: Maximum number of records to return (default: 50)
    """
    client = SupabaseClient(use_service_role=True)
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days_back)
    
    print(f"\n{'='*80}")
    print(f"JOB EXECUTION LOGS")
    print(f"{'='*80}")
    print(f"Date range: {start_date.date()} to {end_date.date()}")
    if job_name:
        print(f"Job: {job_name}")
    if status:
        print(f"Status: {status}")
    print(f"{'='*80}\n")
    
    # Build query
    query = client.supabase.table("job_executions")\
        .select("*")\
        .gte("started_at", start_date.isoformat())\
        .order("started_at", desc=True)\
        .limit(limit)
    
    if job_name:
        query = query.eq("job_name", job_name)
    
    if status:
        query = query.eq("status", status)
    
    result = query.execute()
    
    if not result.data:
        print("No job executions found.")
        return
    
    print(f"Found {len(result.data)} execution(s):\n")
    
    for record in result.data:
        job_name_val = record.get('job_name', 'N/A')
        status_val = record.get('status', 'N/A')
        target_date = record.get('target_date', 'N/A')
        fund_name = record.get('fund_name') or 'all funds'
        started_at = record.get('started_at', 'N/A')
        completed_at = record.get('completed_at', 'N/A')
        duration_ms = record.get('duration_ms', 0)
        error_message = record.get('error_message', '')
        
        # Format timestamps
        if isinstance(started_at, str):
            try:
                started_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                started_str = started_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            except:
                started_str = str(started_at)
        else:
            started_str = str(started_at)
        
        if isinstance(completed_at, str) and completed_at:
            try:
                completed_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                completed_str = completed_dt.strftime('%Y-%m-%d %H:%M:%S %Z')
            except:
                completed_str = str(completed_at)
        else:
            completed_str = 'N/A'
        
        # Status icon
        if status_val == 'success':
            icon = '✅'
        elif status_val == 'failed':
            icon = '❌'
        elif status_val == 'running':
            icon = '🔵'
        else:
            icon = '❓'
        
        # Duration
        if duration_ms:
            if duration_ms < 1000:
                duration_str = f"{duration_ms}ms"
            else:
                seconds = duration_ms / 1000.0
                if seconds < 60:
                    duration_str = f"{seconds:.1f}s"
                else:
                    minutes = int(seconds // 60)
                    secs = int(seconds % 60)
                    duration_str = f"{minutes}m {secs}s"
        else:
            duration_str = "N/A"
        
        print(f"{icon} {job_name_val} - {status_val.upper()}")
        print(f"   Target Date: {target_date}")
        print(f"   Fund: {fund_name}")
        print(f"   Started: {started_str}")
        print(f"   Completed: {completed_str}")
        print(f"   Duration: {duration_str}")
        
        if error_message:
            # Truncate long error messages
            if len(error_message) > 200:
                error_message = error_message[:200] + "..."
            print(f"   Error: {error_message}")
        
        print()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Read job execution logs')
    parser.add_argument('--job', '-j', help='Job name to filter by (e.g., update_portfolio_prices)')
    parser.add_argument('--status', '-s', choices=['running', 'success', 'failed'], 
                       help='Status to filter by')
    parser.add_argument('--days', '-d', type=int, default=1, 
                       help='Number of days to look back (default: 1)')
    parser.add_argument('--limit', '-l', type=int, default=50,
                       help='Maximum number of records to return (default: 50)')
    
    args = parser.parse_args()
    
    read_job_logs(
        job_name=args.job,
        status=args.status,
        days_back=args.days,
        limit=args.limit
    )


if __name__ == "__main__":
    main()

