#!/usr/bin/env python3
"""
Flask Authentication Utilities
==============================

Helper functions for Flask routes to extract user information from auth_token cookie.
Shares the same cookie format as Streamlit auth system.
"""

import base64
import json
import logging
from typing import Optional, Dict
from flask import request

logger = logging.getLogger(__name__)


def get_auth_token() -> Optional[str]:
    """Get auth_token or session_token from cookies"""
    return request.cookies.get('auth_token') or request.cookies.get('session_token')


def get_refresh_token() -> Optional[str]:
    """Get refresh_token from cookies"""
    return request.cookies.get('refresh_token')


def get_user_id_flask() -> Optional[str]:
    """Extract user ID from auth_token/session_token cookie (Flask context)"""
    token = get_auth_token()
    if not token:
        return None
    
    try:
        # Parse JWT token
        # Handle simple encoding (no header) or full JWT
        token_parts = token.split('.')
        
        if len(token_parts) < 2:
            # Try to decode as raw payload if it's not a full JWT
            # session_token might be full JWT, auth_token definitely is
            return None
        
        # Decode payload
        payload = token_parts[1]
        # Add padding if needed
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        user_data = json.loads(decoded)
        
        # Extract user ID (Supabase uses 'sub', our session uses 'user_id')
        user_id = user_data.get('sub') or user_data.get('user_id')
        return user_id
    except Exception as e:
        logger.warning(f"Error extracting user ID from token: {e}")
        return None


def get_user_email_flask() -> Optional[str]:
    """Extract user email from auth_token cookie (Flask context)"""
    token = get_auth_token()
    if not token:
        return None
    
    try:
        # Parse JWT token
        token_parts = token.split('.')
        if len(token_parts) < 2:
            return None
        
        # Decode payload
        payload = token_parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        user_data = json.loads(decoded)
        
        # Extract email
        email = user_data.get('email')
        return email
    except Exception as e:
        logger.warning(f"Error extracting email from token: {e}")
        return None


def is_authenticated_flask() -> bool:
    """Check if user is authenticated (Flask context)"""
    token = get_auth_token()
    if not token:
        return False
    
    try:
        # Parse and validate token expiration
        token_parts = token.split('.')
        if len(token_parts) < 2:
            return False
        
        payload = token_parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        user_data = json.loads(decoded)
        
        # Check expiration
        exp = user_data.get('exp', 0)
        import time
        if exp > 0 and exp < time.time():
            return False
        
        return True
    except Exception as e:
        logger.warning(f"Error validating token: {e}")
        return False


def _decode_jwt_token(token: str) -> Optional[Dict]:
    """Decode JWT token without verification (for extracting user_id/email/access_token)"""
    try:
        token_parts = token.split('.')
        if len(token_parts) >= 2:
            payload = token_parts[1]
            payload += '=' * (4 - len(payload) % 4)  # Add padding if needed
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
    except Exception as e:
        logger.debug(f"Failed to decode JWT token: {e}")
    return None
