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
    st.warning("Please log in to access settings.")
    st.stop()

st.title("⚙️ Settings")
st.markdown("Configure your dashboard preferences")

# Get current user email
user_email = get_user_email()
if user_email:
    st.caption(f"Logged in as: {user_email}")

st.divider()

# Timezone Settings
st.subheader("🌍 Timezone")

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
    # Default to system timezone
    try:
        current_tz = str(datetime.now().astimezone().tzinfo)
        # Try to map to a common timezone name
        if "PST" in current_tz or "PDT" in current_tz:
            current_tz = "America/Los_Angeles"
        elif "EST" in current_tz or "EDT" in current_tz:
            current_tz = "America/New_York"
        elif "CST" in current_tz or "CDT" in current_tz:
            current_tz = "America/Chicago"
        elif "MST" in current_tz or "MDT" in current_tz:
            current_tz = "America/Denver"
        else:
            current_tz = "UTC"
    except Exception:
        current_tz = "UTC"

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
        st.rerun()
    else:
        st.error("❌ Failed to save timezone. Please try again.")

st.divider()

# Currency Settings
st.subheader("💰 Currency")

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
        st.rerun()
    else:
        st.error("❌ Failed to save currency. Please try again.")

st.divider()

# Show all preferences (for debugging)
if st.checkbox("Show all preferences (debug)"):
    prefs = get_all_user_preferences()
    st.json(prefs)

