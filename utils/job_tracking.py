"""
Job Execution Tracking Utilities
=================================

Centralized functions for tracking job execution status across web dashboard
and console app. Enables detection of incomplete runs when Docker crashes.

Usage:
    from utils.job_tracking import mark_job_started, mark_job_completed
    
    mark_job_started('update_portfolio_prices', target_date)
    try:
        # ... process data ...
        mark_job_completed('update_portfolio_prices', target_date, None, funds_completed)
    except Exception as e:
        mark_job_failed('update_portfolio_prices', target_date, None, str(e))
        raise
"""

import logging
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def mark_job_started(
    job_name: str,
    target_date: date,
    fund_name: Optional[str] = None
) -> None:
    """
    Mark a job as started (status='running').
    
    Args:
        job_name: Name of the job (e.g., 'update_portfolio_prices')
        target_date: Date the job is processing
        fund_name: Specific fund being processed, None if all funds
    """
    from supabase_client import SupabaseClient
    
    try:
        client = SupabaseClient()
        client.supabase.table("job_executions").upsert({
            'job_name': job_name,
            'target_date': target_date.isoformat(),
            'fund_name': fund_name,
            'status': 'running',
            'started_at': datetime.now(timezone.utc).isoformat()
        }, on_conflict='job_name,target_date,fund_name').execute()
        
        logger.debug(f"Marked job '{job_name}' as started for {target_date}")
    except Exception as e:
        # Don't fail the job if tracking fails
        logger.warning(f"Failed to mark job started: {e}")


def mark_job_completed(
    job_name: str,
    target_date: date,
    fund_name: Optional[str],
    funds_processed: List[str]
) -> None:
    """
    Mark a job as successfully completed.
    
    Args:
        job_name: Name of the job
        target_date: Date the job processed
        fund_name: Specific fund processed, None if all funds
        funds_processed: List of fund names that completed successfully
    """
    from supabase_client import SupabaseClient
    
    try:
        client = SupabaseClient()
        
        # First check if there's an existing entry
        result = client.supabase.table("job_executions")\
            .select("id")\
            .eq("job_name", job_name)\
            .eq("target_date", target_date.isoformat())
        
        if fund_name is not None:
            result = result.eq("fund_name", fund_name)
        else:
            result = result.is_("fund_name", "null")
        
        result = result.execute()
        
        # Update existing or insert new
        data = {
            'job_name': job_name,
            'target_date': target_date.isoformat(),
            'fund_name': fund_name,
            'status': 'success',
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'funds_processed': funds_processed
        }
        
        client.supabase.table("job_executions").upsert(
            data,
            on_conflict='job_name,target_date,fund_name'
        ).execute()
        
        logger.debug(f"Marked job '{job_name}' as completed for {target_date}")
    except Exception as e:
        logger.warning(f"Failed to mark job completed: {e}")


def mark_job_failed(
    job_name: str,
    target_date: date,
    fund_name: Optional[str],
    error: str
) -> None:
    """
    Mark a job as failed with error message.
    
    Args:
        job_name: Name of the job
        target_date: Date the job was processing
        fund_name: Specific fund being processed, None if all funds
        error: Error message
    """
    from supabase_client import SupabaseClient
    
    try:
        client = SupabaseClient()
        client.supabase.table("job_executions").upsert({
            'job_name': job_name,
            'target_date': target_date.isoformat(),
            'fund_name': fund_name,
            'status': 'failed',
            'completed_at': datetime.now(timezone.utc).isoformat(),
            'error_message': error[:500]  # Truncate to prevent huge error strings
        }, on_conflict='job_name,target_date,fund_name').execute()
        
        logger.debug(f"Marked job '{job_name}' as failed for {target_date}")
    except Exception as e:
        logger.warning(f"Failed to mark job as failed: {e}")


def is_job_completed(
    job_name: str,
    target_date: date,
    fund_name: Optional[str] = None
) -> bool:
    """
    Check if a job completed successfully for a specific date.
    
    Args:
        job_name: Name of the job
        target_date: Date to check
        fund_name: Specific fund to check, None if checking all-funds job
        
    Returns:
        True if job completed successfully, False otherwise
    """
    from supabase_client import SupabaseClient
    
    try:
        client = SupabaseClient()
        result = client.supabase.table("job_executions")\
            .select("status")\
            .eq("job_name", job_name)\
            .eq("target_date", target_date.isoformat())\
            .eq("status", "success")
        
        if fund_name is not None:
            result = result.eq("fund_name", fund_name)
        else:
            result = result.is_("fund_name", "null")
        
        result = result.execute()
        
        return bool(result.data)
    except Exception as e:
        logger.warning(f"Failed to check job completion: {e}")
        # If tracking check fails, assume not completed (safe default)
        return False


def get_incomplete_jobs(
    job_name: str,
    since_date: date
) -> List[Dict[str, Any]]:
    """
    Get all jobs with status='running' or 'failed' since a given date.
    
    Used to detect crashed jobs (status still 'running' for old dates).
    
    Args:
        job_name: Name of the job to check
        since_date: Only return jobs from this date onwards
        
    Returns:
        List of job execution records that are incomplete
    """
    from supabase_client import SupabaseClient
    
    try:
        client = SupabaseClient()
        result = client.supabase.table("job_executions")\
            .select("*")\
            .eq("job_name", job_name)\
            .gte("target_date", since_date.isoformat())\
            .in_("status", ["running", "failed"])\
            .execute()
        
        return result.data if result.data else []
    except Exception as e:
        logger.warning(f"Failed to get incomplete jobs: {e}")
        return []


def cleanup_stale_running_jobs(max_age_hours: int = 24) -> int:
    """
    Mark old 'running' jobs as 'failed' (assume they crashed).
    
    Jobs that have been 'running' for more than max_age_hours are
    assumed to have crashed and are marked as failed.
    
    Args:
        max_age_hours: Consider jobs older than this as crashed
        
    Returns:
        Number of jobs cleaned up
    """
    from supabase_client import SupabaseClient
    
    try:
        client = SupabaseClient()
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        cutoff_dt = datetime.fromtimestamp(cutoff_time, tz=timezone.utc)
        
        # Find stale running jobs
        result = client.supabase.table("job_executions")\
            .select("id")\
            .eq("status", "running")\
            .lt("started_at", cutoff_dt.isoformat())\
            .execute()
        
        if not result.data:
            return 0
        
        # Mark them as failed
        for job in result.data:
            client.supabase.table("job_executions")\
                .update({
                    'status': 'failed',
                    'completed_at': datetime.now(timezone.utc).isoformat(),
                    'error_message': f'Job stale (running > {max_age_hours}h)'
                })\
                .eq("id", job['id'])\
                .execute()
        
        count = len(result.data)
        logger.info(f"Cleaned up {count} stale running jobs")
        return count
    except Exception as e:
        logger.warning(f"Failed to cleanup stale jobs: {e}")
        return 0
