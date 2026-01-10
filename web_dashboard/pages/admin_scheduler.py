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

from auth_utils import is_authenticated, has_admin_access, get_user_email, redirect_to_login
from navigation import render_navigation
from admin_utils import perf_timer

# Page configuration
st.set_page_config(page_title="Jobs", page_icon="🔨", layout="wide")

# Check authentication - redirect to main page if not logged in
if not is_authenticated():
    redirect_to_login("pages/admin_scheduler.py")

# Refresh token if needed
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    from auth_utils import logout_user
    logout_user(return_to="pages/admin_scheduler.py")
    st.stop()

# Check admin access
if not has_admin_access():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Main Content
st.title("🔨 Jobs")
st.caption(f"Logged in as: {get_user_email()}")

with perf_timer("Scheduler UI"):
    try:
        from scheduler_ui import render_scheduler_admin
        render_scheduler_admin()
    except ImportError as e:
        st.warning(f"Scheduler UI not available: {e}")
        st.info("The scheduler module may not be running in this environment.")
    except Exception as e:
        st.error(f"Error loading scheduler: {e}")
