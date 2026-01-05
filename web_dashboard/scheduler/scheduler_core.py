"""
Scheduler Core - APScheduler Configuration and Management
==========================================================

Provides the background scheduler instance and management functions.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

# Add project root to path for utils imports
current_dir = Path(__file__).resolve().parent
if current_dir.name == 'scheduler':
    project_root = current_dir.parent.parent
else:
    project_root = current_dir.parent.parent

# CRITICAL: Project root must be FIRST in sys.path to ensure utils.job_tracking
# is found from the project root, not from web_dashboard/utils
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
elif sys.path[0] != str(project_root):
    # If it is in path but not first, move it to front
    if str(project_root) in sys.path:
        sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))

# Also ensure web_dashboard is in path for supabase_client imports
# (but AFTER project root so it doesn't shadow utils)
web_dashboard_path = str(current_dir.parent)
if web_dashboard_path not in sys.path:
    sys.path.insert(1, web_dashboard_path)  # Insert at index 1, after project_root

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None

# Job execution log (in-memory, last N executions)
_job_logs: Dict[str, List[Dict[str, Any]]] = {}
MAX_LOG_ENTRIES = 50


def get_scheduler() -> BackgroundScheduler:
    """Get or create the scheduler instance."""
    global _scheduler
    
    if _scheduler is None:
        jobstores = {
            'default': MemoryJobStore()
        }
        executors = {
            'default': ThreadPoolExecutor(max_workers=3)
        }
        job_defaults = {
            'coalesce': True,  # Combine multiple missed executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 60 * 5  # 5 minute grace period for misfires
        }
        
        _scheduler = BackgroundScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='America/Los_Angeles'  # Pacific Time
        )
        
        logger.info("Created new BackgroundScheduler instance")
    
    return _scheduler


def cleanup_stale_running_jobs() -> int:
    """Clean up stale 'running' jobs on startup and add to retry queue.
    
    When the container restarts, any jobs that were running are interrupted.
    This function:
    1. Marks them as failed in job_executions
    2. Adds calculation jobs to retry queue
    3. Deletes the stale records
    
    Returns:
        Number of stale jobs cleaned up
    """
    try:
        from supabase_client import SupabaseClient
        from utils.job_tracking import add_to_retry_queue, is_calculation_job, mark_job_failed
        from datetime import datetime
        
        client = SupabaseClient(use_service_role=True)
        
        # Find all jobs still marked as running
        result = client.supabase.table("job_executions")\
            .select("id, job_name, target_date, fund_name, started_at")\
            .eq("status", "running")\
            .execute()
        
        if not result.data:
            logger.info("No stale running jobs to clean up")
            return 0
        
        count = len(result.data)
        logger.info(f"Found {count} stale 'running' job(s), cleaning up...")
        
        # Process each stale job
        for job in result.data:
            job_name = job['job_name']
            target_date_str = job.get('target_date')
            fund_name = job.get('fund_name') or None
            
            # Mark as failed in job_executions
            if target_date_str:
                try:
                    target_date = datetime.fromisoformat(target_date_str).date()
                    mark_job_failed(
                        job_name=job_name,
                        target_date=target_date,
                        fund_name=fund_name,
                        error="Container restarted - job interrupted"
                    )
                except Exception as e:
                    logger.warning(f"  Failed to mark {job_name} as failed: {e}")
            
            # Add to retry queue if calculation job
            if target_date_str and is_calculation_job(job_name):
                try:
                    target_date = datetime.fromisoformat(target_date_str).date()
                    entity_id = fund_name if fund_name else None
                    entity_type = 'fund' if fund_name else 'all_funds'
                    
                    add_to_retry_queue(
                        job_name=job_name,
                        target_date=target_date,
                        entity_id=entity_id,
                        entity_type=entity_type,
                        failure_reason='container_restart',
                        error_message='Job interrupted by container restart'
                    )
                    logger.info(f"  📝 Added {job_name} {target_date} to retry queue")
                except Exception as e:
                    logger.error(f"  ❌ Failed to add {job_name} to retry queue: {e}")
            
            # Delete the stale record
            client.supabase.table("job_executions")\
                .delete()\
                .eq("id", job['id'])\
                .execute()
            
            logger.info(f"  ✓ Cleaned up stale run for {job_name} (started: {job.get('started_at')})")
        
        logger.info(f"✅ Cleaned up {count} stale running job records")
        return count
        
    except Exception as e:
        logger.error(f"Failed to clean up stale running jobs: {e}")
        return 0


def start_scheduler() -> bool:
    """Start the scheduler and register default jobs.
    
    Returns True if started successfully, False if already running.
    """
    global _scheduler
    scheduler = get_scheduler()
    
    if scheduler.running:
        logger.info("Scheduler already running")
        return False
    
    # Clean up any stale 'running' jobs from previous container run
    cleanup_stale_running_jobs()
    
    # Register default jobs
    from scheduler.jobs import register_default_jobs
    register_default_jobs(scheduler)
    
    # Start scheduler
    scheduler.start()
    logger.info("✅ Background scheduler started")
    
    # Log startup summary with all registered jobs
    jobs = scheduler.get_jobs()
    logger.info("="*50)
    logger.info(f"✅ SCHEDULER STARTED - {len(jobs)} jobs registered")
    for job in jobs:
        next_run = job.next_run_time.strftime('%Y-%m-%d %H:%M %Z') if job.next_run_time else 'PAUSED'
        logger.info(f"   📋 {job.id}: {next_run}")
    logger.info("="*50)
    
    # Run backfill check once on startup (catches downtime/reboots)
    # This runs asynchronously to not block scheduler startup
    from scheduler.backfill import startup_backfill_check
    scheduler.add_job(
        startup_backfill_check,
        trigger='date',  # Run once immediately
        id='startup_backfill',
        name='Startup Backfill Check'
    )
    logger.info("📋 Scheduled startup backfill check")
    
    return True


def shutdown_scheduler() -> None:
    """Gracefully shutdown the scheduler."""
    global _scheduler
    
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")


def log_job_execution(job_id: str, success: bool, message: str, duration_ms: int = 0) -> None:
    """Log a job execution result."""
    global _job_logs
    
    if job_id not in _job_logs:
        _job_logs[job_id] = []
    
    log_entry = {
        'timestamp': datetime.now(timezone.utc),
        'success': success,
        'message': message,
        'duration_ms': duration_ms
    }
    
    _job_logs[job_id].insert(0, log_entry)
    
    # Trim old entries
    if len(_job_logs[job_id]) > MAX_LOG_ENTRIES:
        _job_logs[job_id] = _job_logs[job_id][:MAX_LOG_ENTRIES]


def _map_job_id_to_job_name(job_id: str) -> str:
    """Map scheduler job ID to job_executions.job_name.
    
    Some scheduler job IDs have variants (e.g., 'update_portfolio_prices_close')
    that map to the same job_name in the database.
    
    Args:
        job_id: The scheduler job ID
        
    Returns:
        The job_name to use in job_executions table
    """
    # Handle special cases for job variants
    if job_id == 'update_portfolio_prices_close':
        return 'update_portfolio_prices'
    elif job_id.startswith('market_research_collect_'):
        return 'market_research'
    # Remove verb suffixes to get base job name for grouping
    # This allows variants to be grouped together in the database
    if job_id.endswith('_refresh'):
        return job_id[:-8]  # Remove '_refresh'
    elif job_id.endswith('_populate'):
        return job_id[:-9]  # Remove '_populate'
    elif job_id.endswith('_collect'):
        return job_id[:-8]  # Remove '_collect'
    elif job_id.endswith('_scan'):
        return job_id[:-5]  # Remove '_scan'
    elif job_id.endswith('_fetch'):
        return job_id[:-6]  # Remove '_fetch'
    elif job_id.endswith('_cleanup'):
        return job_id[:-8]  # Remove '_cleanup'
    # Default: use job_id as-is
    return job_id


def get_job_logs(job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent execution logs for a job.
    
    Reads from both:
    1. Database job_executions table (persistent, survives restarts)
    2. In-memory _job_logs (recent executions in current session)
    
    Args:
        job_id: The scheduler job ID
        limit: Maximum number of logs to return
        
    Returns:
        List of log entries with keys: timestamp, success, message, duration_ms
    """
    job_name = _map_job_id_to_job_name(job_id)
    logs: List[Dict[str, Any]] = []
    
    # First, try to read from database (persistent)
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Get recent successful/failed executions from database
        # Use completed_at for ordering (most recent first)
        result = client.supabase.table("job_executions")\
            .select("*")\
            .eq("job_name", job_name)\
            .in_("status", ["success", "failed"])\
            .order("completed_at", desc=True)\
            .limit(limit)\
            .execute()
        
        if result.data:
            for record in result.data:
                # Convert database record to log format
                completed_at = record.get('completed_at')
                if completed_at:
                    try:
                        # Parse timestamp string to datetime
                        if isinstance(completed_at, str):
                            # Handle ISO format strings
                            timestamp = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                        else:
                            timestamp = completed_at
                    except Exception:
                        # Fallback to current time if parsing fails
                        timestamp = datetime.now(timezone.utc)
                else:
                    timestamp = datetime.now(timezone.utc)
                
                status = record.get('status', 'failed')
                success = (status == 'success')
                
                # Build message from error_message or funds_processed
                message = record.get('error_message', '')
                if not message and record.get('funds_processed'):
                    funds = record.get('funds_processed', [])
                    if isinstance(funds, list) and funds:
                        message = f"Processed {len(funds)} fund(s)"
                    else:
                        message = "Completed successfully"
                elif not message:
                    message = "Completed successfully" if success else "Job failed"
                
                # Use stored duration_ms if available, otherwise calculate from timestamps
                duration_ms = record.get('duration_ms')
                if duration_ms is None:
                    # Fallback: calculate from timestamps if duration_ms not stored
                    duration_ms = 0
                    started_at = record.get('started_at')
                    if started_at and completed_at:
                        try:
                            # Parse started_at
                            if isinstance(started_at, str):
                                start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                            else:
                                start_dt = started_at
                            
                            # Parse completed_at
                            if isinstance(completed_at, str):
                                end_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                            else:
                                end_dt = completed_at
                            
                            # Ensure both are timezone-aware (UTC)
                            if start_dt.tzinfo is None:
                                start_dt = start_dt.replace(tzinfo=timezone.utc)
                            else:
                                start_dt = start_dt.astimezone(timezone.utc)
                            
                            if end_dt.tzinfo is None:
                                end_dt = end_dt.replace(tzinfo=timezone.utc)
                            else:
                                end_dt = end_dt.astimezone(timezone.utc)
                            
                            # Calculate duration and ensure it's never negative
                            delta = end_dt - start_dt
                            duration_seconds = delta.total_seconds()
                            duration_ms = max(0, int(duration_seconds * 1000))  # Clamp to 0 if negative
                        except Exception as e:
                            logger.debug(f"Error calculating duration: {e}")
                            duration_ms = 0
                else:
                    # Ensure stored duration is never negative
                    duration_ms = max(0, int(duration_ms))
                
                logs.append({
                    'timestamp': timestamp,
                    'success': success,
                    'message': message,
                    'duration_ms': duration_ms
                })
    except Exception as e:
        logger.warning(f"Failed to read job logs from database for {job_id}: {e}")
    
    # Also include in-memory logs (for very recent executions not yet in DB)
    # Merge and deduplicate by timestamp
    in_memory_logs = _job_logs.get(job_id, [])
    for mem_log in in_memory_logs:
        # Check if we already have this log from database
        mem_ts = mem_log.get('timestamp')
        if mem_ts:
            # Check if timestamp is close to any existing log (within 1 second)
            is_duplicate = False
            for existing_log in logs:
                existing_ts = existing_log.get('timestamp')
                if existing_ts and abs((mem_ts - existing_ts).total_seconds()) < 1:
                    is_duplicate = True
                    break
            if not is_duplicate:
                logs.append(mem_log)
    
    # Sort by timestamp (most recent first) and limit
    logs.sort(key=lambda x: x.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    return logs[:limit]


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get status of a specific job."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        return None
    
    # Map job_id to job_name for database lookup
    job_name = _map_job_id_to_job_name(job_id)
    
    # Check if job is currently running
    is_running = False
    running_since = None
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Query for running executions
        running_result = client.supabase.table("job_executions")\
            .select("started_at")\
            .eq("job_name", job_name)\
            .eq("status", "running")\
            .order("started_at", desc=True)\
            .limit(1)\
            .execute()
        
        if running_result.data and len(running_result.data) > 0:
            started_at = running_result.data[0].get('started_at')
            if started_at:
                try:
                    if isinstance(started_at, str):
                        running_since = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    else:
                        running_since = started_at
                    
                    # Ensure timezone awareness
                    if running_since.tzinfo is None:
                        running_since = running_since.replace(tzinfo=timezone.utc)
                    else:
                        running_since = running_since.astimezone(timezone.utc)
                        
                    # Ignore if older than 6 hours (likely stale/crashed)
                    now_utc = datetime.now(timezone.utc)
                    if (now_utc - running_since).total_seconds() < 6 * 3600:
                        is_running = True
                    else:
                         # It's stale - ignore it for UI purposes
                         # (Cleanup job will eventually catch it on restart, or we could trigger cleanup here)
                         is_running = False
                         logger.debug(f"Ignoring stale running status for {job_id} (started {running_since})")

                except Exception as e:
                    logger.warning(f"Error parsing running_since for {job_id}: {e}")
                    pass
    except Exception as e:
        logger.warning(f"Failed to check running status for {job_id}: {e}")
    
    # Get last error from failed executions
    last_error = None
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Query for most recent failed execution
        failed_result = client.supabase.table("job_executions")\
            .select("error_message, completed_at")\
            .eq("job_name", job_name)\
            .eq("status", "failed")\
            .order("completed_at", desc=True)\
            .limit(1)\
            .execute()
        
        if failed_result.data and len(failed_result.data) > 0:
            last_error = failed_result.data[0].get('error_message')
    except Exception as e:
        logger.warning(f"Failed to fetch last error for {job_id}: {e}")
    
    return {
        'id': job.id,
        'name': job.name or job.id,
        'next_run': job.next_run_time,
        'is_paused': job.next_run_time is None,
        'trigger': str(job.trigger),
        'is_running': is_running,
        'running_since': running_since,
        'last_error': last_error,
        'recent_logs': get_job_logs(job.id, limit=5)
    }


def get_all_jobs_status_batched() -> List[Dict[str, Any]]:
    """Get status of all scheduled jobs using batched database queries for performance.
    
    This is an optimized version that makes 3-5 total queries instead of N queries per job.
    Reduces load time from 20+ seconds to <1 second for 10+ jobs.
    
    Returns:
        List of job status dictionaries
    """
    import time
    start_time = time.perf_counter()
    
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    
    if not jobs:
        return []
    
    # Map all job IDs to job names
    job_id_to_name = {}
    job_id_to_job = {}
    job_names = set()
    
    for job in jobs:
        job_name = _map_job_id_to_job_name(job.id)
        job_id_to_name[job.id] = job_name
        job_id_to_job[job.id] = job
        job_names.add(job_name)
    
    job_names_list = list(job_names)
    
    # Initialize result structure
    job_statuses = {}
    for job in jobs:
        job_statuses[job.id] = {
            'id': job.id,
            'name': job.name or job.id,
            'next_run': job.next_run_time,
            'is_paused': job.next_run_time is None,
            'trigger': str(job.trigger),
            'is_running': False,
            'running_since': None,
            'last_error': None,
            'recent_logs': []
        }
    
    # Batch query 1: Get all running jobs
    running_jobs = {}
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Get all running executions for our job names
        running_result = client.supabase.table("job_executions")\
            .select("job_name, started_at")\
            .in_("job_name", job_names_list)\
            .eq("status", "running")\
            .order("started_at", desc=True)\
            .execute()
        
        if running_result.data:
            # Group by job_name, keeping only the most recent for each
            job_name_to_latest = {}
            for record in running_result.data:
                job_name = record.get('job_name')
                if job_name not in job_name_to_latest:
                    job_name_to_latest[job_name] = record
            
            # Map back to job IDs and check if still valid (not stale)
            now_utc = datetime.now(timezone.utc)
            for job_id, job_name in job_id_to_name.items():
                if job_name in job_name_to_latest:
                    record = job_name_to_latest[job_name]
                    started_at = record.get('started_at')
                    if started_at:
                        try:
                            if isinstance(started_at, str):
                                running_since = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                            else:
                                running_since = started_at
                            
                            if running_since.tzinfo is None:
                                running_since = running_since.replace(tzinfo=timezone.utc)
                            else:
                                running_since = running_since.astimezone(timezone.utc)
                            
                            # Ignore if older than 6 hours (stale)
                            if (now_utc - running_since).total_seconds() < 6 * 3600:
                                job_statuses[job_id]['is_running'] = True
                                job_statuses[job_id]['running_since'] = running_since
                        except Exception as e:
                            logger.debug(f"Error parsing running_since for {job_id}: {e}")
    except Exception as e:
        logger.warning(f"Failed to batch query running jobs: {e}")
    
    # Batch query 2: Get most recent execution status (to check for errors vs success)
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Get most recent execution (success or failed) for each job
        # We need to see if the *last* run was a failure
        status_result = client.supabase.table("job_executions")\
            .select("job_name, status, error_message, completed_at")\
            .in_("job_name", job_names_list)\
            .in_("status", ["success", "failed"])\
            .order("completed_at", desc=True)\
            .limit(200)\
            .execute()
        
        if status_result.data:
            # Group by job_name, keeping only the absolute most recent for each
            job_name_to_latest_status = {}
            for record in status_result.data:
                job_name = record.get('job_name')
                # Since we ordered by completed_at desc, the first one we see is the latest
                if job_name not in job_name_to_latest_status:
                    job_name_to_latest_status[job_name] = record
            
            # Map back to job IDs
            for job_id, job_name in job_id_to_name.items():
                if job_name in job_name_to_latest_status:
                    latest = job_name_to_latest_status[job_name]
                    # Only show error if the MOST RECENT execution was a failure
                    if latest.get('status') == 'failed':
                        job_statuses[job_id]['last_error'] = latest.get('error_message')
                    else:
                        # Job succeeded recently, so clear any error status
                        job_statuses[job_id]['last_error'] = None
    except Exception as e:
        logger.warning(f"Failed to batch query last errors: {e}")
    
    # Batch query 3: Get recent logs for all jobs
    # We'll get recent executions and group by job_name in memory
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        
        # Get recent successful/failed executions for all our jobs
        # Get more than we need, then group by job_name
        logs_result = client.supabase.table("job_executions")\
            .select("*")\
            .in_("job_name", job_names_list)\
            .in_("status", ["success", "failed"])\
            .order("completed_at", desc=True)\
            .limit(200)\
            .execute()  # Get enough to have recent logs for each job
        
        if logs_result.data:
            # Group logs by job_name, keeping most recent per job
            job_name_to_logs = {}
            for record in logs_result.data:
                job_name = record.get('job_name')
                if job_name not in job_name_to_logs:
                    job_name_to_logs[job_name] = []
                job_name_to_logs[job_name].append(record)
            
            # Process logs for each job (limit to 5 per job)
            for job_id, job_name in job_id_to_name.items():
                if job_name in job_name_to_logs:
                    logs = []
                    for record in job_name_to_logs[job_name][:5]:  # Limit to 5 per job
                        # Convert database record to log format (same logic as get_job_logs)
                        completed_at = record.get('completed_at')
                        if completed_at:
                            try:
                                if isinstance(completed_at, str):
                                    timestamp = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                                else:
                                    timestamp = completed_at
                            except Exception:
                                timestamp = datetime.now(timezone.utc)
                        else:
                            timestamp = datetime.now(timezone.utc)
                        
                        status = record.get('status', 'failed')
                        success = (status == 'success')
                        
                        message = record.get('error_message', '')
                        if not message and record.get('funds_processed'):
                            funds = record.get('funds_processed', [])
                            if isinstance(funds, list) and funds:
                                message = f"Processed {len(funds)} fund(s)"
                            else:
                                message = "Completed successfully"
                        elif not message:
                            message = "Completed successfully" if success else "Job failed"
                        
                        duration_ms = record.get('duration_ms')
                        if duration_ms is None:
                            duration_ms = 0
                            started_at = record.get('started_at')
                            if started_at and completed_at:
                                try:
                                    if isinstance(started_at, str):
                                        start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                                    else:
                                        start_dt = started_at
                                    
                                    if isinstance(completed_at, str):
                                        end_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                                    else:
                                        end_dt = completed_at
                                    
                                    if start_dt.tzinfo is None:
                                        start_dt = start_dt.replace(tzinfo=timezone.utc)
                                    else:
                                        start_dt = start_dt.astimezone(timezone.utc)
                                    
                                    if end_dt.tzinfo is None:
                                        end_dt = end_dt.replace(tzinfo=timezone.utc)
                                    else:
                                        end_dt = end_dt.astimezone(timezone.utc)
                                    
                                    delta = end_dt - start_dt
                                    duration_seconds = delta.total_seconds()
                                    duration_ms = max(0, int(duration_seconds * 1000))
                                except Exception:
                                    duration_ms = 0
                        else:
                            duration_ms = max(0, int(duration_ms))
                        
                        logs.append({
                            'timestamp': timestamp,
                            'success': success,
                            'message': message,
                            'duration_ms': duration_ms
                        })
                    
                    job_statuses[job_id]['recent_logs'] = logs
    except Exception as e:
        logger.warning(f"Failed to batch query job logs: {e}")
    
    # Also include in-memory logs (for very recent executions not yet in DB)
    for job_id in job_statuses.keys():
        in_memory_logs = _job_logs.get(job_id, [])
        existing_logs = job_statuses[job_id]['recent_logs']
        
        # Merge and deduplicate
        for mem_log in in_memory_logs:
            mem_ts = mem_log.get('timestamp')
            if mem_ts:
                is_duplicate = False
                for existing_log in existing_logs:
                    existing_ts = existing_log.get('timestamp')
                    if existing_ts and abs((mem_ts - existing_ts).total_seconds()) < 1:
                        is_duplicate = True
                        break
                if not is_duplicate:
                    existing_logs.append(mem_log)
        
        # Sort and limit
        existing_logs.sort(key=lambda x: x.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        job_statuses[job_id]['recent_logs'] = existing_logs[:5]
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"⏱️ get_all_jobs_status_batched: {elapsed_ms:.2f}ms for {len(jobs)} jobs")
    
    return list(job_statuses.values())


def get_all_jobs_status() -> List[Dict[str, Any]]:
    """Get status of all scheduled jobs.
    
    Uses batched queries for performance. For single job queries, use get_job_status().
    """
    return get_all_jobs_status_batched()


def run_job_now(job_id: str, **kwargs) -> bool:
    """Trigger a job to run immediately in the background.
    
    This schedules the job to run asynchronously via the scheduler's thread pool
    instead of calling it synchronously in the main thread, which prevents UI freezing.
    
    Args:
        job_id: The job identifier
        **kwargs: Arguments to pass to the job function
    
    Returns True if job was scheduled, False if job not found.
    """
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        logger.warning(f"Job not found: {job_id}")
        return False
    
    # Schedule the job to run ASYNCHRONOUSLY via the scheduler
    # This prevents blocking the main thread (and the UI)
    try:
        logger.info(f"Scheduling job for immediate async execution: {job_id} (args: {kwargs})")
        
        # Use add_job with trigger='date' to run once, immediately, in background thread
        scheduler.add_job(
            job.func,
            trigger='date',  # Run once at a specific datetime (now)
            kwargs=kwargs,   # Pass keyword arguments to function
            id=f"{job_id}_manual_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            name=f"Manual: {job.name or job_id}",
            replace_existing=False  # Allow multiple manual runs
        )
        
        logger.info(f"Job {job_id} scheduled for async execution")
        return True
    except Exception as e:
        logger.error(f"Error scheduling job {job_id}: {e}")
        return False


def pause_job(job_id: str) -> bool:
    """Pause a scheduled job."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        return False
    
    scheduler.pause_job(job_id)
    logger.info(f"Paused job: {job_id}")
    return True


def resume_job(job_id: str) -> bool:
    """Resume a paused job."""
    scheduler = get_scheduler()
    job = scheduler.get_job(job_id)
    
    if not job:
        return False
    
    scheduler.resume_job(job_id)
    logger.info(f"Resumed job: {job_id}")
    return True
