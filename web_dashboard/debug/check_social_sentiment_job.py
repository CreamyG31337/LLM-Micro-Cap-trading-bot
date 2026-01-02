#!/usr/bin/env python3
"""
Diagnostic script to check social sentiment job status and execution logs.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def check_scheduler_status():
    """Check if scheduler is running and job is registered."""
    print("=" * 70)
    print("SCHEDULER STATUS CHECK")
    print("=" * 70)
    
    try:
        from scheduler import get_scheduler, get_job_status
        
        scheduler = get_scheduler()
        print(f"Scheduler running: {scheduler.running}")
        
        if not scheduler.running:
            print("⚠️  WARNING: Scheduler is NOT running!")
            return False
        
        # Check if job is registered
        job = scheduler.get_job('social_sentiment')
        if not job:
            print("❌ ERROR: social_sentiment job is NOT registered!")
            return False
        
        print(f"✅ Job registered: {job.name}")
        print(f"   Job ID: {job.id}")
        print(f"   Trigger: {job.trigger}")
        print(f"   Next run: {job.next_run_time}")
        print(f"   Is paused: {job.next_run_time is None}")
        
        # Get detailed status
        status = get_job_status('social_sentiment')
        if status:
            print(f"\nDetailed Status:")
            print(f"   Is running: {status.get('is_running', False)}")
            if status.get('running_since'):
                print(f"   Running since: {status.get('running_since')}")
            if status.get('last_error'):
                print(f"   Last error: {status.get('last_error')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_execution_logs():
    """Check job execution logs for today."""
    print("\n" + "=" * 70)
    print("EXECUTION LOGS (Today)")
    print("=" * 70)
    
    try:
        from supabase_client import SupabaseClient
        
        client = SupabaseClient(use_service_role=True)
        
        # Get today's date
        today = datetime.now(timezone.utc).date()
        today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        today_start_str = today_start.isoformat()
        
        print(f"Checking executions for: {today}")
        print(f"From: {today_start_str}\n")
        
        # Query job_executions table
        result = client.supabase.table("job_executions")\
            .select("*")\
            .eq("job_name", "social_sentiment")\
            .gte("started_at", today_start_str)\
            .order("started_at", desc=True)\
            .execute()
        
        if not result.data:
            print("❌ No executions found for today!")
            print("\nChecking recent executions (last 7 days):")
            
            # Check last 7 days
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            week_ago_str = week_ago.isoformat()
            
            result = client.supabase.table("job_executions")\
                .select("*")\
                .eq("job_name", "social_sentiment")\
                .gte("started_at", week_ago_str)\
                .order("started_at", desc=True)\
                .limit(10)\
                .execute()
            
            if result.data:
                print(f"\nFound {len(result.data)} recent executions:")
                for record in result.data:
                    started = record.get('started_at', 'N/A')
                    status = record.get('status', 'unknown')
                    duration = record.get('duration_ms', 0)
                    error = record.get('error_message', '')
                    
                    print(f"\n  Started: {started}")
                    print(f"  Status: {status}")
                    print(f"  Duration: {duration}ms ({duration/1000/60:.1f} minutes)" if duration else "  Duration: N/A")
                    if error:
                        print(f"  Error: {error}")
            else:
                print("  No executions found in last 7 days!")
        else:
            print(f"✅ Found {len(result.data)} execution(s) today:")
            for record in result.data:
                started = record.get('started_at', 'N/A')
                completed = record.get('completed_at', 'N/A')
                status = record.get('status', 'unknown')
                duration = record.get('duration_ms', 0)
                error = record.get('error_message', '')
                
                print(f"\n  Started: {started}")
                print(f"  Completed: {completed}")
                print(f"  Status: {status}")
                print(f"  Duration: {duration}ms ({duration/1000/60:.1f} minutes)" if duration else "  Duration: N/A")
                if error:
                    print(f"  Error: {error}")
        
    except Exception as e:
        print(f"❌ Error checking execution logs: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run all diagnostic checks."""
    print("\n🔍 Social Sentiment Job Diagnostic Check\n")
    
    scheduler_ok = check_scheduler_status()
    check_execution_logs()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if not scheduler_ok:
        print("❌ Scheduler is not running or job is not registered!")
        print("   Action: Check if web dashboard is running and scheduler is initialized")
    else:
        print("✅ Scheduler is running and job is registered")
        print("   If job hasn't run today, check:")
        print("   1. Is the job paused?")
        print("   2. Are there any errors in the logs?")
        print("   3. Is the scheduler actually executing jobs?")


if __name__ == "__main__":
    main()

