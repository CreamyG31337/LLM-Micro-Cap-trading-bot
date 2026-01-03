"""
Background rebuild helper - triggers incremental rebuilds as background processes.

This module provides utilities to launch rebuild_from_date.py as a background
subprocess and track its execution via the job_executions table.
"""

import subprocess
import sys
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_rebuild_job_record(fund_name: str, start_date: date) -> Optional[int]:
    """
    Create a job execution record in the database.
    
    Args:
        fund_name: Fund being rebuilt
        start_date: Start date for rebuild
        
    Returns:
        job_id: Integer ID of created job execution record, or None if failed
    """
    try:
        from web_dashboard.supabase_client import SupabaseClient
        
        client = SupabaseClient(use_service_role=True)
        
        job_data = {
            'job_name': 'rebuild_from_date',
            'target_date': start_date.isoformat(),
            'fund_name': fund_name,
            'status': 'running',  # Use 'running' instead of 'pending'
            'started_at': datetime.now(timezone.utc).isoformat()  # Use 'started_at' not 'start_time'
        }
        
        result = client.supabase.table("job_executions").insert(job_data).execute()
        
        if result.data and len(result.data) > 0:
            job_id = result.data[0].get('id')
            logger.info(f"Created job execution record: {job_id}")
            return job_id
        else:
            logger.error("Failed to create job record: no data returned")
            return None
        
    except Exception as e:
        logger.error(f"Failed to create job record: {e}")
        return None


def trigger_background_rebuild(fund_name: str, start_date: date) -> Optional[int]:
    """
    Trigger background rebuild subprocess.
    
    Checks for running rebuild jobs for the same fund and cancels them if found,
    then launches rebuild_from_date.py as a detached subprocess.
    
    Args:
        fund_name: Fund to rebuild
        start_date: Start date for rebuild (inclusive)
        
    Returns:
        job_id (integer) for tracking, or None if failed to launch
    """
    try:
        # Check for running rebuild jobs for this fund
        running_jobs = find_running_rebuild_jobs(fund_name)
        
        # Determine optimal start_date
        optimal_start_date = start_date
        cancelled_jobs = []
        
        if running_jobs:
            # Extract start_dates from running jobs (from target_date column)
            running_start_dates = []
            for job in running_jobs:
                target_date_str = job.get("target_date")
                if target_date_str:
                    try:
                        running_start_date = datetime.fromisoformat(target_date_str).date()
                        running_start_dates.append(running_start_date)
                    except (ValueError, AttributeError):
                        logger.warning(f"Could not parse target_date from job {job.get('id')}")
            
            if running_start_dates:
                # Use the minimum of new trade date and all running job start dates
                optimal_start_date = min(start_date, min(running_start_dates))
                logger.info(f"Found {len(running_jobs)} running rebuild job(s). Optimal start_date: {optimal_start_date}")
            
            # Cancel all running jobs
            for job in running_jobs:
                job_id_to_cancel = job.get("id")
                if job_id_to_cancel:
                    reason = f"New backdated trade entered (date: {start_date}). Restarting rebuild from {optimal_start_date}."
                    if cancel_rebuild_job(job_id_to_cancel, reason):
                        cancelled_jobs.append(job_id_to_cancel)
        
        # Create job execution record with optimal start_date
        job_id = create_rebuild_job_record(fund_name, optimal_start_date)
        if not job_id:
            logger.error("Failed to create job record, cannot launch rebuild")
            return None
        
        # Get path to rebuild script
        script_path = Path(__file__).parent / "rebuild_from_date.py"
        if not script_path.exists():
            logger.error(f"Rebuild script not found: {script_path}")
            return None
        
        # Build command with optimal start_date
        cmd = [
            sys.executable,
            str(script_path),
            fund_name,
            optimal_start_date.isoformat(),
            '--job-id', str(job_id)  # Convert to string for command line
        ]
        
        # Launch subprocess (detached)
        # On Windows: use CREATE_NEW_PROCESS_GROUP
        # On Unix: use start_new_session
        import os
        if os.name == 'nt':
            # Windows
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
                cwd=str(Path(__file__).parent.parent.parent)
            )
        else:
            # Unix/Linux/Docker
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                cwd=str(Path(__file__).parent.parent.parent)
            )
        
        logger.info(f"Launched rebuild subprocess (PID: {process.pid}, Job ID: {job_id})")
        
        return job_id
        
    except Exception as e:
        logger.error(f"Failed to launch rebuild subprocess: {e}", exc_info=True)
        return None


def get_job_status(job_id: str) -> Optional[dict]:
    """
    Get status of a job execution.
    
    Args:
        job_id: Job execution ID (can be string or int)
        
    Returns:
        Job data dict or None if not found
    """
    try:
        from web_dashboard.supabase_client import SupabaseClient
        
        client = SupabaseClient(use_service_role=True)
        # Convert to int if it's a string
        job_id_int = int(job_id) if isinstance(job_id, str) else job_id
        result = client.supabase.table("job_executions").select("*").eq("id", job_id_int).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            return None
            
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return None


def find_running_rebuild_jobs(fund_name: str) -> list:
    """
    Find all running rebuild jobs for a specific fund.
    
    Args:
        fund_name: Fund name to search for
        
    Returns:
        List of job records with 'id' and 'target_date'
    """
    try:
        from web_dashboard.supabase_client import SupabaseClient
        
        client = SupabaseClient(use_service_role=True)
        
        # Query for rebuild jobs with running status, filtered by fund_name
        result = client.supabase.table("job_executions") \
            .select("id, status, target_date, fund_name, started_at") \
            .eq("job_name", "rebuild_from_date") \
            .eq("status", "running") \
            .eq("fund_name", fund_name) \
            .execute()
        
        if not result.data:
            return []
        
        logger.info(f"Found {len(result.data)} running rebuild jobs for {fund_name}")
        return result.data
        
    except Exception as e:
        logger.error(f"Failed to find running rebuild jobs: {e}")
        return []


def cancel_rebuild_job(job_id: str, reason: str) -> bool:
    """
    Cancel a running rebuild job by marking it as failed with cancellation reason.
    
    Args:
        job_id: Job execution ID (can be string or int)
        reason: Reason for cancellation
        
    Returns:
        True if cancellation succeeded, False otherwise
    """
    try:
        from web_dashboard.supabase_client import SupabaseClient
        from datetime import datetime, timezone
        
        client = SupabaseClient(use_service_role=True)
        
        # Convert to int if it's a string
        job_id_int = int(job_id) if isinstance(job_id, str) else job_id
        
        # First check if job is still running
        job = get_job_status(job_id)
        if not job:
            logger.warning(f"Job {job_id} not found, cannot cancel")
            return False
        
        current_status = job.get("status")
        if current_status != "running":
            logger.info(f"Job {job_id} is already {current_status}, no need to cancel")
            return True  # Already done, consider it successful
        
        # Mark as failed with cancellation reason
        cancellation_message = f"Cancelled: {reason}"
        client.supabase.table("job_executions").update({
            'status': 'failed',
            'error_message': cancellation_message,  # Use error_message instead of output
            'completed_at': datetime.now(timezone.utc).isoformat()  # Use completed_at instead of end_time
        }).eq('id', job_id_int).execute()
        
        logger.info(f"Cancelled rebuild job {job_id}: {reason}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to cancel rebuild job {job_id}: {e}")
        return False