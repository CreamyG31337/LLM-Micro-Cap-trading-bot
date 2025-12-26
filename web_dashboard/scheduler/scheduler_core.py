"""
Scheduler Core - APScheduler Configuration and Management
==========================================================

Provides the background scheduler instance and management functions.
"""

import logging
from datetime import datetime, timezone, date, timedelta
from typing import Dict, List, Optional, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

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


def start_scheduler() -> bool:
    """Start the scheduler and register default jobs.
    
    Returns True if started successfully, False if already running.
    """
    global _scheduler
    scheduler = get_scheduler()
    
    if scheduler.running:
        logger.info("Scheduler already running")
        return False
    
    # Register default jobs
    from scheduler.jobs import register_default_jobs
    register_default_jobs(scheduler)
    
    # Start scheduler
    scheduler.start()
    logger.info("✅ Background scheduler started")
    
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
    elif job_id.startswith('market_research_'):
        return 'market_research'
    elif job_id == 'ticker_research_job':
        return 'ticker_research'
    elif job_id == 'opportunity_discovery_job':
        return 'opportunity_discovery'
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
                
                # Calculate duration if we have both timestamps
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
                        duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
                    except Exception:
                        pass
                
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
    
    return {
        'id': job.id,
        'name': job.name or job.id,
        'next_run': job.next_run_time,
        'is_paused': job.next_run_time is None,
        'trigger': str(job.trigger),
        'recent_logs': get_job_logs(job.id, limit=5)
    }


def get_all_jobs_status() -> List[Dict[str, Any]]:
    """Get status of all scheduled jobs."""
    scheduler = get_scheduler()
    jobs = scheduler.get_jobs()
    
    return [get_job_status(job.id) for job in jobs if get_job_status(job.id)]


def run_job_now(job_id: str) -> bool:
    """Trigger a job to run immediately in the background.
    
    This schedules the job to run asynchronously via the scheduler's thread pool
    instead of calling it synchronously in the main thread, which prevents UI freezing.
    
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
        logger.info(f"Scheduling job for immediate async execution: {job_id}")
        
        # Use add_job with trigger='date' to run once, immediately, in background thread
        scheduler.add_job(
            job.func,
            trigger='date',  # Run once at a specific datetime (now)
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
