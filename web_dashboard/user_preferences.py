#!/usr/bin/env python3
"""
User Preferences Utilities
===========================

Functions for getting and setting user preferences in the database.
Uses session state as a cache for performance.
"""

import streamlit as st
from typing import Optional, Any, Dict
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def get_user_preference(key: str, default: Any = None) -> Any:
    """Get a user preference value.
    
    Checks session state cache first, then falls back to database.
    Caches the result in session state for performance.
    
    Args:
        key: Preference key (e.g., 'timezone')
        default: Default value if preference not found
        
    Returns:
        Preference value or default
    """
    # Check session state cache first
    cache_key = f"_pref_{key}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    
    # Try to get from database
    try:
        from auth_utils import get_user_id, is_authenticated
        from streamlit_utils import get_supabase_client
        
        if not is_authenticated():
            return default
        
        user_id = get_user_id()
        if not user_id:
            return default
        
        client = get_supabase_client()
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
            
            # Cache in session state
            if value is not None:
                st.session_state[cache_key] = value
                return value
        
        return default
        
    except Exception as e:
        logger.warning(f"Error getting user preference '{key}': {e}")
        return default


def set_user_preference(key: str, value: Any) -> bool:
    """Set a user preference value.
    
    Updates both database and session state cache.
    
    Args:
        key: Preference key (e.g., 'timezone')
        value: Preference value (will be converted to JSONB-compatible format)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from auth_utils import get_user_id, is_authenticated
        from streamlit_utils import get_supabase_client
        
        if not is_authenticated():
            logger.warning("Cannot set preference: user not authenticated")
            return False
        
        user_id = get_user_id()
        if not user_id:
            logger.warning("Cannot set preference: no user_id")
            return False
        
        client = get_supabase_client()
        if not client:
            logger.warning("Cannot set preference: no Supabase client")
            return False
        
        # Convert value to JSONB-compatible format
        # Supabase RPC expects JSONB as a JSON string
        json_value = json.dumps(value)
        
        # Call the RPC function to set preference
        # Note: Supabase will convert the JSON string to JSONB
        result = client.supabase.rpc('set_user_preference', {
            'pref_key': key,
            'pref_value': json_value
        }).execute()
        
        # Update session state cache
        cache_key = f"_pref_{key}"
        st.session_state[cache_key] = value
        
        return True
        
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
    
    Returns:
        Dictionary of all preferences
    """
    try:
        from auth_utils import get_user_id, is_authenticated
        from streamlit_utils import get_supabase_client
        
        if not is_authenticated():
            return {}
        
        user_id = get_user_id()
        if not user_id:
            return {}
        
        client = get_supabase_client()
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
    """Clear all preference caches from session state."""
    keys_to_remove = [key for key in st.session_state.keys() if key.startswith("_pref_")]
    for key in keys_to_remove:
        del st.session_state[key]


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
    
    # Fall back to environment variable
    env_model = os.getenv("OLLAMA_MODEL")
    if env_model:
        return env_model
    
    # Final fallback
    return "llama3"


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