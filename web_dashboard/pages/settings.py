#!/usr/bin/env python3
"""
User Settings Page
==================

Allows users to configure their preferences like timezone.

NOTE: This page has been migrated to Flask. This file redirects to the Flask version.
"""

import streamlit as st
from datetime import datetime
import os

# Page config
st.set_page_config(
    page_title="Settings",
    page_icon="⚙️",
    layout="wide"
)

# CRITICAL: Restore session from cookies before checking preferences
try:
    from auth_utils import ensure_session_restored
    ensure_session_restored()
except Exception:
    pass

# Redirect to Flask version if available AND enabled
try:
    from shared_navigation import is_page_migrated, get_page_url
    from user_preferences import get_user_preference
    
    # Only redirect if V2 is enabled AND page is migrated
    is_v2_enabled = get_user_preference('v2_enabled', default=False)
    
    if is_v2_enabled and is_page_migrated('settings'):
        url = get_page_url('settings')
        st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
        st.write("Redirecting to new settings page...")
        st.stop()
except ImportError:
    pass  # Continue with Streamlit version if shared_navigation not available

# Check authentication
try:
    from auth_utils import is_authenticated, get_user_email, redirect_to_login
    from user_preferences import (
        get_user_timezone, 
        set_user_timezone,
        get_user_currency,
        set_user_currency,
        get_user_theme,
        set_user_theme,
        THEME_OPTIONS,
        get_all_user_preferences
    )
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

if not is_authenticated():
    redirect_to_login("pages/settings.py")

