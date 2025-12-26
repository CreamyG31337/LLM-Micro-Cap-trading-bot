"""
Scheduler Core - APScheduler Configuration and Management
==========================================================

Provides the background scheduler instance and management functions.
"""

import logging
from datetime import datetime, timezone
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


def get_job_logs(job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent execution logs for a job."""
    return _job_logs.get(job_id, [])[:limit]


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
