#!/usr/bin/env python3
"""
Verify Scheduler Status and SQLAlchemyJobStore
Checks if scheduler is running and if jobs are persisted in database
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_database_table():
    """Check if apscheduler_jobs table exists and has jobs"""
    database_url = os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        print("❌ SUPABASE_DATABASE_URL not set")
        return False
    
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(sqlalchemy.text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'apscheduler_jobs'
                )
            """))
            table_exists = result.fetchone()[0]
            
            if not table_exists:
                print("❌ Table 'apscheduler_jobs' does not exist")
                print("   This means scheduler hasn't been started yet")
                return False
            
            # Count jobs in table
            result = conn.execute(sqlalchemy.text("SELECT COUNT(*) FROM apscheduler_jobs"))
            job_count = result.fetchone()[0]
            
            print(f"✅ Table 'apscheduler_jobs' exists with {job_count} job(s)")
            
            # Show sample jobs
            if job_count > 0:
                result = conn.execute(sqlalchemy.text("""
                    SELECT id, next_run_time 
                    FROM apscheduler_jobs 
                    ORDER BY id 
                    LIMIT 5
                """))
                print("\n   Sample jobs:")
                for row in result:
                    job_id = row[0]
                    next_run = row[1]
                    print(f"      - {job_id}: next_run={next_run}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_scheduler_running():
    """Check if scheduler is actually running"""
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from scheduler.scheduler_core import get_scheduler, is_scheduler_running
        
        scheduler = get_scheduler(create=False)
        if not scheduler:
            print("❌ Scheduler instance not created")
            print("   Scheduler needs to be started (via UI or startup code)")
            return False
        
        if scheduler.running:
            print("✅ Scheduler is RUNNING")
            jobs = scheduler.get_jobs()
            print(f"   {len(jobs)} job(s) loaded from SQLAlchemyJobStore")
            
            # Show running jobs
            running_jobs = [j for j in jobs if j.next_run_time is not None]
            if running_jobs:
                print(f"\n   {len(running_jobs)} job(s) scheduled:")
                for job in running_jobs[:5]:
                    print(f"      - {job.id}: next_run={job.next_run_time}")
        else:
            print("⚠️  Scheduler exists but is NOT running")
            print("   Start it via the jobs page UI or add startup code to Flask app")
            jobs = scheduler.get_jobs()
            print(f"   {len(jobs)} job(s) loaded from SQLAlchemyJobStore (but paused/stopped)")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run verification checks"""
    print("=" * 60)
    print("Scheduler Verification")
    print("=" * 60)
    print()
    
    print("1. Checking SQLAlchemyJobStore database table...")
    db_ok = check_database_table()
    print()
    
    print("2. Checking scheduler status...")
    scheduler_ok = check_scheduler_running()
    print()
    
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    if db_ok and scheduler_ok:
        print("✅ Scheduler is fully operational!")
    elif db_ok:
        print("⚠️  SQLAlchemyJobStore is working, but scheduler is not running")
        print("   → Start scheduler via jobs page UI or add startup code")
    else:
        print("❌ SQLAlchemyJobStore not initialized")
        print("   → Start scheduler once to create the database table")
    
    return 0 if (db_ok and scheduler_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