# Refresh token if needed (auto-refresh before expiry)
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    # Token refresh failed - session is invalid, redirect to login
    from auth_utils import logout_user
    logout_user(return_to="pages/settings.py")
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
    tz_options = list(COMMON_TIMEZONES.keys())
    
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

    # Find current index (tz_options already created above for debug)
    tz_labels = [f"{tz} - {COMMON_TIMEZONES[tz]}" for tz in tz_options]

    # Normalize current_tz for comparison (ensure it's a string, strip whitespace)
    if current_tz:
        current_tz_normalized = str(current_tz).strip()
    else:
        current_tz_normalized = None

    try:
        if current_tz_normalized and current_tz_normalized in tz_options:
            current_index = tz_options.index(current_tz_normalized)
        else:
            current_index = 0
    except ValueError:
        current_index = 0

    # Auto-save function - defined before use
    def _save_timezone_on_change():
        if "timezone_selectbox" in st.session_state:
            selected_label = st.session_state.timezone_selectbox
            selected_tz = tz_options[tz_labels.index(selected_label)]
            try:
                cache = st.session_state
                if "_pref_error_timezone" in cache:
                    del cache["_pref_error_timezone"]
                
                # Clear cache to force fresh read
                from user_preferences import clear_preference_cache
                clear_preference_cache()
                
                result = set_user_timezone(selected_tz)
                if result:
                    st.success(f"✅ Timezone saved as {selected_tz}")
                    # Clear cache again after save to ensure fresh read
                    clear_preference_cache()
                else:
                    error_msg = cache.get("_pref_error_timezone", "Unknown error - RPC call returned False")
                    st.error(f"❌ Failed to save timezone: {error_msg}")
                    st.caption("Check the application console/logs for more details.")
            except Exception as e:
                st.error(f"❌ Exception saving timezone: {type(e).__name__}: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # Timezone selector - auto-saves on change
    selected_tz_label = st.selectbox(
        "Select your timezone:",
        options=tz_labels,
        index=current_index,
        help="This timezone will be used to display all times in the dashboard. Changes are saved automatically.",
        key="timezone_selectbox",
        on_change=_save_timezone_on_change
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

    # Normalize current_currency for comparison (options are already uppercase)
    if current_currency:
        current_currency_normalized = str(current_currency).strip().upper()
    else:
        current_currency_normalized = None

    # Find current index
    try:
        if current_currency_normalized:
            # Try exact match first (case-sensitive)
            if current_currency_normalized in currency_options:
                current_index = currency_options.index(current_currency_normalized)
            # Try case-insensitive match
            elif current_currency_normalized in [opt.upper() for opt in currency_options]:
                currency_options_normalized = [opt.upper() for opt in currency_options]
                current_index = currency_options_normalized.index(current_currency_normalized)
            else:
                current_index = 0
        else:
            current_index = 0
    except ValueError:
        current_index = 0

    # Auto-save function - defined before use
    def _save_currency_on_change():
        if "currency_selectbox" in st.session_state:
            selected_label = st.session_state.currency_selectbox
            selected_currency = currency_options[currency_labels.index(selected_label)]
            try:
                cache = st.session_state
                if "_pref_error_currency" in cache:
                    del cache["_pref_error_currency"]
                
                # Clear cache to force fresh read
                from user_preferences import clear_preference_cache
                clear_preference_cache()
                
                result = set_user_currency(selected_currency)
                if result:
                    st.success(f"✅ Currency saved as {selected_currency}")
                    # Clear cache again after save to ensure fresh read
                    clear_preference_cache()
                else:
                    error_msg = cache.get("_pref_error_currency", "Unknown error - RPC call returned False")
                    st.error(f"❌ Failed to save currency: {error_msg}")
                    st.caption("Check the application console/logs for more details.")
            except Exception as e:
                st.error(f"❌ Exception saving currency: {type(e).__name__}: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # Currency selector - auto-saves on change
    selected_currency_label = st.selectbox(
        "Select your display currency:",
        options=currency_labels,
        index=current_index,
        help="All values will be converted and displayed in this currency. Changes are saved automatically.",
        key="currency_selectbox",
        on_change=_save_currency_on_change
    )

    selected_currency = currency_options[currency_labels.index(selected_currency_label)]

render_currency_settings()

st.divider()

# Theme Settings
st.subheader("🎨 Theme")

@st.fragment
def render_theme_settings():
    """Theme selection fragment - prevents full page reload on save"""
    # Get current theme
    current_theme = get_user_theme()
    
    # Build theme options
    theme_options = list(THEME_OPTIONS.keys())
    theme_labels = [f"{THEME_OPTIONS[key]}" for key in theme_options]
    
    # Normalize current_theme for comparison
    if current_theme:
        current_theme_normalized = str(current_theme).strip().lower()
    else:
        current_theme_normalized = None

    # Find current index
    try:
        # Compare normalized theme to normalized options
        theme_options_normalized = [opt.lower() for opt in theme_options]
        if current_theme_normalized and current_theme_normalized in theme_options_normalized:
            current_index = theme_options_normalized.index(current_theme_normalized)
        else:
            current_index = 0
    except ValueError:
        current_index = 0
    
    # Auto-save function - defined before use
    def _save_theme_on_change():
        if "theme_selectbox" in st.session_state:
            selected_label = st.session_state.theme_selectbox
            selected = theme_options[theme_labels.index(selected_label)]
            try:
                result = set_user_theme(selected)
                if result:
                    st.success(f"✅ Theme saved as {THEME_OPTIONS[selected]}")
                    # No rerun needed - fragment will update automatically
                    # Note: Theme change may require page refresh to fully apply
                    st.info("🔄 You may need to refresh the page to see theme changes")
            except Exception as e:
                st.error(f"Failed to save theme: {e}")
    
    # Theme selector - auto-saves on change
    selected_theme_label = st.selectbox(
        "Select your theme:",
        options=theme_labels,
        index=current_index,
        help="Override your browser/system theme preference. 'System Default' follows your OS setting. Changes are saved automatically.",
        key="theme_selectbox",
        on_change=_save_theme_on_change
    )
    
    selected_theme = theme_options[theme_labels.index(selected_theme_label)]
    
    # Show current setting info
    if selected_theme == 'system':
        st.caption("ℹ️ Theme will follow your browser/OS dark mode setting")
    elif selected_theme == 'dark':
        st.caption("🌙 Dark mode")
    else:
        st.caption("☀️ Light mode")

render_theme_settings()

st.divider()

# V2 Beta Features Toggle
st.subheader("🚀 Beta Features")

# @st.fragment
def render_v2_settings():
    """V2 beta features toggle fragment - prevents full page reload on save"""
    from user_preferences import get_user_preference, set_user_preference
    
    # Get current v2 enabled state
    current_v2_enabled = get_user_preference('v2_enabled', default=False)
    
    st.markdown("**Use Cloud Pages (Flask)**")
    st.caption("Enable new, faster page implementations for Settings, Logs, and Ticker Details.")
    
    # Auto-save function - defined before use
    def _save_v2_on_change():
        if "v2_toggle" in st.session_state:
            v2_enabled = st.session_state.v2_toggle
            try:
                cache = st.session_state
                if "_pref_error_v2_enabled" in cache:
                    del cache["_pref_error_v2_enabled"]
                
                result = set_user_preference('v2_enabled', v2_enabled)
                if result:
                    st.success(f"✅ Beta features {'enabled' if v2_enabled else 'disabled'}")
                    st.info("🔄 Refresh the page or navigate to see the changes take effect")
                    # No rerun needed - fragment will update automatically
                else:
                    error_msg = cache.get("_pref_error_v2_enabled", "Unknown error - RPC call returned False")
                    st.error(f"❌ Failed to save preference: {error_msg}")
            except Exception as e:
                st.error(f"❌ Exception saving preference: {type(e).__name__}: {str(e)}")

    # V2 toggle - auto-saves on change
    v2_enabled = st.toggle(
        "Enable v2 Beta Pages",
        value=current_v2_enabled,
        help="When enabled, migrated pages (Settings, Logs, Ticker Details) will use the new Flask-based implementation with better performance. Changes are saved automatically.",
        key="v2_toggle",
        on_change=_save_v2_on_change
    )

render_v2_settings()

st.divider()

# Show all preferences (for debugging)
if st.checkbox("Show all preferences (debug)"):
    try:
        from user_preferences import _get_user_id, _is_authenticated
        from auth_utils import get_user_id, is_authenticated
        
        st.write("**Debug Info:**")
        st.write(f"- Authenticated (user_preferences): {_is_authenticated()}")
        st.write(f"- Authenticated (auth_utils): {is_authenticated()}")
        st.write(f"- User ID (user_preferences): {_get_user_id()}")
        st.write(f"- User ID (auth_utils): {get_user_id() if is_authenticated() else 'N/A'}")
        
        prefs = get_all_user_preferences()
        st.write("**All Preferences:**")
        if prefs:
            st.json(prefs)
        else:
            st.warning("⚠️ No preferences found (empty dict returned)")
            st.caption("This could mean:")
            st.caption("1. User is not authenticated properly")
            st.caption("2. RPC function is failing")
            st.caption("3. User has no preferences saved yet")
            
            # Try to get individual preferences
            st.write("**Individual Preference Tests:**")
            from user_preferences import get_user_preference
            st.write(f"- timezone: {get_user_preference('timezone', 'NOT FOUND')}")
            st.write(f"- currency: {get_user_preference('currency', 'NOT FOUND')}")
            st.write(f"- theme: {get_user_preference('theme', 'NOT FOUND')}")
            st.write(f"- v2_enabled: {get_user_preference('v2_enabled', 'NOT FOUND')}")
    except Exception as e:
        st.error(f"Error in debug section: {e}")
        import traceback
        st.code(traceback.format_exc())

