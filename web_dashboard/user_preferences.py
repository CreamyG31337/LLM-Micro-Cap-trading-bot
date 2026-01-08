#!/usr/bin/env python3
"""
User Preferences Utilities
===========================

Functions for getting and setting user preferences in the database.
Uses session state as a cache for performance.
"""

from typing import Optional, Any, Dict
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import streamlit, but don't fail if not available (Flask context)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except (ImportError, RuntimeError):
    STREAMLIT_AVAILABLE = False
    st = None


def _get_cache():
    """Get appropriate cache (Flask session or Streamlit session state)"""
    try:
        from flask import session
        # Check if we're in a Flask request context
        from flask import has_request_context
        if has_request_context():
            return session
    except (ImportError, RuntimeError):
        pass
    
    # Fall back to Streamlit if available
    if STREAMLIT_AVAILABLE and st is not None:
        return st.session_state
    
    # No cache available (shouldn't happen in normal usage)
    return {}


def _get_user_id():
    """Get user ID from either Flask or Streamlit context"""
    # Try Flask first
    try:
        from flask_auth_utils import get_user_id_flask
        from flask import has_request_context
        if has_request_context():
            user_id = get_user_id_flask()
            if user_id:
                return user_id
    except (ImportError, RuntimeError):
        pass
    
    # Fall back to Streamlit
    if STREAMLIT_AVAILABLE and st is not None:
        try:
            from auth_utils import get_user_id, is_authenticated
            if is_authenticated():
                return get_user_id()
        except ImportError:
            pass
    
    return None


def _is_authenticated():
    """Check authentication in either Flask or Streamlit context"""
    # Try Flask first
    try:
        from flask_auth_utils import is_authenticated_flask
        from flask import has_request_context
        if has_request_context():
            return is_authenticated_flask()
    except (ImportError, RuntimeError):
        pass
    
    # Fall back to Streamlit
    if STREAMLIT_AVAILABLE and st is not None:
        try:
            from auth_utils import is_authenticated
            return is_authenticated()
        except ImportError:
            pass
    
    return False


def get_user_preference(key: str, default: Any = None) -> Any:
    """Get a user preference value.
    
    Checks session cache first, then falls back to database.
    Works in both Flask and Streamlit contexts.
    
    Args:
        key: Preference key (e.g., 'timezone')
        default: Default value if preference not found
        
    Returns:
        Preference value or default
    """
    # Check cache first (but skip cache for v2_enabled to ensure fresh reads)
    cache = _get_cache()
    cache_key = f"_pref_{key}"
    # v2_enabled controls navigation and must always be read fresh from database
    if key != 'v2_enabled' and cache_key in cache:
        return cache[cache_key]
    
    # Try to get from database
    try:
        if not _is_authenticated():
            return default
        
        user_id = _get_user_id()
        if not user_id:
            return default
        
        # Get Supabase client (works in both contexts)
        client = None
        try:
            from streamlit_utils import get_supabase_client
            # Try to get token from Streamlit context
            try:
                from auth_utils import get_user_token
                user_token = get_user_token()
                client = get_supabase_client(user_token=user_token)
            except ImportError:
                client = get_supabase_client()
        except ImportError:
            # Flask context - need to get token from Flask request
            try:
                from supabase_client import SupabaseClient
                from flask_auth_utils import get_auth_token
                from flask import has_request_context
                
                if has_request_context():
                    # Get token from Flask cookies
                    user_token = get_auth_token()
                    client = SupabaseClient(user_token=user_token) if user_token else SupabaseClient()
                else:
                    client = SupabaseClient()
            except ImportError:
                return default
        
        if not client:
            return default
        
        # Call the RPC function to get preference
        result = client.supabase.rpc('get_user_preference', {'pref_key': key}).execute()
        
        if result.data is not None:
            # Handle both scalar and list responses
            if isinstance(result.data, list) and len(result.data) > 0:
                value = result.data[0]
            else:
                value = result.data
            
            # Parse JSONB string if needed
            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    pass  # Keep as string if not valid JSON
            
            # Cache in session (but skip v2_enabled to ensure fresh reads)
            if value is not None and key != 'v2_enabled':
                cache[cache_key] = value
                return value
            elif value is not None:
                return value
        
        return default
        
    except Exception as e:
        logger.warning(f"Error getting user preference '{key}': {e}")
        return default


