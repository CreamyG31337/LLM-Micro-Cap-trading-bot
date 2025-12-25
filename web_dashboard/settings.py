#!/usr/bin/env python3
"""
System Settings Module
======================

Helper functions for reading and writing global system settings.
Settings are stored in the `system_settings` table as key-value pairs.
"""

from typing import Optional, Any
import json
import logging

logger = logging.getLogger(__name__)


def get_system_setting(key: str, default: Any = None) -> Any:
    """Get a system setting value.
    
    Args:
        key: Setting key
        default: Default value if setting not found
        
    Returns:
        Setting value (parsed from JSONB) or default
    """
    try:
        from streamlit_utils import get_supabase_client
        
        client = get_supabase_client()
        if not client:
            logger.warning("Could not connect to database for system settings")
            return default
        
        result = client.supabase.table("system_settings").select("value").eq("key", key).execute()
        
        if result.data and len(result.data) > 0:
            # Value is stored as JSONB, extract the actual value
            jsonb_value = result.data[0].get("value")
            # JSONB is already parsed by Supabase client
            return jsonb_value
        
        return default
        
    except Exception as e:
        logger.error(f"Error getting system setting '{key}': {e}")
        return default


def set_system_setting(key: str, value: Any, description: Optional[str] = None) -> bool:
    """Set a system setting value.
    
    Args:
        key: Setting key
        value: Setting value (will be stored as JSONB)
        description: Optional description of the setting
        
    Returns:
        True if successful, False otherwise
    """
    try:
        from streamlit_utils import get_supabase_client
        from auth_utils import get_user_id
        
        client = get_supabase_client()
        if not client:
            logger.error("Could not connect to database for system settings")
            return False
        
        user_id = get_user_id()
        
        # Prepare the data
        # Supabase handles JSONB conversion automatically, just pass the value
        data = {
            "key": key,
            "value": value,  # Supabase will handle JSON conversion
            "updated_by": user_id
        }
        
        if description:
            data["description"] = description
        
        # Upsert (insert or update)
        result = client.supabase.table("system_settings").upsert(data).execute()
        
        if result.data:
            logger.info(f"System setting '{key}' updated successfully")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error setting system setting '{key}': {e}")
        return False


def get_all_system_settings() -> dict:
    """Get all system settings as a dictionary.
    
    Returns:
        Dictionary of key-value pairs
    """
    try:
        from streamlit_utils import get_supabase_client
        
        client = get_supabase_client()
        if not client:
            return {}
        
        result = client.supabase.table("system_settings").select("key, value").execute()
        
        if result.data:
            return {row["key"]: row["value"] for row in result.data}
        
        return {}
        
    except Exception as e:
        logger.error(f"Error getting all system settings: {e}")
        return {}
