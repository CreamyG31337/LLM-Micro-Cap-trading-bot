#!/usr/bin/env python3
"""
Authentication utilities for Streamlit dashboard
Handles user login, session management, and token storage
"""

import os
import streamlit as st
from typing import Optional, Dict
import requests
import base64
import json
import time
from dotenv import load_dotenv
from supabase import create_client, Client
# CookieManager imported in functions where needed to avoid import errors at module level

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")


def login_user(email: str, password: str) -> Optional[Dict]:
    """Authenticate user with Supabase and return session data"""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        return None
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
            headers={
                "apikey": SUPABASE_PUBLISHABLE_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password
            }
        )
        
        if response.status_code == 200:
            auth_data = response.json()
            return {
                "access_token": auth_data.get("access_token"),
                "user": auth_data.get("user"),
                "expires_at": auth_data.get("expires_at")
            }
        else:
            error_data = response.json() if response.text else {}
            return {"error": error_data.get("msg", "Login failed")}
    except Exception as e:
        return {"error": str(e)}


def register_user(email: str, password: str) -> Optional[Dict]:
    """Register new user with Supabase"""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        return None
    
    try:
        response = requests.post(
            f"{SUPABASE_URL}/auth/v1/signup",
            headers={
                "apikey": SUPABASE_PUBLISHABLE_KEY,
                "Content-Type": "application/json"
            },
            json={
                "email": email,
                "password": password
            }
        )
        
        if response.status_code == 200:
            auth_data = response.json()
            # Supabase may return user without access_token if email confirmation is required
            return {
                "access_token": auth_data.get("access_token"),
                "user": auth_data.get("user"),
                "expires_at": auth_data.get("expires_at"),
                "requires_confirmation": auth_data.get("access_token") is None
            }
        else:
            error_data = {}
            try:
                error_data = response.json() if response.text else {}
            except:
                error_data = {"message": response.text or "Unknown error"}
            
            error_msg = error_data.get("msg") or error_data.get("message") or error_data.get("error_description") or "Registration failed"
            error_code = error_data.get("error") or error_data.get("error_code", "")
            
            if "database" in error_msg.lower() or "Database error" in error_msg:
                return {
                    "error": f"Database error: {error_msg}. This might be due to a database trigger failing. Check Supabase logs for details.",
                    "error_code": error_code,
                    "details": error_data
                }
            
            return {
                "error": error_msg,
                "error_code": error_code,
                "details": error_data
            }
    except Exception as e:
        return {"error": str(e)}


def get_user_token() -> Optional[str]:
    """Get current user's access token from session state"""
    if "user_token" in st.session_state:
        return st.session_state.user_token
    return None


def get_user_id() -> Optional[str]:
    """Get current user's ID from session state"""
    if "user_id" in st.session_state:
        return st.session_state.user_id
    return None


def get_user_email() -> Optional[str]:
    """Get current user's email from session state"""
    if "user_email" in st.session_state:
        return st.session_state.user_email
    return None


def is_authenticated() -> bool:
    """Check if user is authenticated (checks session_state only)"""
    # Session should be restored from cookie at app start, so just check session_state
    return "user_token" in st.session_state and st.session_state.user_token is not None


def logout_user():
    """Clear user session"""
    if "user_token" in st.session_state:
        del st.session_state.user_token
    if "user_id" in st.session_state:
        del st.session_state.user_id
    if "user_email" in st.session_state:
        del st.session_state.user_email
    # Clear cookie flag so next login will set a fresh cookie
    if "session_restored_from_cookie" in st.session_state:
        del st.session_state.session_restored_from_cookie
    
    # Redirect through set_cookie.html to clear the cookie
    # (Streamlit can't clear cookies directly due to iframe sandboxing)
    st.markdown(
        '<meta http-equiv="refresh" content="0; url=/set_cookie.html?action=clear">',
        unsafe_allow_html=True
    )
    st.write("Logging out...")
    st.stop()


