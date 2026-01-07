#!/usr/bin/env python3
"""
Admin Dashboard - Main Page
==========================

Lightweight admin dashboard with Scheduled Tasks management.
Other admin functions are split into separate pages for better performance.
"""

import streamlit as st
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, has_admin_access, get_user_email
from navigation import render_navigation

# Import log_handler to register PERF logging level
try:
    import log_handler  # noqa: F401 - Import to register PERF level
except ImportError:
    pass

# Performance logging setup
import logging
logger = logging.getLogger(__name__)

# Initialize performance tracking in session state
if 'perf_log' not in st.session_state:
    st.session_state.perf_log = []

# Import shared utilities
from admin_utils import perf_timer

# Page configuration
st.set_page_config(page_title="Admin Dashboard", page_icon="🔧", layout="wide")

# Check authentication - redirect to main page if not logged in
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Refresh token if needed (auto-refresh before expiry)
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    # Token refresh failed - session is invalid, redirect to login
    from auth_utils import logout_user
    logout_user()
    st.error("Your session has expired. Please log in again.")
    st.switch_page("streamlit_app.py")
    st.stop()

# Check admin access (allows both admin and readonly_admin)
if not has_admin_access():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Header with cache clearing button
col_header1, col_header2, col_header3 = st.columns([2, 2, 1])
with col_header1:
    st.markdown("# 🔧 Admin Dashboard")
with col_header3:
    st.write("")  # Spacer for alignment
    if st.button("🔄 Clear Cache", help="Force refresh all cached data from database", use_container_width=True):
        clear_time = datetime.now().isoformat()
        
        try:
            logger.info(f"Cache clear initiated by {get_user_email()} at {clear_time}")
            
            # Clear ALL Streamlit data caches
            st.cache_data.clear()
            
            logger.info(f"Cache cleared successfully at {clear_time}")
            
            # Show toast notification that persists across rerun
            st.toast(
                f"✅ Cache cleared by {get_user_email()} at {datetime.now().strftime('%H:%M:%S')}",
                icon="✅"
            )
            
            # Log to file for audit trail
            try:
                from log_handler import log_message
                log_message("INFO", f"Cache cleared by {get_user_email()}")
            except:
                pass  # Logging is optional
            
            st.rerun()
            
        except Exception as e:
            error_msg = f"Failed to clear cache: {e}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")

st.caption(f"Logged in as: {get_user_email()}")

# Start overall page load timer
page_start_time = time.perf_counter()

# Display build timestamp (from Woodpecker CI environment variable)
build_timestamp = os.getenv("BUILD_TIMESTAMP")
if build_timestamp:
    # Convert UTC timestamp to user's preferred timezone
    try:
        from user_preferences import format_timestamp_in_user_timezone
        build_timestamp = format_timestamp_in_user_timezone(build_timestamp)
    except ImportError:
        # Fallback if user_preferences not available
        if "UTC" in build_timestamp:
            build_timestamp = build_timestamp.replace(" UTC", " PST")
    st.caption(f"🏷️ Build: {build_timestamp}")
else:
    # Development mode - show current time in user's timezone (or PST)
    try:
        from user_preferences import get_user_timezone
        from zoneinfo import ZoneInfo
        user_tz_str = get_user_timezone() or "America/Vancouver"
        user_tz = ZoneInfo(user_tz_str)
        now = datetime.now(user_tz)
        dev_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
        st.caption(f"🏷️ Build: Development ({dev_timestamp})")
    except (ImportError, Exception):
        st.caption(f"🏷️ Build: Development ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

# Custom page navigation in sidebar
render_navigation(show_ai_assistant=True, show_settings=True)

# Quick links to other admin pages
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔗 Admin Pages")
    st.page_link("pages/admin_scheduler.py", label="Jobs", icon="⏰")
    st.page_link("pages/admin_users.py", label="👥 User & Access Management", icon="👥")
    st.page_link("pages/admin_system.py", label="📊 System Monitoring", icon="📊")
    st.page_link("pages/admin_funds.py", label="🏦 Fund Management", icon="🏦")
    st.page_link("pages/admin_trade_entry.py", label="📈 Trade Entry", icon="📈")
    st.page_link("pages/admin_contributions.py", label="💰 Contributions", icon="💰")
    st.page_link("pages/admin_ai_settings.py", label="🤖 AI Settings", icon="🤖")

# Scheduler has moved to dedicated admin pages
# See admin pages sidebar for scheduler management
st.info("ℹ️ The scheduler has been moved to dedicated admin pages for better organization.")

# Calculate and log total page load time
page_load_time = (time.perf_counter() - page_start_time) * 1000
total_entry = {
    'operation': 'TOTAL PAGE LOAD',
    'time_ms': round(page_load_time, 2),
    'timestamp': datetime.now().isoformat()
}
st.session_state.perf_log.append(total_entry)
logger.perf(f"⏱️ TOTAL PAGE LOAD: {total_entry['time_ms']}ms")
