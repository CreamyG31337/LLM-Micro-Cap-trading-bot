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


def clear_preference_cache():
    """Clear all preference caches from session state."""
    keys_to_remove = [key for key in st.session_state.keys() if key.startswith("_pref_")]
    for key in keys_to_remove:
        del st.session_state[key]

