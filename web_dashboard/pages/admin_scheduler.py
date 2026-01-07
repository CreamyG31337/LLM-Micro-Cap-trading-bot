#!/usr/bin/env python3
"""
Scheduler Administration
=======================

Dedicated admin page for managing background scheduled jobs.
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
from admin_utils import perf_timer

# Page configuration
st.set_page_config(page_title="Scheduler Admin", page_icon="⏰", layout="wide")

# Check authentication - redirect to main page if not logged in
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Refresh token if needed
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    from auth_utils import logout_user
    logout_user()
    st.error("Your session has expired. Please log in again.")
    st.switch_page("streamlit_app.py")
    st.stop()

# Check admin access
if not has_admin_access():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Main Content
st.title("⏰ Scheduler Administration")
st.caption(f"Logged in as: {get_user_email()}")

# Add quick links to sidebar manually (since they seem to be manual in other pages)
with st.sidebar:
    st.markdown("---")
    st.markdown("### 🔗 Admin Pages")
    st.page_link("pages/admin.py", label="🔧 Admin Dashboard", icon="🔧")
    st.page_link("pages/admin_scheduler.py", label="⏰ Scheduler Admin", icon="⏰")
    st.page_link("pages/admin_users.py", label="👥 User & Access Management", icon="👥")
    st.page_link("pages/admin_system.py", label="📊 System Monitoring", icon="📊")
    st.page_link("pages/admin_funds.py", label="🏦 Fund Management", icon="🏦")
    st.page_link("pages/admin_trade_entry.py", label="📈 Trade Entry", icon="📈")
    st.page_link("pages/admin_contributions.py", label="💰 Contributions", icon="💰")
    st.page_link("pages/admin_ai_settings.py", label="🤖 AI Settings", icon="🤖")

with perf_timer("Scheduler UI"):
    try:
        from scheduler_ui import render_scheduler_admin
        render_scheduler_admin()
    except ImportError as e:
        st.warning(f"Scheduler UI not available: {e}")
        st.info("The scheduler module may not be running in this environment.")
    except Exception as e:
        st.error(f"Error loading scheduler: {e}")
