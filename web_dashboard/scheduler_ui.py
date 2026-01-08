"""
Scheduler Admin UI Component
============================

Streamlit UI for managing background scheduled tasks.
Add to your Streamlit app with:

    from scheduler_ui import render_scheduler_admin
    render_scheduler_admin()
"""

import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional


def get_display_timezone():
    """Get the timezone to use for display.
    
    First checks user preference, then falls back to system timezone.
    """
    try:
        from user_preferences import get_user_timezone
        user_tz = get_user_timezone()
        if user_tz:
            # Try to use user's preferred timezone
            try:
                import pytz
                return pytz.timezone(user_tz)
            except Exception:
                # Fallback if pytz can't parse it
                pass
    except ImportError:
        # user_preferences module not available
        pass
    except Exception:
        # Error getting preference, fallback to system timezone
        pass
    
    # Fallback to system timezone
    return datetime.now().astimezone().tzinfo


def format_datetime_local(dt: Optional[datetime]) -> str:
    """Format a datetime in user's preferred timezone (or local) for display.
    
    Args:
        dt: Datetime to format (can be in any timezone)
        
    Returns:
        Formatted string in user's preferred timezone
    """
    if dt is None:
        return "N/A"
    
    # Ensure datetime is timezone-aware
    if dt.tzinfo is None:
        # If no timezone info, assume UTC
        from datetime import timezone
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Convert to display timezone (user preference or system default)
    display_tz = get_display_timezone()
    local_dt = dt.astimezone(display_tz)
    
    # Format with timezone abbreviation
    return local_dt.strftime('%Y-%m-%d %H:%M:%S %Z')


def format_duration(duration_ms: Optional[int]) -> str:
    """Format duration in milliseconds to a human-readable string.
    
    Args:
        duration_ms: Duration in milliseconds (can be None or negative)
        
    Returns:
        Formatted string like "1.2s" or "500ms", or empty string if invalid
    """
    if duration_ms is None or duration_ms < 0:
        return ""
    
    if duration_ms < 1000:
        return f"{duration_ms}ms"
    else:
        seconds = duration_ms / 1000.0
        if seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"


@st.cache_data(ttl=5)  # Cache for 5 seconds to reduce database load
def _get_cached_jobs_status():
    """Get all jobs status with caching."""
    from scheduler import get_all_jobs_status
    return get_all_jobs_status()


