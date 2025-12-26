#!/usr/bin/env python3
"""
User Settings Page
==================

Allows users to configure their preferences like timezone.
"""

import streamlit as st
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

# Check authentication
try:
    from auth_utils import is_authenticated, get_user_email
    from user_preferences import (
        get_user_timezone, 
        set_user_timezone,
        get_user_currency,
        set_user_currency,
        get_all_user_preferences
    )
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

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

# Sidebar navigation
from navigation import render_navigation
render_navigation(show_ai_assistant=True, show_settings=False)  # Don't show Settings link on this page

st.title("👤 User Preferences")
st.markdown("Configure your dashboard preferences")

# Get current user email
user_email = get_user_email()
if user_email:
    st.caption(f"Logged in as: {user_email}")

st.divider()

# Timezone Settings
st.subheader("🌍 Timezone")

@st.fragment
def render_timezone_settings():
    """Timezone selection fragment - prevents full page reload on save"""
    # Common timezones
    COMMON_TIMEZONES = {
        "America/Los_Angeles": "Pacific Time (US & Canada)",
        "America/Denver": "Mountain Time (US & Canada)",
        "America/Chicago": "Central Time (US & Canada)",
        "America/New_York": "Eastern Time (US & Canada)",
        "America/Toronto": "Eastern Time (Canada)",
        "America/Vancouver": "Pacific Time (Canada)",
        "UTC": "UTC (Coordinated Universal Time)",
        "Europe/London": "London (GMT/BST)",
        "Europe/Paris": "Paris (CET/CEST)",
        "Asia/Tokyo": "Tokyo (JST)",
        "Australia/Sydney": "Sydney (AEDT/AEST)",
    }

    # Get current timezone
    current_tz = get_user_timezone()
    if not current_tz:
        # Default to PST (Pacific Time) when no preference is set
        try:
            # Try to detect system timezone first
            system_tz = str(datetime.now().astimezone().tzinfo)
            # Try to map to a common timezone name
            if "PST" in system_tz or "PDT" in system_tz:
                current_tz = "America/Los_Angeles"
            elif "EST" in system_tz or "EDT" in system_tz:
                current_tz = "America/New_York"
            elif "CST" in system_tz or "CDT" in system_tz:
                current_tz = "America/Chicago"
            elif "MST" in system_tz or "MDT" in system_tz:
                current_tz = "America/Denver"
            else:
                # Default to PST if system timezone can't be determined
                current_tz = "America/Los_Angeles"
        except Exception:
            # Default to PST if detection fails
            current_tz = "America/Los_Angeles"

    # Find current index
    tz_options = list(COMMON_TIMEZONES.keys())
    tz_labels = [f"{tz} - {COMMON_TIMEZONES[tz]}" for tz in tz_options]

    try:
        current_index = tz_options.index(current_tz) if current_tz in tz_options else 0
    except ValueError:
        current_index = 0

    # Timezone selector
    selected_tz_label = st.selectbox(
        "Select your timezone:",
        options=tz_labels,
        index=current_index,
        help="This timezone will be used to display all times in the dashboard."
    )

    selected_tz = tz_options[tz_labels.index(selected_tz_label)]

    # Show current time in selected timezone
    if selected_tz:
        try:
            import pytz
            tz_obj = pytz.timezone(selected_tz)
            now = datetime.now(tz_obj)
            st.caption(f"Current time in {selected_tz}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        except Exception as e:
            st.caption(f"Could not display time: {e}")

    # Save button
    if st.button("💾 Save Timezone", type="primary"):
        if set_user_timezone(selected_tz):
            st.success(f"✅ Timezone saved as {selected_tz}")
        else:
            st.error("❌ Failed to save timezone. Please try again.")

render_timezone_settings()

st.divider()

# Currency Settings
st.subheader("💰 Currency")

@st.fragment
def render_currency_settings():
    """Currency selection fragment - prevents full page reload on save"""
    # Get current currency
    current_currency = get_user_currency()
    if not current_currency:
        current_currency = 'CAD'  # Default

    # Build currency options from registry
    try:
        from streamlit_utils import SUPPORTED_CURRENCIES
        currency_options = list(SUPPORTED_CURRENCIES.keys())
        currency_labels = [f"{code} - {SUPPORTED_CURRENCIES[code]}" for code in currency_options]
    except ImportError:
        # Fallback if import fails
        currency_options = ['CAD', 'USD']
        currency_labels = ['CAD - Canadian Dollar', 'USD - US Dollar']

    # Find current index
    try:
        current_index = currency_options.index(current_currency) if current_currency in currency_options else 0
    except ValueError:
        current_index = 0

    # Currency selector (same pattern as timezone)
    selected_currency_label = st.selectbox(
        "Select your display currency:",
        options=currency_labels,
        index=current_index,
        help="All values will be converted and displayed in this currency."
    )

    selected_currency = currency_options[currency_labels.index(selected_currency_label)]

    # Save button (same pattern as timezone)
    if st.button("💾 Save Currency", type="primary", key="save_currency"):
        if set_user_currency(selected_currency):
            st.success(f"✅ Currency saved as {selected_currency}")
        else:
            st.error("❌ Failed to save currency. Please try again.")

render_currency_settings()

st.divider()

# Show all preferences (for debugging)
if st.checkbox("Show all preferences (debug)"):
    prefs = get_all_user_preferences()
    st.json(prefs)