def set_user_session(access_token: str, user: Optional[Dict] = None, skip_cookie_redirect: bool = False):
    """Store user session data. If user is None, decode from JWT token.
    
    Args:
        access_token: The JWT access token
        user: Optional user dict with id and email
        skip_cookie_redirect: If True, don't redirect to set cookie (used when restoring from cookie)
    """
    st.session_state.user_token = access_token
    
    if user:
        st.session_state.user_id = user.get("id")
        st.session_state.user_email = user.get("email")
    else:
        # Decode user info from JWT token if user object not provided
        try:
            token_parts = access_token.split('.')
            if len(token_parts) >= 2:
                payload = token_parts[1]
                # Add padding if needed (JWT uses base64url)
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                user_data = json.loads(decoded)
                st.session_state.user_id = user_data.get("sub")
                st.session_state.user_email = user_data.get("email")
            else:
                st.session_state.user_id = None
                st.session_state.user_email = None
        except Exception:
            # If decoding fails, just store token
            st.session_state.user_id = None
            st.session_state.user_email = None
    
    # For email/password login, redirect through set_cookie.html to persist the cookie
    # (Streamlit can't set cookies directly due to iframe sandboxing)
    # Skip if restoring from cookie (to avoid infinite loop)
    if not skip_cookie_redirect and "session_restored_from_cookie" not in st.session_state:
        import urllib.parse
        encoded_token = urllib.parse.quote(access_token, safe='')
        
        # Store token temporarily in session state (will be cleared after redirect)
        st.session_state._pending_cookie_token = access_token
        
        # Use JavaScript via st.markdown with meta refresh (not stripped like script tags)
        # This will redirect the ENTIRE page, not just an iframe
        redirect_url = f'/set_cookie.html?token={encoded_token}'
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={redirect_url}">',
            unsafe_allow_html=True
        )
        st.write("Saving session... Redirecting...")
        st.stop()  # Stop execution - we'll continue after redirect back
    
    # Mark that session is set (either from cookie restore or after redirect)
    st.session_state.session_restored_from_cookie = True


def request_password_reset(email: str) -> Optional[Dict]:
    """Request password reset email from Supabase"""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        return None
    
    # Redirect to auth callback page which processes hash and redirects to Streamlit
    redirect_url = os.getenv("MAGIC_LINK_REDIRECT_URL", "https://ai-trading.hobo.cash/auth_callback.html")
    
    try:
        # Use Supabase client library which handles redirect_to correctly
        # Note: reset_password_for_email() returns None on success, raises exception on failure
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
        supabase.auth.reset_password_for_email(
            email,
            {
                "redirect_to": redirect_url
            }
        )
        # If we get here, no exception was raised = success
        return {"success": True, "message": "Password reset email sent"}
    except Exception as e:
        return {"error": str(e)}


def send_magic_link(email: str) -> Optional[Dict]:
    """Send magic link login email from Supabase"""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        return None
    
    # Redirect to auth callback page which processes hash and redirects to Streamlit
    redirect_url = os.getenv("MAGIC_LINK_REDIRECT_URL", "https://ai-trading.hobo.cash/auth_callback.html")
    
    try:
        # Use Supabase client library which handles redirect_to correctly
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
        response = supabase.auth.sign_in_with_otp({
            "email": email,
            "options": {
                "email_redirect_to": redirect_url
            }
        })
        
        if response:
            return {"success": True, "message": "Magic link sent to your email"}
        else:
            return {"error": "Failed to send magic link"}
    except Exception as e:
        return {"error": str(e)}


def is_admin() -> bool:
    """Check if current user is admin by querying user_profiles table using SQL function"""
    user_id = get_user_id()
    if not user_id:
        return False
    
    try:
        from streamlit_utils import get_supabase_client
        client = get_supabase_client()
        if not client:
            return False
        
        # Call the is_admin SQL function
        result = client.supabase.rpc('is_admin', {'user_uuid': user_id}).execute()
        
        if result.data:
            return result.data[0] if isinstance(result.data[0], bool) else bool(result.data[0])
        return False
    except Exception as e:
        import logging
        logging.error(f"Error checking admin status: {e}")
        return False

