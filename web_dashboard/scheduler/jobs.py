"""
Scheduled Jobs Definitions
==========================

Define all background jobs here. Each job should:
1. Be a function that takes no arguments
2. Handle its own error logging
3. Call log_job_execution() to record results
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from scheduler.scheduler_core import log_job_execution

logger = logging.getLogger(__name__)


# Job definitions with metadata
AVAILABLE_JOBS: Dict[str, Dict[str, Any]] = {
    'exchange_rates': {
        'name': 'Refresh Exchange Rates',
        'description': 'Fetch latest USD/CAD exchange rate and store in database',
        'default_interval_minutes': 30,
        'enabled_by_default': True
    }
}


def refresh_exchange_rates_job() -> None:
    """Fetch and store the latest exchange rate.
    
    This ensures the dashboard always has up-to-date rates for currency conversion.
    """
    job_id = 'exchange_rates'
    start_time = time.time()
    
    try:
        logger.info("Starting exchange rates refresh job...")
        
        # Import here to avoid circular imports
        from exchange_rates_utils import reload_exchange_rate_for_date
        
        # Fetch today's rate
        today = datetime.now(timezone.utc)
        rate = reload_exchange_rate_for_date(today, 'USD', 'CAD')
        
        if rate is not None:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Updated USD/CAD rate: {rate}"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"✅ {message}")
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "Failed to fetch exchange rate from API"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.warning(f"⚠️ {message}")
            
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Exchange rates job failed: {e}")


def register_default_jobs(scheduler) -> None:
    """Register all default jobs with the scheduler.
    
    Called by start_scheduler() during initialization.
    """
    from apscheduler.triggers.interval import IntervalTrigger
    
    # Exchange rates job - every 30 minutes
    if AVAILABLE_JOBS['exchange_rates']['enabled_by_default']:
        scheduler.add_job(
            refresh_exchange_rates_job,
            trigger=IntervalTrigger(minutes=AVAILABLE_JOBS['exchange_rates']['default_interval_minutes']),
            id='exchange_rates',
            name='Refresh Exchange Rates',
            replace_existing=True
        )
        logger.info("Registered job: exchange_rates (every 30 min)")
    
    # Add more default jobs here as needed
    # Example:
    # scheduler.add_job(
    #     refresh_portfolio_prices_job,
    #     trigger=IntervalTrigger(minutes=60),
    #     id='portfolio_prices',
    #     name='Refresh Portfolio Prices',
    #     replace_existing=True
    # )
