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
        cached_value = cache[cache_key]
        logger.debug(f"[PREF] Cache hit for '{key}': {cached_value} (type: {type(cached_value).__name__})")
        # If cache has None but we know the value exists (from get_all_user_preferences),
        # bypass cache and read from DB
        if cached_value is None:
            logger.debug(f"[PREF] Cache has None for '{key}', bypassing cache to check DB")
        else:
            return cached_value
    
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
        
        # Debug logging
        logger.debug(f"[PREF] RPC result for '{key}': data={result.data}, type={type(result.data).__name__}, raw={repr(result.data)}")
        
        # The RPC function returns JSONB, which Supabase returns as:
        # - None if the key doesn't exist or value is NULL
        # - The actual value (str, bool, int, etc.) if it's a scalar JSONB
        # - A dict/list if it's a complex JSONB
        # - Sometimes wrapped in a list
        
        if result.data is not None:
            # Handle both scalar and list responses
            if isinstance(result.data, list):
                if len(result.data) == 0:
                    # Empty list means no value
                    logger.debug(f"[PREF] Empty list returned for '{key}', returning default")
                    return default
                # Extract first element (Supabase sometimes wraps in list)
                value = result.data[0]
                logger.debug(f"[PREF] Extracted from list: value={value}, type={type(value).__name__}")
            else:
                value = result.data
                logger.debug(f"[PREF] Using direct value: value={value}, type={type(value).__name__}")
            
            # Handle None/null values
            if value is None:
                logger.debug(f"[PREF] Value is None for '{key}', returning default")
                return default
            
            # If it's a dict, it might be a wrapped JSONB object - try to extract the value
            # Some Supabase clients return JSONB as {"value": "actual_value"} or similar
            if isinstance(value, dict):
                logger.debug(f"[PREF] Value is dict for '{key}': {value}")
                # Try common keys that might contain the actual value
                if 'value' in value:
                    value = value['value']
                    logger.debug(f"[PREF] Extracted 'value' key: {value}")
                elif len(value) == 1:
                    # If dict has only one key, use that value
                    value = list(value.values())[0]
                    logger.debug(f"[PREF] Extracted single dict value: {value}")
                # Otherwise, keep the dict as-is (might be intentional)
            
            # If it's a string, check if it's JSON-encoded
            if isinstance(value, str):
                # Check if it's a JSON-encoded string (starts/ends with quotes or is valid JSON)
                value_stripped = value.strip()
                if value_stripped.lower() == 'null':
                    logger.debug(f"[PREF] Value is 'null' string for '{key}', returning default")
                    return default
                # Try to parse as JSON (handles JSON-encoded strings like "\"value\"")
                try:
                    parsed = json.loads(value)
                    # Only use parsed value if it's different from original
                    # (avoids double-parsing already decoded values)
                    # But if parsed is a string, use it (it was JSON-encoded)
                    if isinstance(parsed, str) or parsed != value:
                        logger.debug(f"[PREF] Parsed JSON string for '{key}': {parsed}")
                        value = parsed
                except (json.JSONDecodeError, TypeError):
                    # Not JSON-encoded, use as-is
                    logger.debug(f"[PREF] Value is plain string for '{key}': {value}")
                    pass
            
            # Handle boolean JSONB values - they might come as:
            # - Python bool (True/False) - already correct
            # - String "true"/"false" - need conversion
            # - JSONB true/false - Supabase should convert to Python bool, but check anyway
            if isinstance(value, bool):
                # Already a boolean, use as-is
                pass
            elif isinstance(value, str) and value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
                logger.debug(f"[PREF] Converted string boolean for '{key}': {value}")
            elif value in (True, False, 1, 0, '1', '0'):
                # Handle other truthy/falsy representations
                value = bool(value) if not isinstance(value, bool) else value
                logger.debug(f"[PREF] Normalized boolean for '{key}': {value}")
            
            # Handle None after parsing
            if value is None or (isinstance(value, str) and value.lower() == 'null'):
                logger.debug(f"[PREF] Value is None/null after parsing for '{key}', returning default")
                return default
            
            logger.debug(f"[PREF] Final value for '{key}': {value} (type: {type(value).__name__})")
            
            # Return the value (don't cache v2_enabled to ensure fresh reads)
            if value is not None:
                if key != 'v2_enabled':
                    cache[cache_key] = value
                return value
        
        logger.debug(f"[PREF] No value found for '{key}', returning default")
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
        user_token = None
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
                    if user_token:
                        logger.info(f"[PREF] Creating SupabaseClient with token (length: {len(user_token)}) for preference '{key}'")
                        client = SupabaseClient(user_token=user_token)
                        # Verify the client has the token set
                        if hasattr(client, '_user_token') and client._user_token:
                            logger.info(f"[PREF] Client token verified: {client._user_token[:20]}...")
                        else:
                            logger.warning(f"[PREF] Client created but _user_token not set!")
                    else:
                        logger.warning(f"[PREF] No token available for preference '{key}' - creating client without token")
                        client = SupabaseClient()
                else:
                    logger.warning(f"[PREF] No Flask request context for preference '{key}' - creating client without token")
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
        rpc_success = False
        rpc_error_msg = None
        try:
            logger.info(f"Calling RPC set_user_preference with key='{key}', user_id='{user_id}'")
            
            # Ensure Authorization header is set right before RPC call
            # (in case client was reused or header was cleared)
            if hasattr(client, 'supabase') and hasattr(client.supabase, 'postgrest'):
                postgrest = client.supabase.postgrest
                if hasattr(postgrest, 'session') and user_token:
                    # Ensure header is set on the session
                    if not hasattr(postgrest.session, 'headers'):
                        postgrest.session.headers = {}
                    postgrest.session.headers['Authorization'] = f'Bearer {user_token}'
                    logger.debug(f"[PREF] Ensured Authorization header is set before RPC call")
            
            result = client.supabase.rpc('set_user_preference', {
                'pref_key': key,
                'pref_value': json_value
                # Don't pass user_uuid - let auth.uid() work from Authorization header
            }).execute()
            
            # Check if the RPC call succeeded
            # The function returns a boolean, but Supabase might wrap it
            logger.info(f"RPC set_user_preference result: {result.data}, type: {type(result.data)}")
            
            # Handle different response formats
            if result.data is None:
                rpc_error_msg = f"RPC returned None for key '{key}'"
                logger.warning(rpc_error_msg)
            elif result.data is False:
                rpc_error_msg = f"RPC returned False for key '{key}'"
                logger.warning(rpc_error_msg)
            elif result.data is True:
                rpc_success = True
            elif isinstance(result.data, list) and len(result.data) > 0:
                if result.data[0] is True:
                    rpc_success = True
                elif result.data[0] is False:
                    rpc_error_msg = f"RPC returned [False] for key '{key}'"
                    logger.warning(rpc_error_msg)
                else:
                    rpc_error_msg = f"RPC returned unexpected list value: {result.data}"
                    logger.warning(rpc_error_msg)
            else:
                rpc_error_msg = f"RPC returned unexpected value: {result.data}"
                logger.warning(rpc_error_msg)
        except Exception as rpc_error:
            rpc_error_msg = f"RPC call failed: {str(rpc_error)}"
            logger.warning(f"{rpc_error_msg}, trying HTTP fallback", exc_info=True)
            rpc_success = False
        
        # Fallback to direct HTTP request if RPC client call failed
        if not rpc_success and user_token:
            try:
                import requests
                import os
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_anon_key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
                
                if supabase_url and supabase_anon_key:
                    logger.info(f"Trying HTTP fallback for set_user_preference with key='{key}'")
                    response = requests.post(
                        f"{supabase_url}/rest/v1/rpc/set_user_preference",
                        headers={
                            "apikey": supabase_anon_key,
                            "Authorization": f"Bearer {user_token}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "pref_key": key,
                            "pref_value": json_value
                            # Don't pass user_uuid - let auth.uid() work from Authorization header
                        }
                    )
                    
                    if response.status_code == 200:
                        result_data = response.json()
                        logger.info(f"HTTP fallback RPC result: {result_data}, type: {type(result_data)}")
                        if result_data is True or (isinstance(result_data, list) and len(result_data) > 0 and result_data[0] is True):
                            rpc_success = True
                        else:
                            logger.warning(f"HTTP fallback returned False: {result_data}")
                    else:
                        logger.error(f"HTTP fallback failed with status {response.status_code}: {response.text}")
            except Exception as http_error:
                logger.error(f"HTTP fallback also failed: {http_error}", exc_info=True)
        
        if not rpc_success:
            error_details = rpc_error_msg or "Unknown error"
            if user_token:
                error_details += " (HTTP fallback also attempted)"
            logger.error(f"Both RPC client and HTTP fallback failed for preference '{key}': {error_details}")
            # Store error in cache so UI can display it
            cache = _get_cache()
            cache[f"_pref_error_{key}"] = error_details
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

        
    except Exception as e:
        logger.error(f"Error setting user preference '{key}': {e}")
        return False