def render_scheduler_admin():
    """Render the scheduler admin interface."""
    
    try:
        from scheduler import (
            get_scheduler, 
            get_all_jobs_status, 
            run_job_now, 
            pause_job, 
            resume_job,
            start_scheduler,
            is_scheduler_running
        )
        
        from scheduler.jobs import AVAILABLE_JOBS
        
        # Check scheduler status using cross-process safe method (heartbeat file)
        # This avoids creating a new scheduler instance in each Streamlit worker
        if not is_scheduler_running():
            st.error("❌ **Scheduler is not running**")
            st.info("The scheduler may have crashed. Check the logs for errors.")
            if st.button("🚀 Start Scheduler"):
                try:
                    result = start_scheduler()
                    if result:
                        st.success("✅ Scheduler started!")
                    else:
                        st.warning("⚠️ Scheduler was already running (or failed to start)")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Failed to start scheduler: {e}")
                    st.exception(e)
            return
        
        # Get all jobs (using cached version for performance)
        jobs = _get_cached_jobs_status()
        
        if not jobs:
            st.info("No scheduled jobs configured.")
            return
        
        # Consolidate jobs by base ID (e.g., update_portfolio_prices and update_portfolio_prices_close -> update_portfolio_prices)
        # This avoids showing multiple entries for the same logical job
        # IMPORTANT: We preserve the actual job ID for execution while consolidating for display
        consolidated_jobs = {}
        for job in jobs:
            job_id = job['id']
            # Get base job ID by removing common suffixes
            base_id = job_id
            
            # Remove time-based suffixes (e.g., _close, _open, _premarket, etc.)
            for suffix in ['_close', '_open', '_premarket', '_midmorning', '_powerhour', '_postmarket', '_refresh', '_populate', '_collect', '_scan', '_fetch', '_cleanup', '_scrape']:
                if job_id.endswith(suffix):
                    base_id = job_id[:-len(suffix)]
                    break
            
            # Keep only one entry per base job (prefer the main one without suffix, or the first one seen)
            if base_id not in consolidated_jobs:
                # Store the job but remember to use the ACTUAL job ID for execution and widget keys
                job['actual_job_id'] = job_id  # Preserve the real ID for stable keys
                consolidated_jobs[base_id] = job
            elif job_id == base_id:
                # This is the main job (no suffix), prefer it
                job['actual_job_id'] = job_id  # Preserve the real ID
                consolidated_jobs[base_id] = job
            elif len(job_id) < len(consolidated_jobs[base_id]['id']):
                # Prefer shorter job IDs (likely the "main" one)
                job['actual_job_id'] = job_id
                consolidated_jobs[base_id] = job
        
        jobs = list(consolidated_jobs.values())
        
        # Sort jobs alphabetically by name (strip emoji for proper sorting)
        def get_sort_key(job_name: str) -> str:
            """Extract sortable name by removing emoji and leading whitespace."""
            name = job_name.strip()
            # Remove first character if it's not alphanumeric (likely an emoji)
            if name and not name[0].isalnum():
                # Check if first char is emoji (not ASCII)
                if ord(name[0]) > 127:
                    name = name[1:].lstrip()
            return name.lower()
        
        jobs = sorted(jobs, key=lambda x: get_sort_key(x.get('name', '')))
        
        # Display each job
        for job in jobs:
            # Determine status badge
            if job.get('is_running'):
                status_badge = "🔵 RUNNING"
                status_color = "blue"
            elif job.get('last_error'):
                status_badge = "🔴 FAILED"
                status_color = "red"
            elif job['is_paused']:
                status_badge = "⏸️ PAUSED"
                status_color = "gray"
            else:
                status_badge = "✅ IDLE"
                status_color = "green"
            
            with st.expander(f"{job['name']} - {status_badge}", expanded=True):
                # Show running status prominently
                if job.get('is_running'):
                    running_since = job.get('running_since')
                    if running_since:
                        since_str = format_datetime_local(running_since)
                        duration = datetime.now(running_since.tzinfo or datetime.now().astimezone().tzinfo) - running_since
                        duration_str = f"{int(duration.total_seconds() // 60)}m {int(duration.total_seconds() % 60)}s"
                        st.info(f"⏳ **Job is currently running** (Started: {since_str}, Duration: {duration_str})")
                    else:
                        st.info("⏳ **Job is currently running**")
                
                # Show last error prominently
                if job.get('last_error'):
                    st.error(f"❌ **Last Error:** {job['last_error']}")
                
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if job['next_run']:
                        next_run_str = format_datetime_local(job['next_run'])
                        st.write(f"📅 **Next run:** {next_run_str}")
                    else:
                        st.write("📅 **Next run:** Paused")
                    st.write(f"🔄 **Schedule:** {job['trigger']}")
                
                with col2:
                    # Always show parameters editor for manual runs
                    job_params = {}
                    # CRITICAL: Use actual_job_id for stable widget keys, not the consolidated ID
                    widget_key_base = job.get('actual_job_id', job['id'])
                    job_id_base = widget_key_base
                    
                    # Get parameter definitions (check both job_id and base job_id for variants)
                    params = {}
                    if job_id_base in AVAILABLE_JOBS and 'parameters' in AVAILABLE_JOBS[job_id_base]:
                        params = AVAILABLE_JOBS[job_id_base]['parameters']
                    
                    # Show parameters editor in expander
                    with st.expander("⚙️ Edit Parameters", expanded=False):
                        if params:
                            # Special handling for jobs with date range support
                            if 'use_date_range' in params:
                                # Show use_date_range checkbox first
                                use_range_key = f"param_{widget_key_base}_use_date_range"
                                use_date_range = st.checkbox(
                                    "Use Date Range",
                                    value=params['use_date_range'].get('default', False),
                                    help=params['use_date_range'].get('description', ''),
                                    key=use_range_key
                                )
                                
                                if use_date_range:
                                    # Show date range pickers
                                    from_date_key = f"param_{widget_key_base}_from_date"
                                    to_date_key = f"param_{widget_key_base}_to_date"
                                    
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        from_date = st.date_input(
                                            "From Date",
                                            value=datetime.now().date() - timedelta(days=7),
                                            help=params['from_date'].get('description', ''),
                                            key=from_date_key
                                        )
                                    with col2:
                                        to_date = st.date_input(
                                            "To Date",
                                            value=datetime.now().date(),
                                            help=params['to_date'].get('description', ''),
                                            key=to_date_key
                                        )
                                    
                                    if from_date and to_date:
                                        days_in_range = (to_date - from_date).days + 1
                                        if days_in_range > 30:
                                            st.warning(f"⚠️ Large date range: {days_in_range} days. This may take a while to process.")
                                        elif days_in_range > 0:
                                            st.info(f"Will process {days_in_range} day(s)")
                                    
                                    if use_date_range:
                                        job_params['use_date_range'] = True
                                        if from_date:
                                            job_params['from_date'] = from_date
                                        if to_date:
                                            job_params['to_date'] = to_date
                                else:
                                    # Show single date picker
                                    target_date_key = f"param_{widget_key_base}_target_date"
                                    target_date = st.date_input(
                                        "Target Date",
                                        value=datetime.now().date() - timedelta(days=1),
                                        help=params['target_date'].get('description', ''),
                                        key=target_date_key
                                    )
                                    if target_date:
                                        job_params['target_date'] = target_date
                            else:
                                # Standard parameter handling for other jobs
                                for param_name, param_info in params.items():
                                    label = param_name.replace('_', ' ').title()
                                    help_text = param_info.get('description', '')
                                    default_val = param_info.get('default')
                                    param_type = param_info.get('type', 'text')
                                    optional = param_info.get('optional', False)
                                    
                                    key = f"param_{widget_key_base}_{param_name}"
                                    
                                    if param_type == 'date':
                                        # Date picker for date parameters
                                        if default_val is None:
                                            default_date = datetime.now().date()
                                        elif isinstance(default_val, str):
                                            from datetime import datetime as dt
                                            try:
                                                default_date = dt.fromisoformat(default_val).date()
                                            except (ValueError, AttributeError):
                                                default_date = datetime.now().date()
                                        elif isinstance(default_val, date):
                                            default_date = default_val
                                        else:
                                            default_date = datetime.now().date()
                                        
                                        selected_date = st.date_input(
                                            label, 
                                            value=default_date, 
                                            help=help_text, 
                                            key=key
                                        )
                                        # For optional date params with None default, only include if user changed from today
                                        if optional and default_val is None:
                                            if selected_date != datetime.now().date():
                                                job_params[param_name] = selected_date
                                        else:
                                            job_params[param_name] = selected_date
                                    elif param_type == 'number':
                                        # Number input
                                        if isinstance(default_val, int):
                                            input_val = st.number_input(
                                                label, 
                                                value=default_val, 
                                                step=1, 
                                                help=help_text, 
                                                key=key
                                            )
                                        else:
                                            input_val = st.number_input(
                                                label, 
                                                value=default_val if default_val is not None else 0.0, 
                                                help=help_text, 
                                                key=key
                                            )
                                        # For optional params, only include if different from default
                                        if optional and default_val is not None:
                                            if input_val != default_val:
                                                job_params[param_name] = input_val
                                        else:
                                            job_params[param_name] = input_val
                                    elif param_type == 'boolean':
                                        # Checkbox for boolean parameters
                                        input_val = st.checkbox(
                                            label, 
                                            value=default_val if default_val is not None else False, 
                                            help=help_text, 
                                            key=key
                                        )
                                        # For optional boolean params, only include if different from default
                                        if optional and default_val is not None:
                                            if input_val != default_val:
                                                job_params[param_name] = input_val
                                        else:
                                            job_params[param_name] = input_val
                                    else:
                                        # Text input for string parameters
                                        input_val = st.text_input(
                                            label, 
                                            value=str(default_val) if default_val is not None else '', 
                                            help=help_text, 
                                            key=key
                                        )
                                        # For optional text params, only include if different from default
                                        if optional and default_val is not None:
                                            if input_val != str(default_val):
                                                job_params[param_name] = input_val
                                        else:
                                            job_params[param_name] = input_val
                        else:
                            st.info("This job has no configurable parameters.")

                    # Action buttons
                    # Disable run button if already running
                    run_disabled = job.get('is_running', False)
                    if st.button("▶️ Run Now", key=f"run_{widget_key_base}", disabled=run_disabled):
                        with st.spinner("Running..."):
                            # Handle date range parameters for jobs that support it
                            final_params = job_params.copy()
                            if 'use_date_range' in final_params:
                                use_range = final_params.get('use_date_range', False)
                                if not use_range:
                                    # Single date mode - remove range params and the flag
                                    final_params.pop('use_date_range', None)
                                    final_params.pop('from_date', None)
                                    final_params.pop('to_date', None)
                                else:
                                    # Date range mode - keep use_date_range=True and remove single date param
                                    final_params.pop('target_date', None)
                            
                            # IMPORTANT: Use actual_job_id for execution, not the consolidated base ID
                            actual_id = job.get('actual_job_id', job['id'])
                            success = run_job_now(actual_id, **final_params)
                            if success:
                                st.success("✅ Job started! Refresh the page to see updated status.")
                            else:
                                st.error("❌ Failed to start job. Check logs for details.")
                    
                    if run_disabled:
                        st.caption("⚠️ Job is currently running")
                    
                    # Use actual_job_id for pause/resume operations too
                    actual_id = job.get('actual_job_id', job['id'])
                    if job['is_paused']:
                        if st.button("▶️ Resume", key=f"resume_{widget_key_base}"):
                            resume_job(actual_id)
                            st.rerun()
                    else:
                        if st.button("⏸️ Pause", key=f"pause_{widget_key_base}"):
                            pause_job(actual_id)
                            st.rerun()
                
                # Recent execution logs (already included in job status from batched query)
                logs = job.get('recent_logs', [])
                if logs:
                    st.write("**Recent executions:**")
                    for log in logs:
                        status_icon = "✅" if log['success'] else "❌"
                        time_str = format_datetime_local(log['timestamp'])
                        duration_str = format_duration(log.get('duration_ms'))
                        duration = f"({duration_str})" if duration_str else ""
                        st.text(f"{status_icon} {time_str} {duration} - {log['message']}")
                else:
                    st.text("No recent executions")
        
        # Refresh button
        st.divider()
        if st.button("🔄 Refresh Status"):
            # Clear cache on refresh
            _get_cached_jobs_status.clear()
            st.rerun()
            
    except ImportError as e:
        st.error(f"Scheduler module not available: {e}")
        st.info("The scheduler module may not be installed. Check that APScheduler is in requirements.txt.")
    except Exception as e:
        st.error(f"Error loading scheduler: {e}")


def render_scheduler_status_badge() -> str:
    """Return a status badge string for the scheduler.
    
    Use in sidebar: st.sidebar.write(render_scheduler_status_badge())
    """
    try:
        from scheduler import get_scheduler
        scheduler = get_scheduler()
        
        if scheduler.running:
            job_count = len(scheduler.get_jobs())
            return f"⏰ Scheduler: **Active** ({job_count} jobs)"
        else:
            return "⏰ Scheduler: **Stopped**"
    except:
        return "⏰ Scheduler: **Not Available**"