def set_user_preference(key: str, value: Any) -> bool:
    """Set a user preference value.
    
    Updates both database and session cache.
    Works in both Flask and Streamlit contexts.
    
    Args:
        key: Preference key (e.g., 'timezone')
        value: Preference value (will be converted to JSONB-compatible format)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if not _is_authenticated():
            logger.warning("Cannot set preference: user not authenticated")
            return False
        
        user_id = _get_user_id()
        if not user_id:
            logger.warning("Cannot set preference: no user_id")
            return False
        
        # Get Supabase client (works in both contexts)
        client = None
        try:
            from streamlit_utils import get_supabase_client
            # Try to get token from Streamlit context
            try:
                from auth_utils import get_user_token
                user_token = get_user_token()
                client = get_supabase_client(user_token=user_token)
            except ImportError:
                client = get_supabase_client()
        except ImportError:
            # Flask context - need to get token from Flask request
            try:
                from supabase_client import SupabaseClient
                from flask_auth_utils import get_auth_token
                from flask import has_request_context
                
                if has_request_context():
                    # Get token from Flask cookies
                    user_token = get_auth_token()
                    client = SupabaseClient(user_token=user_token) if user_token else SupabaseClient()
                else:
                    client = SupabaseClient()
            except ImportError:
                logger.warning("Cannot set preference: no Supabase client available")
                return False
        
        if not client:
            logger.warning("Cannot set preference: no Supabase client")
            return False
        
        # Convert value to JSONB-compatible format
        # Supabase RPC expects JSONB as a JSON string
        json_value = json.dumps(value)
        
        # Call the RPC function to set preference
        # Note: Supabase will convert the JSON string to JSONB
        try:
            result = client.supabase.rpc('set_user_preference', {
                'pref_key': key,
                'pref_value': json_value
            }).execute()
            
            # Check if the RPC call succeeded
            # The function returns a boolean, but Supabase might wrap it
            logger.debug(f"RPC set_user_preference result: {result.data}, type: {type(result.data)}")
            
            # Handle different response formats
            if result.data is None:
                logger.warning(f"RPC set_user_preference returned None for key '{key}'")
                return False
            
            # Check if it's a boolean False
            if result.data is False:
                logger.warning(f"RPC set_user_preference returned False for key '{key}'")
                return False
            
            # Check if it's a list with False
            if isinstance(result.data, list) and len(result.data) > 0:
                if result.data[0] is False:
                    logger.warning(f"RPC set_user_preference returned [False] for key '{key}'")
                    return False
                # If it's a list with True, that's success
                if result.data[0] is True:
                    logger.info(f"RPC set_user_preference returned [True] for key '{key}'")
                else:
                    logger.warning(f"RPC set_user_preference returned unexpected list value: {result.data}")
                    return False
            
            # Update session cache strategy: INVALIDATE instead of WRITE-THROUGH
            # This is more robust as it forces a fresh DB read on next access,
            # preventing stale cache state if the session cookie update fails.
            cache = _get_cache()
            cache_key = f"_pref_{key}"
            if cache_key in cache:
                del cache[cache_key]
            
            logger.info(f"Successfully set preference '{key}' = {value}")
            return True
        except Exception as rpc_error:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"RPC call failed for set_user_preference('{key}', '{json_value}'): {rpc_error}")
            logger.error(f"Full traceback: {error_details}")
            return False
        
    except Exception as e:
        logger.error(f"Error setting user preference '{key}': {e}")
        return False


def get_user_timezone() -> Optional[str]:
    """Get user's preferred timezone.
    
    Returns:
        Timezone string (e.g., 'America/Los_Angeles') or None
    """
    return get_user_preference('timezone', default=None)


def set_user_timezone(timezone: str) -> bool:
    """Set user's preferred timezone.
    
    Args:
        timezone: Timezone string (e.g., 'America/Los_Angeles')
        
    Returns:
        True if successful, False otherwise
    """
    return set_user_preference('timezone', timezone)


def get_all_user_preferences() -> Dict[str, Any]:
    """Get all user preferences.
    
    Works in both Flask and Streamlit contexts.
    
    Returns:
        Dictionary of all preferences
    """
    try:
        if not _is_authenticated():
            return {}
        
        user_id = _get_user_id()
        if not user_id:
            return {}
        
        # Get Supabase client (works in both contexts)
        client = None
        try:
            from streamlit_utils import get_supabase_client
            # Try to get token from Streamlit context
            try:
                from auth_utils import get_user_token
                user_token = get_user_token()
                client = get_supabase_client(user_token=user_token)
            except ImportError:
                client = get_supabase_client()
        except ImportError:
            # Flask context - need to get token from Flask request
            try:
                from supabase_client import SupabaseClient
                from flask_auth_utils import get_auth_token
                from flask import has_request_context
                
                if has_request_context():
                    # Get token from Flask cookies
                    user_token = get_auth_token()
                    client = SupabaseClient(user_token=user_token) if user_token else SupabaseClient()
                else:
                    client = SupabaseClient()
            except ImportError:
                return {}
        
        if not client:
            return {}
        
        # Call the RPC function to get all preferences
        result = client.supabase.rpc('get_user_preferences').execute()
        
        if result.data is not None:
            # Handle both scalar and list responses
            if isinstance(result.data, list) and len(result.data) > 0:
                prefs = result.data[0]
            else:
                prefs = result.data
            
            if isinstance(prefs, dict):
                return prefs
        
        return {}
        
    except Exception as e:
        logger.warning(f"Error getting all user preferences: {e}")
        return {}


def get_user_currency() -> Optional[str]:
    """Get user's preferred currency.
    
    Returns:
        Currency code (e.g., 'CAD', 'USD') or None
    """
    # Import here to avoid circular dependency
    try:
        from streamlit_utils import SUPPORTED_CURRENCIES
    except ImportError:
        # Fallback if import fails
        SUPPORTED_CURRENCIES = {'CAD': 'Canadian Dollar', 'USD': 'US Dollar'}
    
    currency = get_user_preference('currency', default=None)
    # Validate against supported currencies
    if currency and currency in SUPPORTED_CURRENCIES:
        return currency
    return 'CAD'  # Default to CAD


def set_user_currency(currency: str) -> bool:
    """Set user's preferred currency.
    
    Args:
        currency: Currency code (e.g., 'CAD', 'USD')
        
    Returns:
        True if successful, False otherwise
    """
    # Import here to avoid circular dependency
    try:
        from streamlit_utils import SUPPORTED_CURRENCIES
    except ImportError:
        # Fallback if import fails
        SUPPORTED_CURRENCIES = {'CAD': 'Canadian Dollar', 'USD': 'US Dollar'}
    
    # Validate currency
    if currency not in SUPPORTED_CURRENCIES:
        logger.warning(f"Invalid currency: {currency}")
        return False
    return set_user_preference('currency', currency)


def clear_preference_cache():
    """Clear all preference caches from session (Flask or Streamlit)."""
    cache = _get_cache()
    keys_to_remove = [key for key in cache.keys() if key.startswith("_pref_")]
    for key in keys_to_remove:
        del cache[key]


def get_user_ai_model() -> Optional[str]:
    """Get user's preferred AI model.
    
    Fallback order:
    1. User's personal preference (from user_profiles.preferences)
    2. System default (from system_settings table)
    3. Environment variable OLLAMA_MODEL
    4. Hardcoded default 'llama3'
    
    Returns:
        Model name (e.g., 'llama3', 'mistral') or None
    """
    # Check user preference first
    user_model = get_user_preference('ai_model', default=None)
    if user_model:
        return user_model
    
    # Fall back to system setting
    try:
        from settings import get_system_setting
        system_model = get_system_setting("ai_default_model", default=None)
        if system_model:
            return system_model
    except Exception as e:
        logger.warning(f"Could not load system default model: {e}")
    
    # Fall back to hardcoded default (Granite 3.3)
    return "granite3.3:8b"

    # Fall back to environment variable (deprotilized in favor of Granite)
    # env_model = os.getenv("OLLAMA_MODEL")
    # if env_model:
    #     return env_model
    
    # Final fallback
    # return "llama3"


def set_user_ai_model(model: str) -> bool:
    """Set user's preferred AI model.
    
    Args:
        model: Model name (e.g., 'llama3', 'mistral')
        
    Returns:
        True if successful, False otherwise
    """
    if not model or not isinstance(model, str):
        logger.warning(f"Invalid AI model: {model}")
        return False
    return set_user_preference('ai_model', model)


# Theme options
THEME_OPTIONS = {
    'system': 'System Default',
    'dark': 'Dark Mode',
    'light': 'Light Mode'
}


def get_user_theme() -> str:
    """Get user's preferred theme.
    
    Returns:
        Theme preference: 'system', 'dark', or 'light'
    """
    theme = get_user_preference('theme', default=None)
    if theme and theme in THEME_OPTIONS:
        return theme
    return 'system'  # Default to system


def set_user_theme(theme: str) -> bool:
    """Set user's preferred theme.
    
    Args:
        theme: Theme preference ('system', 'dark', 'light')
        
    Returns:
        True if successful, False otherwise
    """
    if theme not in THEME_OPTIONS:
        logger.warning(f"Invalid theme: {theme}")
        return False
    return set_user_preference('theme', theme)


def get_user_selected_fund() -> Optional[str]:
    """Get user's preferred selected fund.
    
    Returns:
        Fund name (e.g., 'Project Chimera') or None
    """
    return get_user_preference('selected_fund', default=None)


def set_user_selected_fund(fund: str) -> bool:
    """Set user's preferred selected fund.
    
    Args:
        fund: Fund name (e.g., 'Project Chimera')
        
    Returns:
        True if successful, False otherwise
    """
    if not fund or not isinstance(fund, str):
        logger.warning(f"Invalid fund: {fund}")
        return False
    return set_user_preference('selected_fund', fund)


def apply_user_theme() -> None:
    """Apply user's theme preference using CSS injection.
    
    Call this early in each page to override browser dark mode detection.
    Works in Streamlit context only (Flask templates handle theme differently).
    """
    if not STREAMLIT_AVAILABLE or st is None:
        return  # Only works in Streamlit
    
    theme = get_user_theme()
    
    if theme == 'system':
        # Let the system handle it - no override needed
        return
    
    if theme == 'dark':
        # Force dark mode
        st.markdown("""
        <style>
            /* Force dark mode */
            :root {
                color-scheme: dark;
            }
            
            /* Override Streamlit's theme detection */
            [data-testid="stAppViewContainer"],
            [data-testid="stSidebar"],
            [data-testid="stHeader"],
            .main,
            .stApp {
                background-color: #0e1117 !important;
                color: #fafafa !important;
            }
            
            /* Inputs and widgets */
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea,
            [data-testid="stSelectbox"] > div,
            .stSelectbox > div > div {
                background-color: #262730 !important;
                color: #fafafa !important;
            }
            
            /* Cards and containers */
            [data-testid="stExpander"],
            .stAlert,
            .element-container {
                background-color: #262730 !important;
            }
            
            /* Ensure text is readable */
            p, span, label, h1, h2, h3, h4, h5, h6, li, td, th {
                color: #fafafa !important;
            }
        </style>
        """, unsafe_allow_html=True)
    
    elif theme == 'light':
        # Force light mode
        st.markdown("""
        <style>
            /* Force light mode */
            :root {
                color-scheme: light;
            }
            
            /* Override Streamlit's theme detection */
            [data-testid="stAppViewContainer"],
            [data-testid="stSidebar"],
            [data-testid="stHeader"],
            .main,
            .stApp {
                background-color: #ffffff !important;
                color: #31333F !important;
            }
            
            /* Inputs and widgets */
            [data-testid="stTextInput"] input,
            [data-testid="stTextArea"] textarea,
            [data-testid="stSelectbox"] > div,
            .stSelectbox > div > div {
                background-color: #f0f2f6 !important;
                color: #31333F !important;
            }
            
            /* Cards and containers */
            [data-testid="stExpander"],
            .stAlert,
            .element-container {
                background-color: #f0f2f6 !important;
            }
            
            /* Ensure text is readable */
            p, span, label, h1, h2, h3, h4, h5, h6, li, td, th {
                color: #31333F !important;
            }
        </style>
        """, unsafe_allow_html=True)


def format_timestamp_in_user_timezone(
    timestamp_str: str,
    format: str = "%Y-%m-%d %H:%M %Z"
) -> str:
    """Convert UTC timestamp string to user's preferred timezone.
    
    Parses a UTC timestamp string and converts it to the user's preferred
    timezone (from their settings). Falls back to Pacific Time (PST/PDT)
    if no timezone preference is set.
    
    Args:
        timestamp_str: UTC timestamp string (e.g., "2025-12-26 02:05 UTC" or "2025-12-26 02:05")
        format: Output format string (default: "%Y-%m-%d %H:%M %Z")
        
    Returns:
        Formatted timestamp in user's timezone (or PST if no preference)
    """
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        # Fallback for Python < 3.9
        try:
            import pytz
            HAS_PYTZ = True
        except ImportError:
            HAS_PYTZ = False
            # If neither available, just return the original string
            return timestamp_str
    
    # Parse the UTC timestamp string
    # Remove "UTC" suffix if present
    timestamp_clean = timestamp_str.replace(" UTC", "").strip()
    
    try:
        # Try parsing with format "YYYY-MM-DD HH:MM"
        dt_utc = datetime.strptime(timestamp_clean, "%Y-%m-%d %H:%M")
        
        # Add UTC timezone
        try:
            dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
        except NameError:
            if HAS_PYTZ:
                dt_utc = pytz.UTC.localize(dt_utc)
            else:
                return timestamp_str
        
        # Get user's timezone preference (fallback to PST)
        user_tz_str = get_user_timezone()
        if not user_tz_str:
            user_tz_str = "America/Vancouver"  # PST/PDT fallback
        
        # Convert to user's timezone
        try:
            user_tz = ZoneInfo(user_tz_str)
        except NameError:
            if HAS_PYTZ:
                user_tz = pytz.timezone(user_tz_str)
            else:
                return timestamp_str
        
        dt_user = dt_utc.astimezone(user_tz)
        return dt_user.strftime(format)
        
    except ValueError as e:
        logger.warning(f"Could not parse timestamp '{timestamp_str}': {e}")
        # If parsing fails, try to just remove UTC and return
        return timestamp_str.replace(" UTC", "")
    except Exception as e:
        logger.warning(f"Error converting timestamp to user timezone: {e}")
        # Fallback: just return the original string
        return timestamp_str