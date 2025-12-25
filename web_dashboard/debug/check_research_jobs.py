#!/usr/bin/env python3
"""
Check Research Jobs Status
==========================

This script checks:
1. If research jobs are scheduled and running
2. If jobs have executed recently
3. If data is being saved to PostgreSQL
4. Recent articles in the database
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

# Add web_dashboard to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from postgres_client import PostgresClient
    from research_repository import ResearchRepository
except ImportError as e:
    print(f"ERROR: Failed to import: {e}")
    print("Make sure you're in the project root and dependencies are installed")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Optional imports for scheduler checks
try:
    from scheduler.scheduler_core import get_scheduler, get_job_logs
    from scheduler.jobs import AVAILABLE_JOBS
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    print("Note: Scheduler modules not available (apscheduler may not be installed)")
    print("Will skip scheduler checks and focus on database verification\n")


def check_scheduler_status():
    """Check if scheduler is running and what jobs are registered"""
    print("=" * 70)
    print("SCHEDULER STATUS")
    print("=" * 70)
    
    if not SCHEDULER_AVAILABLE:
        print("WARNING: Scheduler modules not available - skipping check")
        print("   To check scheduler, ensure apscheduler is installed and web dashboard is running")
        return None  # Return None to indicate skipped
    
    try:
        scheduler = get_scheduler()
        
        if scheduler.running:
            print("[OK] Scheduler is RUNNING")
        else:
            print("[FAIL] Scheduler is NOT running")
            print("   Note: Scheduler may not be started if web dashboard isn't running")
            return False
        
        print(f"\nRegistered jobs:")
        jobs = scheduler.get_jobs()
        if not jobs:
            print("   No jobs registered")
            return False
        
        research_jobs = [j for j in jobs if 'research' in j.id.lower()]
        if not research_jobs:
            print("   [WARNING] No research jobs found!")
            print(f"   Total jobs: {len(jobs)}")
            for job in jobs:
                print(f"      - {job.id}: {job.name}")
            return False
        
        print(f"   Found {len(research_jobs)} research job(s):")
        for job in research_jobs:
            next_run = job.next_run_time
            if next_run:
                next_run_str = next_run.strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                next_run_str = "Not scheduled"
            print(f"      - {job.id}: {job.name}")
            print(f"        Next run: {next_run_str}")
            print(f"        Trigger: {job.trigger}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error checking scheduler: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_job_execution_logs():
    """Check in-memory job execution logs"""
    print("\n" + "=" * 70)
    print("JOB EXECUTION LOGS (In-Memory)")
    print("=" * 70)
    
    if not SCHEDULER_AVAILABLE:
        print("[SKIP] Scheduler modules not available - skipping check")
        return None  # Return None to indicate skipped
    
    try:
        logs = get_job_logs('market_research', limit=20)
        
        if not logs:
            print("[WARNING] No execution logs found for 'market_research'")
            print("   This could mean:")
            print("   - Jobs haven't run yet")
            print("   - Jobs are failing silently")
            print("   - Scheduler was restarted (logs are in-memory only)")
            return False
        
        print(f"Found {len(logs)} recent executions:\n")
        for i, log in enumerate(logs, 1):
            timestamp = log['timestamp']
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            status = "[OK]" if log['success'] else "[FAIL]"
            print(f"{i}. {status} {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print(f"   Message: {log['message']}")
            print(f"   Duration: {log['duration_ms']}ms")
            print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error checking logs: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database_articles():
    """Check if articles are in the database"""
    print("=" * 70)
    print("DATABASE ARTICLES")
    print("=" * 70)
    
    try:
        client = PostgresClient()
        
        if not client.test_connection():
            print("[FAIL] Cannot connect to PostgreSQL")
            return False
        
        print("[OK] Connected to PostgreSQL\n")
        
        # Total articles
        total_result = client.execute_query("SELECT COUNT(*) as count FROM research_articles")
        total = total_result[0]['count'] if total_result else 0
        print(f"Total articles in database: {total}")
        
        if total == 0:
            print("[WARNING] No articles found in database!")
            print("   This suggests jobs haven't saved any articles yet")
            return False
        
        # Recent articles (last 7 days)
        recent_result = client.execute_query("""
            SELECT COUNT(*) as count 
            FROM research_articles 
            WHERE fetched_at >= NOW() - INTERVAL '7 days'
        """)
        recent = recent_result[0]['count'] if recent_result else 0
        print(f"Articles fetched in last 7 days: {recent}")
        
        # Articles by type
        type_result = client.execute_query("""
            SELECT article_type, COUNT(*) as count
            FROM research_articles
            GROUP BY article_type
            ORDER BY count DESC
        """)
        if type_result:
            print("\nArticles by type:")
            for row in type_result:
                print(f"   {row['article_type']}: {row['count']}")
        
        # Latest articles
        latest_result = client.execute_query("""
            SELECT title, fetched_at, article_type, source, ticker
            FROM research_articles 
            ORDER BY fetched_at DESC 
            LIMIT 10
        """)
        
        if latest_result:
            print(f"\nLatest {len(latest_result)} articles:")
            for i, article in enumerate(latest_result, 1):
                fetched_at = article['fetched_at']
                if isinstance(fetched_at, str):
                    fetched_at = datetime.fromisoformat(fetched_at.replace('Z', '+00:00'))
                elif fetched_at.tzinfo is None:
                    fetched_at = fetched_at.replace(tzinfo=timezone.utc)
                
                print(f"\n{i}. {article['title'][:60]}...")
                print(f"   Type: {article['article_type']}")
                print(f"   Source: {article.get('source', 'N/A')}")
                print(f"   Fetched: {fetched_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                if article.get('ticker'):
                    print(f"   Ticker: {article['ticker']}")
        
        # Check for articles today
        today_result = client.execute_query("""
            SELECT COUNT(*) as count
            FROM research_articles
            WHERE DATE(fetched_at) = CURRENT_DATE
        """)
        today_count = today_result[0]['count'] if today_result else 0
        print(f"\nArticles fetched today: {today_count}")
        
        if today_count == 0 and recent > 0:
            print("[WARNING] No articles fetched today, but there are recent articles")
            print("   Jobs may not be running on schedule")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_job_dependencies():
    """Check if required services are available"""
    print("\n" + "=" * 70)
    print("DEPENDENCY CHECKS")
    print("=" * 70)
    
    issues = []
    
    # Check SearXNG
    try:
        try:
            from web_dashboard.searxng_client import check_searxng_health
        except ImportError:
            from searxng_client import check_searxng_health
        
        if check_searxng_health():
            print("[OK] SearXNG is available")
        else:
            print("[FAIL] SearXNG is NOT available")
            issues.append("SearXNG unavailable - jobs will skip execution")
    except ImportError:
        print("[WARNING] Cannot import searxng_client")
        issues.append("Missing searxng_client module")
    except Exception as e:
        print(f"[WARNING] Error checking SearXNG: {e}")
        issues.append(f"SearXNG check failed: {e}")
    
    # Check Ollama
    try:
        try:
            from web_dashboard.ollama_client import get_ollama_client
        except ImportError:
            from ollama_client import get_ollama_client
        
        ollama = get_ollama_client()
        if ollama:
            print("[OK] Ollama is available")
        else:
            print("[WARNING] Ollama is NOT available (summaries will be skipped)")
    except ImportError:
        print("[WARNING] Cannot import ollama_client")
    except Exception as e:
        print(f"[WARNING] Error checking Ollama: {e}")
    
    # Check PostgreSQL
    try:
        client = PostgresClient()
        if client.test_connection():
            print("[OK] PostgreSQL connection works")
        else:
            print("[FAIL] PostgreSQL connection failed")
            issues.append("PostgreSQL connection failed")
    except Exception as e:
        print(f"[ERROR] PostgreSQL error: {e}")
        issues.append(f"PostgreSQL error: {e}")
    
    if issues:
        print(f"\n[WARNING] Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"   - {issue}")
    
    return len(issues) == 0


def main():
    """Run all checks"""
    print("\n" + "=" * 70)
    print("RESEARCH JOBS DIAGNOSTIC")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = {
        'scheduler': check_scheduler_status(),
        'logs': check_job_execution_logs(),
        'database': check_database_articles(),
        'dependencies': check_job_dependencies()
    }
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    for check, passed in results.items():
        if passed is None:
            status = "[SKIP]"
        else:
            status = "[PASS]" if passed else "[FAIL]"
        print(f"{check.upper()}: {status}")
    
    # Only count non-None results for pass/fail
    active_results = {k: v for k, v in results.items() if v is not None}
    all_passed = all(active_results.values()) if active_results else False
    
    if all_passed:
        print("\n[OK] All checks passed! Research jobs appear to be working.")
    else:
        print("\n[WARNING] Some checks failed. Review the output above for details.")
        print("\nTroubleshooting tips:")
        print("1. Make sure the web dashboard is running (scheduler starts with it)")
        print("2. Check that RESEARCH_DATABASE_URL is set in web_dashboard/.env")
        print("3. Verify SearXNG is accessible")
        print("4. Check application logs for job execution errors")
        print("5. Manually trigger a job to test: python -c \"from web_dashboard.scheduler.jobs import market_research_job; market_research_job()\"")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

