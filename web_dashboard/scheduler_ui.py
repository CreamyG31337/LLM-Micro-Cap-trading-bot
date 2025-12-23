"""
Scheduler Admin UI Component
============================

Streamlit UI for managing background scheduled tasks.
Add to your Streamlit app with:

    from scheduler_ui import render_scheduler_admin
    render_scheduler_admin()
"""

import streamlit as st
from datetime import datetime
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


def render_scheduler_admin():
    """Render the scheduler admin interface."""
    
    try:
        from scheduler import (
            get_scheduler, 
            get_all_jobs_status, 
            run_job_now, 
            pause_job, 
            resume_job,
            start_scheduler
        )
        from scheduler.scheduler_core import get_job_logs
        
        # Ensure scheduler is running
        scheduler = get_scheduler()
        if not scheduler.running:
            if st.button("🚀 Start Scheduler"):
                start_scheduler()
                st.success("Scheduler started!")
                st.rerun()
            st.warning("Scheduler is not running. Click above to start.")
            return
        
        # Get all jobs
        jobs = get_all_jobs_status()
        
        if not jobs:
            st.info("No scheduled jobs configured.")
            return
        
        # Display each job
        for job in jobs:
            with st.expander(f"**{job['name']}** - {'⏸️ Paused' if job['is_paused'] else '✅ Active'}", expanded=True):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    if job['next_run']:
                        next_run_str = format_datetime_local(job['next_run'])
                        st.write(f"📅 **Next run:** {next_run_str}")
                    else:
                        st.write("📅 **Next run:** Paused")
                    st.write(f"🔄 **Schedule:** {job['trigger']}")
                
                with col2:
                    # Action buttons
                    if st.button("▶️ Run Now", key=f"run_{job['id']}"):
                        with st.spinner("Running..."):
                            success = run_job_now(job['id'])
                            if success:
                                st.success("Job executed!")
                            else:
                                st.error("Job failed!")
                            st.rerun()
                    
                    if job['is_paused']:
                        if st.button("▶️ Resume", key=f"resume_{job['id']}"):
                            resume_job(job['id'])
                            st.rerun()
                    else:
                        if st.button("⏸️ Pause", key=f"pause_{job['id']}"):
                            pause_job(job['id'])
                            st.rerun()
                
                # Recent execution logs
                logs = get_job_logs(job['id'], limit=5)
                if logs:
                    st.write("**Recent executions:**")
                    for log in logs:
                        status_icon = "✅" if log['success'] else "❌"
                        time_str = format_datetime_local(log['timestamp'])
                        duration = f"({log['duration_ms']}ms)" if log['duration_ms'] else ""
                        st.text(f"{status_icon} {time_str} {duration} - {log['message'][:50]}")
                else:
                    st.text("No recent executions")
        
        # Refresh button
        st.divider()
        if st.button("🔄 Refresh Status"):
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
