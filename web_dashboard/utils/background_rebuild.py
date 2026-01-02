"""
Background rebuild helper - triggers incremental rebuilds as background processes.

This module provides utilities to launch rebuild_from_date.py as a background
subprocess and track its execution via the job_executions table.
"""

import subprocess
import sys
import uuid
from pathlib import Path
from datetime import date, datetime, timezone
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def create_rebuild_job_record(fund_name: str, start_date: date) -> str:
    """
    Create a job execution record in the database.
    
    Args:
        fund_name: Fund being rebuilt
        start_date: Start date for rebuild
        
    Returns:
        job_id: UUID of created job execution record
    """
    try:
        from web_dashboard.supabase_client import SupabaseClient
        
        client = SupabaseClient(use_service_role=True)
        job_id = str(uuid.uuid4())
        
        job_data = {
            'id': job_id,
            'job_name': 'rebuild_from_date',
            'status': 'pending',
            'start_time': datetime.now(timezone.utc).isoformat(),
            'output': f'Initializing rebuild for {fund_name} from {start_date}',
            'metadata': {
                'fund': fund_name,
                'start_date': start_date.isoformat(),
                'trigger': 'backdated_trade'
            }
        }
        
        client.supabase.table("job_executions").insert(job_data).execute()
        logger.info(f"Created job execution record: {job_id}")
        
        return job_id
        
    except Exception as e:
        logger.error(f"Failed to create job record: {e}")
        # Return a dummy ID and proceed anyway
        return str(uuid.uuid4())


def trigger_background_rebuild(fund_name: str, start_date: date) -> Optional[str]:
    """
    Trigger background rebuild subprocess.
    
    Launches rebuild_from_date.py as a detached subprocess and returns
    immediately. The job can be monitored via the job_executions table.
    
    Args:
        fund_name: Fund to rebuild
        start_date: Start date for rebuild (inclusive)
        
    Returns:
        job_id for tracking, or None if failed to launch
    """
    try:
        # Create job execution record first
        job_id = create_rebuild_job_record(fund_name, start_date)
        
        # Get path to rebuild script
        script_path = Path(__file__).parent / "rebuild_from_date.py"
        if not script_path.exists():
            logger.error(f"Rebuild script not found: {script_path}")
            return None
        
        # Build command
        cmd = [
            sys.executable,
            str(script_path),
            fund_name,
            start_date.isoformat(),
            '--job-id', job_id
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
        job_id: Job execution ID
        
    Returns:
        Job data dict or None if not found
    """
    try:
        from web_dashboard.supabase_client import SupabaseClient
        
        client = SupabaseClient(use_service_role=True)
        result = client.supabase.table("job_executions").select("*").eq("id", job_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            return None
            
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        return None