def get_user_timezone() -> Optional[str]:
    """Get user's preferred timezone.
    
    Returns:
        Timezone string (e.g., 'America/Los_Angeles') or None
    """
    # Try direct preference lookup first
    timezone = get_user_preference('timezone', default=None)
    
    # Fallback: if direct lookup returns None but we know preferences exist,
    # try getting all preferences and extracting timezone from there
    # This works around issues where the RPC might return None for specific keys
    if timezone is None:
        try:
            all_prefs = get_all_user_preferences()
            if isinstance(all_prefs, dict) and 'timezone' in all_prefs:
                timezone = all_prefs['timezone']
                # Ensure it's a string (handle any JSONB wrapping)
                if isinstance(timezone, str):
                    timezone = timezone.strip()
                elif timezone is not None:
                    timezone = str(timezone).strip()
                logger.debug(f"[PREF] Retrieved timezone from get_all_user_preferences(): {timezone}")
                # Cache it for future use
                cache = _get_cache()
                cache_key = "_pref_timezone"
                if timezone:
                    cache[cache_key] = timezone
        except Exception as e:
            logger.warning(f"Error getting timezone from all preferences: {e}")
    
    return timezone if timezone else None


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
    
    # Try direct preference lookup first
    currency = get_user_preference('currency', default=None)
    
    # Fallback: if direct lookup returns None, try getting all preferences
    if currency is None:
        try:
            all_prefs = get_all_user_preferences()
            if isinstance(all_prefs, dict) and 'currency' in all_prefs:
                currency = all_prefs['currency']
                # Ensure it's a string
                if isinstance(currency, str):
                    currency = currency.strip().upper()
                elif currency is not None:
                    currency = str(currency).strip().upper()
                logger.debug(f"[PREF] Retrieved currency from get_all_user_preferences(): {currency}")
                # Cache it for future use
                cache = _get_cache()
                cache_key = "_pref_currency"
                if currency:
                    cache[cache_key] = currency
        except Exception as e:
            logger.warning(f"Error getting currency from all preferences: {e}")
    
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
    # Try direct preference lookup first
    theme = get_user_preference('theme', default=None)
    
    # Fallback: if direct lookup returns None, try getting all preferences
    if theme is None:
        try:
            all_prefs = get_all_user_preferences()
            if isinstance(all_prefs, dict) and 'theme' in all_prefs:
                theme = all_prefs['theme']
                # Ensure it's a string
                if isinstance(theme, str):
                    theme = theme.strip().lower()
                elif theme is not None:
                    theme = str(theme).strip().lower()
                logger.debug(f"[PREF] Retrieved theme from get_all_user_preferences(): {theme}")
                # Cache it for future use
                cache = _get_cache()
                cache_key = "_pref_theme"
                if theme:
                    cache[cache_key] = theme
        except Exception as e:
            logger.warning(f"Error getting theme from all preferences: {e}")
    
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