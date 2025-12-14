#!/usr/bin/env python3
"""
Streamlit Portfolio Performance Dashboard
Displays historical performance graphs and current portfolio data
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
from pathlib import Path
import base64
import json
import time
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamlit_utils import (
    get_available_funds,
    get_current_positions,
    get_trade_log,
    get_cash_balances,
    calculate_portfolio_value_over_time,
    get_supabase_client,
    get_investor_count,
    get_investor_allocations,
    get_user_investment_metrics
)
from chart_utils import (
    create_portfolio_value_chart,
    create_performance_by_fund_chart,
    create_pnl_chart,
    create_trades_timeline_chart,
    create_currency_exposure_chart,
    create_sector_allocation_chart,
    create_investor_allocation_chart
)
from auth_utils import (
    login_user,
    register_user,
    is_authenticated,
    logout_user,
    set_user_session,
    get_user_email,
    get_user_id,
    get_user_token,
    is_admin
)

# Page configuration
st.set_page_config(
    page_title="Portfolio Performance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (dark mode compatible)
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: var(--secondary-background-color);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)


def show_login_page():
    """Display login/register page"""
    st.markdown('<div class="main-header">📈 Portfolio Performance Dashboard</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])
    
    with tab1:
        st.markdown("### Login")
        
        # Magic link option
        use_magic_link = st.checkbox("Send magic link instead", key="use_magic_link")
        
        with st.form("login_form"):
            email = st.text_input("Email", type="default", key="login_email")
            
            if not use_magic_link:
                password = st.text_input("Password", type="password", key="login_password")
            else:
                password = None
                st.info("A magic link will be sent to your email. Click the link to log in.")
            
            submit = st.form_submit_button("Login" if not use_magic_link else "Send Magic Link")
            
            if submit:
                if email:
                    if use_magic_link:
                        # Send magic link
                        from auth_utils import send_magic_link
                        result = send_magic_link(email)
                        if result and result.get("success"):
                            st.success(result.get("message", "Magic link sent! Check your email."))
                        else:
                            error_msg = result.get("error", "Failed to send magic link") if result else "Failed to send magic link"
                            st.error(f"Error: {error_msg}")
                    else:
                        # Regular password login
                        if password:
                            result = login_user(email, password)
                            if result and "access_token" in result:
                                set_user_session(result["access_token"], result["user"])
                                st.success("Login successful!")
                                st.rerun()
                            else:
                                error_msg = result.get("error", "Login failed") if result else "Login failed"
                                st.error(f"Login failed: {error_msg}")
                        else:
                            st.error("Please enter your password")
                else:
                    st.error("Please enter your email")
    
    with tab2:
        st.markdown("### Register")
        with st.form("register_form"):
            email = st.text_input("Email", type="default", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reg_confirm")
            submit = st.form_submit_button("Register")
            
            if submit:
                if email and password and confirm_password:
                    if password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        result = register_user(email, password)
                        if result and not result.get("error"):
                            # Registration succeeded
                            if result.get("access_token"):
                                # User is logged in immediately (email confirmation not required)
                                set_user_session(result["access_token"], result.get("user"))
                                st.success("✅ Registration successful! You are now logged in.")
                                st.rerun()
                            else:
                                # Email confirmation required
                                st.info("📧 **Registration successful!** Please check your email to confirm your account. Click the confirmation link in the email to complete registration.")
                        else:
                            error_msg = result.get("error", "Registration failed") if result else "Registration failed"
                            st.error(f"❌ Registration failed: {error_msg}")
                else:
                    st.error("Please fill in all fields")
    
    with tab3:
        st.markdown("### Reset Password")
        st.info("Enter your email address and we'll send you a password reset link.")
        
        with st.form("reset_password_form"):
            email = st.text_input("Email", type="default", key="reset_email")
            submit = st.form_submit_button("Send Reset Link")
            
            if submit:
                if email:
                    from auth_utils import request_password_reset
                    result = request_password_reset(email)
                    if result and result.get("success"):
                        st.success(result.get("message", "Password reset email sent! Check your inbox."))
                    else:
                        error_msg = result.get("error", "Failed to send reset email") if result else "Failed to send reset email"
                        st.error(f"Error: {error_msg}")
                else:
                    st.error("Please enter your email address")


def show_password_reset_page(access_token: str):
    """Display dedicated password reset page"""
    # Add link back to main page
    st.markdown('[← Back to Main Page](/)', unsafe_allow_html=True)
    st.markdown('<div class="main-header">🔐 Reset Your Password</div>', unsafe_allow_html=True)
    
    # Check if password reset already completed
    if st.session_state.get("password_reset_completed"):
        st.success("✅ **Password reset completed successfully!**")
        st.info("You can now log in with your new password.")
        st.markdown(f'[Click here to go to the main page](/) or wait 5 seconds to be redirected automatically.')
        st.markdown("""
        <script>
        setTimeout(function() {
            window.location.href = window.location.origin;
        }, 5000);
        </script>
        """, unsafe_allow_html=True)
        return
    
    # Check token expiration before showing form
    try:
        token_parts = access_token.split('.')
        if len(token_parts) >= 2:
            payload = token_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            user_data = json.loads(decoded)
            exp = user_data.get("exp", 0)
            current_time = int(time.time())
            
            if exp < current_time:
                st.error("❌ **Reset link expired** - This password reset link has expired. Please request a new one.")
                st.markdown(f'[Click here to go back to the main page](/) or wait 5 seconds to be redirected automatically.')
                st.markdown("""
                <script>
                setTimeout(function() {
                    window.location.href = window.location.origin;
                }, 5000);
                </script>
                """, unsafe_allow_html=True)
                return
        else:
            st.error("❌ **Invalid reset token** - The reset link is invalid.")
            st.markdown(f'[Click here to go back to the main page](/) or wait 5 seconds to be redirected automatically.')
            st.markdown("""
            <script>
            setTimeout(function() {
                window.location.href = window.location.origin;
            }, 5000);
            </script>
            """, unsafe_allow_html=True)
            return
    except Exception as e:
        st.error(f"❌ **Error processing reset token** - {e}")
        st.markdown(f'[Click here to go back to the main page](/) or wait 5 seconds to be redirected automatically.')
        st.markdown("""
        <script>
        setTimeout(function() {
            window.location.href = window.location.origin;
        }, 5000);
        </script>
        """, unsafe_allow_html=True)
        return
    
    # Set session with reset token first (required for password update)
    if "reset_token" not in st.session_state or st.session_state.reset_token != access_token:
        try:
            # Decode JWT to get user info
            token_parts = access_token.split('.')
            if len(token_parts) >= 2:
                payload = token_parts[1]
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                user_data = json.loads(decoded)
                
                user = {
                    "id": user_data.get("sub"),
                    "email": user_data.get("email")
                }
                
                # Set session with reset token
                set_user_session(access_token, user)
                st.session_state.reset_token = access_token
        except Exception as e:
            st.error(f"Error processing reset token: {e}")
            return
    
    # Show password reset form
    st.markdown("### Enter Your New Password")
    st.info("Please enter your new password below. Make sure it's strong and memorable.")
    
    with st.form("new_password_form"):
        new_password = st.text_input("New Password", type="password", key="new_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_new_password")
        submit = st.form_submit_button("Update Password", use_container_width=True)
        
        if submit:
            if new_password and confirm_password:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Update password using Supabase client with proper session validation
                    import os
                    from supabase import create_client
                    import requests
                    
                    supabase_url = os.getenv("SUPABASE_URL")
                    supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
                    
                    if not supabase_url or not supabase_key:
                        st.error("❌ **Error**: Supabase configuration missing. Please contact support.")
                        st.stop()
                        return
                    
                    # Extract email from token for verification and display
                    user_email = None
                    try:
                        token_parts = access_token.split('.')
                        if len(token_parts) >= 2:
                            payload = token_parts[1]
                            payload += '=' * (4 - len(payload) % 4)
                            decoded = base64.urlsafe_b64decode(payload)
                            user_data = json.loads(decoded)
                            user_email = user_data.get("email")
                    except Exception as decode_error:
                        st.error(f"❌ **Error**: Failed to decode recovery token: {decode_error}")
                        if is_admin():
                            with st.expander("🔍 Debug Information"):
                                st.write(f"Token length: {len(access_token)}")
                                st.write(f"Token parts: {len(token_parts) if 'token_parts' in locals() else 'N/A'}")
                                st.exception(decode_error)
                        return
                    
                    if not user_email:
                        st.error("❌ **Error**: Could not extract email from recovery token. Please request a new reset link.")
                        return
                    
                    # Show status and try Supabase client first
                    status_container = st.container()
                    with status_container:
                        st.info(f"🔄 **Status**: Preparing to update password for {user_email}...")
                    
                    try:
                        # Try using Supabase client first
                        supabase = create_client(supabase_url, supabase_key)
                        
                        # Attempt to set session with recovery token
                        # Note: Recovery tokens may not have refresh_token, so this might fail
                        with status_container:
                            st.info("🔄 **Status**: Attempting to authenticate with Supabase client...")
                        
                        try:
                            # Try to set session - this may fail for recovery tokens without refresh_token
                            # But we'll try it first as it's the preferred method
                            session_response = supabase.auth.set_session(
                                access_token=access_token,
                                refresh_token=""  # Recovery tokens typically don't have this
                            )
                            
                            # Check if session was established
                            if session_response and hasattr(session_response, 'user') and session_response.user:
                                with status_container:
                                    st.success("✅ **Status**: Authenticated with Supabase client successfully!")
                                
                                # Use Supabase client to update password
                                with status_container:
                                    st.info("🔄 **Status**: Updating password using Supabase client...")
                                
                                user_response = supabase.auth.update_user({"password": new_password})
                                
                                if user_response and hasattr(user_response, 'user') and user_response.user:
                                    # Success using Supabase client
                                    with status_container:
                                        st.success("✅ **Status**: Password updated successfully using Supabase client!")
                                    
                                    st.session_state.password_reset_completed = True
                                    st.success("✅ **Password updated successfully!**")
                                    st.info("🔄 **Redirecting to main page...** You can now log in with your new password.")
                                    st.markdown(f'[Click here to go to the main page](/) or wait 5 seconds to be redirected automatically.')
                                    
                                    logout_user()
                                    if "reset_token" in st.session_state:
                                        del st.session_state.reset_token
                                    
                                    st.markdown("""
                                    <script>
                                    setTimeout(function() {
                                        window.location.href = window.location.origin;
                                    }, 5000);
                                    </script>
                                    """, unsafe_allow_html=True)
                                    
                                    st.rerun()
                                else:
                                    with status_container:
                                        st.warning("⚠️ **Status**: Supabase client update_user() returned invalid response, falling back to REST API...")
                                    raise Exception("Supabase client update_user() returned invalid response")
                            else:
                                with status_container:
                                    st.warning("⚠️ **Status**: Could not establish session with Supabase client (recovery tokens may not support this), falling back to REST API...")
                                raise Exception("Could not establish session with Supabase client")
                                
                        except Exception as client_error:
                            # Supabase client method failed, fall back to REST API
                            with status_container:
                                st.info(f"🔄 **Status**: Supabase client method unavailable ({str(client_error)[:50]}...), using REST API instead...")
                            
                            # Use REST API with access_token directly
                            # This validates the token server-side via JWT verification
                            with status_container:
                                st.info("🔄 **Status**: Sending password update request to Supabase REST API...")
                            
                            response = requests.put(
                                f"{supabase_url}/auth/v1/user",
                                headers={
                                    "apikey": supabase_key,
                                    "Authorization": f"Bearer {access_token}",
                                    "Content-Type": "application/json"
                                },
                                json={"password": new_password},
                                timeout=10
                            )
                            
                            with status_container:
                                st.info(f"📡 **Status**: Received response from Supabase API (HTTP {response.status_code})")
                            
                            if response.status_code == 200:
                                response_data = response.json() if response.text else {}
                                
                                # Show response data for debugging
                                with st.expander("🔍 API Response Details"):
                                    st.json(response_data)
                                
                                # Check truthiness consistently for all fields
                                if response_data.get("id") or response_data.get("user") or response_data.get("email"):
                                    # Success - password was updated via REST API
                                    with status_container:
                                        st.success("✅ **Status**: Password updated successfully via REST API!")
                                    
                                    st.session_state.password_reset_completed = True
                                    st.success("✅ **Password updated successfully!**")
                                    st.info("🔄 **Redirecting to main page...** You can now log in with your new password.")
                                    st.markdown(f'[Click here to go to the main page](/) or wait 5 seconds to be redirected automatically.')
                                    
                                    logout_user()
                                    if "reset_token" in st.session_state:
                                        del st.session_state.reset_token
                                    
                                    st.markdown("""
                                    <script>
                                    setTimeout(function() {
                                        window.location.href = window.location.origin;
                                    }, 5000);
                                    </script>
                                    """, unsafe_allow_html=True)
                                    
                                    st.rerun()
                                else:
                                    with status_container:
                                        st.error("❌ **Status**: API returned 200 but response data is invalid")
                                    st.error("❌ **Error**: Password update response was invalid. Please try again or request a new reset link.")
                                    
                                    if is_admin():
                                        with st.expander("🔍 Debug Information"):
                                            st.write("**Response Status**: 200 OK")
                                            st.write("**Response Data**:")
                                            st.json(response_data)
                                            st.write("**Expected Fields**: id, user, or email")
                                    
                                    return
                            else:
                                # API returned an error
                                with status_container:
                                    st.error(f"❌ **Status**: Supabase API returned error (HTTP {response.status_code})")
                                
                                try:
                                    error_data = response.json() if response.text else {}
                                    error_msg = error_data.get("msg") or error_data.get("message") or error_data.get("error_description") or f"HTTP {response.status_code}"
                                    
                                    # Provide helpful error messages
                                    if response.status_code == 401:
                                        st.error("❌ **Error**: Reset link expired or invalid. Please request a new password reset link.")
                                    elif response.status_code == 400:
                                        st.error(f"❌ **Error**: {error_msg}")
                                    else:
                                        st.error(f"❌ **Error**: Failed to update password. {error_msg}")
                                    
                                    # Show full error for debugging (admin only)
                                    if is_admin():
                                        with st.expander("🔍 Error Details"):
                                            st.write(f"**HTTP Status**: {response.status_code}")
                                            st.write("**Error Response**:")
                                            st.json(error_data)
                                            st.write("**Request Headers**:")
                                            st.json({
                                                "apikey": f"{supabase_key[:10]}...",
                                                "Authorization": "Bearer [token]",
                                                "Content-Type": "application/json"
                                            })
                                            st.write("**User Email**:", user_email)
                                        
                                except Exception as parse_error:
                                    st.error(f"❌ **Error**: Failed to update password (HTTP {response.status_code}). Could not parse error response.")
                                    if is_admin():
                                        with st.expander("🔍 Debug Information"):
                                            st.write(f"**HTTP Status**: {response.status_code}")
                                            st.write(f"**Response Text**: {response.text[:500]}")
                                            st.exception(parse_error)
                                
                                return
                                
                    except requests.exceptions.Timeout:
                        st.error("❌ **Error**: Request timed out. Please check your connection and try again.")
                        if is_admin():
                            with st.expander("🔍 Debug Information"):
                                st.write("**Error Type**: Network Timeout")
                                st.write("**Timeout**: 10 seconds")
                    except requests.exceptions.RequestException as e:
                        st.error(f"❌ **Error**: Network error - {str(e)}. Please try again.")
                        if is_admin():
                            with st.expander("🔍 Debug Information"):
                                st.write("**Error Type**: Network Request Exception")
                                st.exception(e)
                    except Exception as e:
                        error_msg = str(e)
                        st.error(f"❌ **Error**: Unexpected error updating password: {error_msg}. Please try again or request a new reset link.")
                        if is_admin():
                            with st.expander("🔍 Error Details"):
                                st.write("**Error Type**: Unexpected Exception")
                            st.exception(e)
                            st.write("**User Email**:", user_email)
                            st.write("**Supabase URL**:", supabase_url)
            else:
                st.error("Please fill in both password fields")


def main():
    """Main dashboard function"""
    
    # Handle magic link token from query params (set by JavaScript hash processor above)
    import base64
    import json
    import time
    
    # ===== SESSION PERSISTENCE VIA COOKIES =====
    # Cookie is set in auth_callback.html (regular HTML page, not iframe)
    # Cookie is read here using st.context.cookies (server-side, Streamlit 1.37+)
    
    # Try to restore session from cookie if not already authenticated
    if not is_authenticated():
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # st.context.cookies is available in Streamlit 1.37+
            # It's a read-only dict of cookies sent in the initial HTTP request
            cookies = st.context.cookies
            auth_token = cookies.get("auth_token")
            
            if auth_token:
                # Validate token
                token_parts = auth_token.split('.')
                if len(token_parts) >= 2:
                    payload = token_parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    user_data = json.loads(decoded)
                    exp = user_data.get("exp", 0)
                    user_id_from_token = user_data.get("sub")
                    user_email_from_token = user_data.get("email")
                    
                    if exp > int(time.time()):
                        # Token valid, restore session (skip redirect since we're restoring from cookie)
                        logger.info(f"Restoring session from cookie for user_id: {user_id_from_token}, email: {user_email_from_token}")
                        set_user_session(auth_token, skip_cookie_redirect=True)
                        
                        # Verify user_id was set correctly
                        restored_user_id = get_user_id()
                        if restored_user_id == user_id_from_token:
                            logger.debug(f"Session restored successfully, user_id verified: {restored_user_id}")
                        else:
                            logger.warning(f"Session restoration mismatch: expected {user_id_from_token}, got {restored_user_id}")
                        # No rerun needed - we're already in the right state
                    else:
                        logger.debug(f"Cookie token expired (exp: {exp}, now: {int(time.time())})")
                    # If expired, we could clear the cookie but since st.context.cookies is read-only,
                    # we'd need JavaScript for that. For now, just don't restore expired tokens.
                else:
                    logger.debug("Cookie token has invalid format (not enough parts)")
            else:
                logger.debug("No auth_token cookie found")
        except AttributeError:
            # st.context.cookies not available (older Streamlit version)
            logger.warning("Session persistence requires Streamlit 1.37+. Please update.")
            st.warning("⚠️ Session persistence requires Streamlit 1.37+. Please update.")
        except Exception as e:
            # Other errors - log but don't block
            logger.warning(f"Cookie restoration error: {e}", exc_info=True)
    
    # Check for authentication errors in query params
    query_params = st.query_params
    if "auth_error" in query_params:
        error_code = query_params.get("error_code", "")
        error_desc = query_params.get("error_desc", "")
        
        # Show user-friendly error message
        if error_code == "otp_expired":
            st.error("❌ **Magic link expired** - The login link has expired. Please request a new magic link.")
        elif error_code:
            st.error(f"❌ **Authentication Error** - {error_desc or error_code}")
        else:
            st.error(f"❌ **Authentication Error** - {error_desc or 'An error occurred during authentication'}")
        
        # Clear error params
        st.query_params.clear()
    
    # Check for password reset token first - show dedicated page
    query_params = st.query_params
    if "magic_token" in query_params:
        access_token = query_params["magic_token"]
        auth_type = query_params.get("auth_type", "magiclink")
        
        # Handle password reset - show dedicated page
        if auth_type == "recovery":
            show_password_reset_page(access_token)
            return
    
    # Check for magic link login (not password reset)
    query_params = st.query_params
    if "magic_token" in query_params and not is_authenticated():
        access_token = query_params["magic_token"]
        auth_type = query_params.get("auth_type", "magiclink")
        
        # Handle magic link login (password reset handled above)
        try:
            # Decode JWT payload (middle part)
            token_parts = access_token.split('.')
            if len(token_parts) >= 2:
                # Decode base64url (JWT uses base64url)
                payload = token_parts[1]
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload)
                user_data = json.loads(decoded)
                
                # Create user dict from token
                user = {
                    "id": user_data.get("sub"),
                    "email": user_data.get("email")
                }
                
                # Set session
                set_user_session(access_token, user)
                
                # Clear query params
                st.query_params.clear()
                
                st.success("Magic link login successful!")
                st.rerun()
        except Exception as e:
            st.error(f"Error processing magic link: {e}")
            st.query_params.clear()
    
    # NOW: Check authentication (after restoration attempts)
    
    if not is_authenticated():
        show_login_page()
        return
    
    # Header with user info and logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown('<div class="main-header">📈 Portfolio Performance Dashboard</div>', unsafe_allow_html=True)
    with col2:
        user_email = get_user_email()
        if user_email:
            st.write(f"Logged in as: **{user_email}**")
        if st.button("Logout"):
            logout_user()
            st.rerun()
    
    # Sidebar - Navigation and Filters
    st.sidebar.title("Navigation")
    
    # Show admin status
    admin_status = is_admin()
    user_email = get_user_email()
    if user_email:
        if admin_status:
            st.sidebar.success("✅ Admin Access")
        else:
            # Check if user profile exists and show role
            try:
                client = get_supabase_client()
                if client:
                    profile_result = client.supabase.table("user_profiles").select("role").eq("user_id", get_user_id()).execute()
                    if profile_result.data:
                        role = profile_result.data[0].get('role', 'user')
                        if role != 'admin':
                            st.sidebar.info(f"👤 Role: {role}")
                            with st.sidebar.expander("🔧 Need Admin Access?"):
                                st.write("To become an admin, run this command on the server:")
                                st.code("python web_dashboard/setup_admin.py", language="bash")
                                st.write(f"Then enter your email: `{user_email}`")
            except Exception:
                pass  # Silently fail if we can't check
    
    # Admin link (only visible to admins)
    # Note: Streamlit automatically shows pages in sidebar, but we conditionally show a custom link
    if admin_status:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### Admin")
        # Use a button to navigate to admin page (more reliable than page_link)
        if st.sidebar.button("⚙️ Admin Dashboard", use_container_width=True, type="secondary"):
            st.switch_page("pages/admin.py")
        st.sidebar.markdown("---")
    
    # Debug section (visible to all authenticated users, requires ?debug=admin query param)
    query_params = st.query_params
    if query_params.get("debug") == "admin":
        st.sidebar.markdown("---")
        with st.sidebar.expander("🔍 Debug Info", expanded=True):
            user_id = get_user_id()
            user_email = get_user_email()
            admin_status = is_admin()
            
            st.write("**Session State:**")
            st.write(f"- User ID: `{user_id}`" if user_id else "- User ID: *Not set*")
            st.write(f"- User Email: `{user_email}`" if user_email else "- User Email: *Not set*")
            st.write(f"- Admin Status: `{admin_status}`")
            st.write(f"- Authenticated: `{is_authenticated()}`")
            
            # Try to get more details about admin check
            if user_id:
                try:
                    client = get_supabase_client()
                    if client:
                        st.write("**Supabase Client:** ✅ Initialized")
                        # Try the RPC call to see what happens
                        try:
                            result = client.supabase.rpc('is_admin', {'user_uuid': user_id}).execute()
                            st.write(f"**RPC Result Type:** `{type(result.data).__name__}`")
                            st.write(f"**RPC Result Value:** `{result.data}`")
                        except Exception as rpc_error:
                            st.write(f"**RPC Error:** `{str(rpc_error)}`")
                        
                        # Check user profile directly
                        try:
                            profile_result = client.supabase.table("user_profiles").select("role, email").eq("user_id", user_id).execute()
                            if profile_result.data:
                                profile = profile_result.data[0]
                                st.write(f"**User Profile Role:** `{profile.get('role', 'N/A')}`")
                                st.write(f"**User Profile Email:** `{profile.get('email', 'N/A')}`")
                                
                                if profile.get('role') != 'admin':
                                    st.warning("⚠️ Your role in the database is not 'admin'")
                                    st.info("💡 To become an admin, run: `python web_dashboard/setup_admin.py`")
                            else:
                                st.warning("⚠️ No user profile found in database")
                        except Exception as profile_error:
                            st.write(f"**Profile Check Error:** `{str(profile_error)}`")
                    else:
                        st.write("**Supabase Client:** ❌ Failed to initialize")
                except Exception as e:
                    st.write(f"**Error:** `{str(e)}`")
            else:
                st.write("**Note:** Cannot check admin status - user_id not set")
        st.sidebar.markdown("---")
    
    st.sidebar.title("Filters")
    
    # Get available funds (no "All Funds" option - default to first fund user has access to)
    try:
        funds = get_available_funds()
        if not funds:
            st.sidebar.warning("⚠️ No funds found in database")
            st.stop()
    except Exception as e:
        st.sidebar.error(f"❌ Error loading funds: {e}")
        st.stop()
    
    selected_fund = st.sidebar.selectbox(
        "Select Fund",
        funds,
        index=0  # Default to first available fund
    )
    
    # Use selected fund directly (no "All Funds" conversion needed)
    fund_filter = selected_fund
    
    # Display fund name
    st.sidebar.info(f"Viewing: **{fund_filter}**")
    
    # Main content
    try:
        # Load data
        with st.spinner("Loading portfolio data..."):
            positions_df = get_current_positions(fund_filter)
            trades_df = get_trade_log(limit=1000, fund=fund_filter)
            cash_balances = get_cash_balances(fund_filter)
            portfolio_value_df = calculate_portfolio_value_over_time(fund_filter)
        
        # Metrics row
        st.markdown("### Performance Metrics")
        
        # Check investor count to determine layout (hide if only 1 investor)
        num_investors = get_investor_count(fund_filter)
        show_investors = num_investors > 1
        
        # Calculate total portfolio value from current positions (with currency conversion)
        portfolio_value_no_cash = 0.0  # Portfolio value without cash (for investment metrics)
        total_value = 0.0
        total_pnl = 0.0
        usd_to_cad_rate = 1.0  # Default fallback
        
        # Get latest USD/CAD exchange rate from database
        if not positions_df.empty:
            client = get_supabase_client()
            if client:
                try:
                    rate_result = client.get_latest_exchange_rate('USD', 'CAD')
                    if rate_result:
                        usd_to_cad_rate = float(rate_result)
                except Exception as e:
                    print(f"Error getting exchange rate: {e}")
                    usd_to_cad_rate = 1.42  # Approximate fallback
        
        if not positions_df.empty and 'market_value' in positions_df.columns:
            # Convert USD positions to CAD before summing
            for _, row in positions_df.iterrows():
                market_value = float(row.get('market_value', 0) or 0)
                currency = str(row.get('currency', 'CAD')).upper() if pd.notna(row.get('currency')) else 'CAD'
                if currency == 'USD':
                    portfolio_value_no_cash += market_value * usd_to_cad_rate
                else:
                    portfolio_value_no_cash += market_value
        
        # Get Total P&L from positions_df (unrealized_pnl from latest_positions view)
        if not positions_df.empty and 'unrealized_pnl' in positions_df.columns:
            # Sum unrealized_pnl with currency conversion
            # Use pd.isna() to properly handle NaN values (NaN or 0 doesn't work because NaN is truthy)
            for _, row in positions_df.iterrows():
                pnl_val = row.get('unrealized_pnl', 0)
                pnl = 0.0 if pd.isna(pnl_val) else float(pnl_val)
                currency = str(row.get('currency', 'CAD')).upper() if pd.notna(row.get('currency')) else 'CAD'
                if currency == 'USD':
                    total_pnl += pnl * usd_to_cad_rate
                else:
                    total_pnl += pnl
        
        # Add cash to total value (USD cash converted to CAD)
        total_value = portfolio_value_no_cash + cash_balances.get('CAD', 0.0) + (cash_balances.get('USD', 0.0) * usd_to_cad_rate)
        
        # Get user's investment metrics (if they have contributions)
        user_investment = get_user_investment_metrics(fund_filter, portfolio_value_no_cash, include_cash=True)
        
        # Determine column layout based on whether we show investors and user investment
        num_cols = 4  # Base: Total Value, Total P&L, Holdings, Last Day P&L
        if show_investors:
            num_cols += 1  # Add Investors column
        if user_investment:
            num_cols += 1  # Add Your Investment column
        
        # Create columns dynamically
        cols = st.columns(num_cols)
        col_idx = 0
        
        
        # Calculate Last Trading Day P&L (used in multiple places)
        last_day_pnl = 0.0
        last_day_pnl_pct = 0.0
        if not positions_df.empty and 'daily_pnl' in positions_df.columns:
            # Convert USD daily P&L to CAD before summing
            # Use pd.isna() to properly handle NaN values (NaN or 0 doesn't work because NaN is truthy)
            for _, row in positions_df.iterrows():
                daily_pnl_val = row.get('daily_pnl', 0)
                daily_pnl = 0.0 if pd.isna(daily_pnl_val) else float(daily_pnl_val)
                currency = str(row.get('currency', 'CAD')).upper() if pd.notna(row.get('currency')) else 'CAD'
                if currency == 'USD':
                    last_day_pnl += daily_pnl * usd_to_cad_rate
                else:
                    last_day_pnl += daily_pnl
            
            # Calculate percentage based on yesterday's value (total_value - today's change)
            yesterday_value = total_value - last_day_pnl
            if yesterday_value > 0:
                last_day_pnl_pct = (last_day_pnl / yesterday_value) * 100
        
        # Display metrics in order: Your Investment (if available), Total Value, Total P&L, Holdings, Investors (if > 1), Last Day P&L
        
        # Your Investment (if user has contributions)
        if user_investment:
            with cols[col_idx]:
                st.metric(
                    "Your Investment (CAD)",
                    f"${user_investment['current_value']:,.2f}",
                    f"{user_investment['gain_loss_pct']:+.2f}%"
                )
            col_idx += 1
        
        # Total Portfolio Value
        with cols[col_idx]:
            st.metric("Total Portfolio Value (CAD)", f"${total_value:,.2f}")
        col_idx += 1
        
        # Total P&L
        with cols[col_idx]:
            pnl_pct = (total_pnl / (total_value - total_pnl) * 100) if (total_value - total_pnl) > 0 else 0.0
            st.metric("Total P&L (CAD)", f"${total_pnl:,.2f}", f"{pnl_pct:.2f}%")
        col_idx += 1
        
        # Holdings
        with cols[col_idx]:
            num_holdings = len(positions_df) if not positions_df.empty else 0
            st.metric("Holdings", f"{num_holdings}")
        col_idx += 1
        
        # Investors (only show if > 1)
        if show_investors:
            with cols[col_idx]:
                st.metric("Investors", f"{num_investors}")
            col_idx += 1
        
        # Last Trading Day P&L
        with cols[col_idx]:
            st.metric("Last Trading Day P&L (CAD)", f"${last_day_pnl:,.2f}", 
                     f"{last_day_pnl_pct:+.2f}%" if last_day_pnl_pct != 0 else "0.00%")
        
        # Charts section
        st.markdown("---")
        st.markdown("### Performance Charts")
        
        # Portfolio value over time
        if not portfolio_value_df.empty:
            st.markdown("#### Portfolio Performance (Baseline 100)")
            
            # Add solid lines toggle for mobile users
            use_solid = st.checkbox("📱 Solid Lines Only (for mobile)", value=False, help="Use solid lines instead of dashed for better mobile readability")
            
            # Use normalized performance index (baseline 100) like the console app
            fig = create_portfolio_value_chart(
                portfolio_value_df, 
                fund_filter,
                show_normalized=True,  # Show percentage change from baseline
                show_benchmarks=['sp500', 'qqq', 'russell2000', 'vti'],  # All benchmarks
                show_weekend_shading=True,
                use_solid_lines=use_solid
            )
            st.plotly_chart(fig, use_container_width=True, key="portfolio_performance_chart")
            
            # Debug info for diagnosing data issues (admin only)
            if is_admin():
                with st.expander("🔍 Debug: Portfolio Data Info"):
                    st.write("**System Status:** v1.1 (Limit Fix Applied) ✅")
                    st.write(f"**Days processed:** {len(portfolio_value_df)}")
                    
                    if 'date' in portfolio_value_df.columns:
                        min_date = portfolio_value_df['date'].min()
                        max_date = portfolio_value_df['date'].max()
                        st.write(f"**Date range:** {min_date.date()} to {max_date.date()}")
                    
                    st.write("**Last 5 days data:**")
                    st.dataframe(portfolio_value_df.tail(5))
            
            # Individual holdings performance chart (lazy loading)
            st.markdown("---")
            show_holdings = st.checkbox("📊 Show Individual Stock Performance", value=False)
            
            if show_holdings:
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    date_range = st.radio(
                        "Date Range:",
                        options=["Last 7 Days", "Last 30 Days", "All Time"],
                        horizontal=True,
                        index=0  # Default to 7 days
                    )
                
                # Map selection to days parameter
                days_map = {
                    "Last 7 Days": 7,
                    "Last 30 Days": 30,
                    "All Time": 0  # 0 = all time
                }
                days = days_map[date_range]
                
                with st.spinner(f"Loading {date_range.lower()} of stock data..."):
                    from streamlit_utils import get_individual_holdings_performance
                    holdings_df = get_individual_holdings_performance(fund_filter, days=days)
                
                if not holdings_df.empty:
                    from chart_utils import create_individual_holdings_chart
                    holdings_fig = create_individual_holdings_chart(
                        holdings_df,
                        fund_name=fund_filter,
                        show_benchmarks=['sp500', 'qqq', 'russell2000', 'vti'],
                        show_weekend_shading=True,
                        use_solid_lines=use_solid  # Use same setting as main chart
                    )  
                    st.plotly_chart(holdings_fig, use_container_width=True, key="individual_holdings_chart")
                    
                    # Show summary stats
                    num_stocks = holdings_df['ticker'].nunique()
                    st.caption(f"Showing {num_stocks} individual stocks over {date_range.lower()}")
                else:
                    st.info(f"No holdings data available for {date_range.lower()}")
        
        else:
            st.info("No historical portfolio value data available")
        
        
        # Current positions
        st.markdown("---")
        st.markdown("### Current Positions")
        
        if not positions_df.empty:
            # P&L chart
            if 'pnl' in positions_df.columns or 'unrealized_pnl' in positions_df.columns:
                st.markdown("#### P&L by Position")
                fig = create_pnl_chart(positions_df, fund_filter)
                st.plotly_chart(fig, use_container_width=True, key="pnl_by_position_chart")
            
            # Currency exposure chart
            if 'currency' in positions_df.columns and 'market_value' in positions_df.columns:
                st.markdown("#### Currency Exposure")
                fig = create_currency_exposure_chart(positions_df, fund_filter)
                st.plotly_chart(fig, use_container_width=True, key="currency_exposure_chart")
            
            # Sector allocation chart
            if 'ticker' in positions_df.columns and 'market_value' in positions_df.columns:
                st.markdown("#### Sector Allocation")
                fig = create_sector_allocation_chart(positions_df, fund_filter)
                st.plotly_chart(fig, use_container_width=True, key="sector_allocation_chart")
            
            # Investor allocation chart (with privacy controls)
            # Only show if there are multiple investors
            if num_investors > 1:
                st.markdown("#### Investor Allocation")
                user_email = get_user_email()
                admin_status = is_admin()
                investors_df = get_investor_allocations(fund_filter, user_email, admin_status)
                
                if not investors_df.empty:
                    fig = create_investor_allocation_chart(investors_df, fund_filter)
                    st.plotly_chart(fig, use_container_width=True, key="investor_allocation_chart")
                else:
                    st.info("No investor data available for this fund")
            
            # Positions table with compact/full mode toggle
            st.markdown("#### Positions Table")
            compact_mode = st.checkbox("📱 Compact View (fewer columns)", value=False, help="Show fewer columns for mobile/narrow screens")
            
            # Define column sets
            if compact_mode:
                # Mobile-friendly: essential columns only
                display_cols = ['ticker', 'shares', 'current_price', 'market_value', 'return_pct']
                col_names = {'ticker': 'Ticker', 'shares': 'Shares', 'current_price': 'Price', 
                           'market_value': 'Value', 'return_pct': 'Return %'}
            else:
                # Full desktop view - removed company name (now in Holdings Info table below)
                display_cols = ['ticker', 'shares', 'current_price', 'cost_basis', 
                              'market_value', 'unrealized_pnl', 'return_pct', 'daily_pnl', 
                              'daily_pnl_pct', 'five_day_pnl_pct']
                col_names = {'ticker': 'Ticker', 'shares': 'Shares',
                           'current_price': 'Price', 'cost_basis': 'Cost Basis',
                           'market_value': 'Value', 'unrealized_pnl': 'P&L ($)',
                           'return_pct': 'Return %', 'daily_pnl': '1-Day ($)',
                           'daily_pnl_pct': '1-Day %', 'five_day_pnl_pct': '5-Day %'}
            
            # Filter to only columns that exist
            display_cols = [col for col in display_cols if col in positions_df.columns]
            
            if display_cols:
                display_df = positions_df[display_cols].copy()
                
                # Rename columns for display
                display_df = display_df.rename(columns={c: col_names.get(c, c) for c in display_cols})
                
                # Format numeric columns
                format_dict = {}
                for col in display_df.columns:
                    if col == 'Shares':
                        format_dict[col] = '{:.4f}'
                    elif col in ['Price', 'Cost Basis', 'Value', 'P&L ($)', '1-Day ($)']:
                        format_dict[col] = '${:,.2f}'
                    elif col in ['Return %', '1-Day %', '5-Day %']:
                        format_dict[col] = '{:+.2f}%'
                
                # Apply color styling to P&L columns
                def color_pnl(val):
                    """Color positive values green, negative red"""
                    try:
                        if isinstance(val, str):
                            val = float(val.replace('$', '').replace('%', '').replace(',', '').replace('+', ''))
                        if val > 0:
                            return 'color: #10b981'  # Green
                        elif val < 0:
                            return 'color: #ef4444'  # Red
                    except:
                        pass
                    return ''
                
                # Style the dataframe
                pnl_cols = [c for c in display_df.columns if any(x in c for x in ['P&L', 'Return', '1-Day', '5-Day'])]
                styled_df = display_df.style.format(format_dict)
                
                for col in pnl_cols:
                    if col in display_df.columns:
                        styled_df = styled_df.map(color_pnl, subset=[col])
                
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    height=400
                )
            else:
                st.dataframe(positions_df, use_container_width=True, height=400)
            
            # Holdings Info table - Company, Sector, Industry
            # Data is already available from latest_positions view (joins with securities table)
            st.markdown("#### Holdings Info")
            if not positions_df.empty:
                # Extract company, sector, industry from positions_df (already loaded from database)
                holdings_info_cols = ['ticker']
                col_rename = {'ticker': 'Ticker'}
                
                if 'company' in positions_df.columns:
                    holdings_info_cols.append('company')
                    col_rename['company'] = 'Company'
                if 'sector' in positions_df.columns:
                    holdings_info_cols.append('sector')
                    col_rename['sector'] = 'Sector'
                if 'industry' in positions_df.columns:
                    holdings_info_cols.append('industry')
                    col_rename['industry'] = 'Industry'
                
                # Filter to only existing columns
                holdings_info_cols = [col for col in holdings_info_cols if col in positions_df.columns]
                
                if holdings_info_cols:
                    holdings_info_df = positions_df[holdings_info_cols].copy()
                    holdings_info_df = holdings_info_df.rename(columns=col_rename)
                    # Remove duplicates (in case same ticker appears multiple times)
                    holdings_info_df = holdings_info_df.drop_duplicates(subset=['Ticker'])
                    # Fill NaN values with 'N/A' for display
                    holdings_info_df = holdings_info_df.fillna('N/A')
                    st.dataframe(holdings_info_df, use_container_width=True, height=300)
                else:
                    st.info("Company, sector, and industry data not available")
        else:
            st.info("No current positions found")
        
        # Recent trades
        st.markdown("---")
        st.markdown("### Recent Trades")
        
        if not trades_df.empty:
            # Limit to last 50 trades for display
            recent_trades = trades_df.head(50).copy()
            
            # company_name comes from get_trade_log() which joins with securities table
            # Rename to 'company' for display column consistency
            # Fall back to positions lookup for any remaining None values
            if 'company_name' in recent_trades.columns:
                recent_trades['company'] = recent_trades['company_name']
            else:
                recent_trades['company'] = None
            
            # Fill missing company names from positions data (if available)
            if not positions_df.empty and 'company' in positions_df.columns and 'ticker' in recent_trades.columns:
                # Create a lookup dictionary from positions_df: ticker -> company
                ticker_to_company = positions_df.set_index('ticker')['company'].to_dict()
                
                # Fill None values in recent_trades['company'] using the lookup
                mask = recent_trades['company'].isna() | (recent_trades['company'] == '')
                recent_trades.loc[mask, 'company'] = recent_trades.loc[mask, 'ticker'].map(ticker_to_company)
            
            # Determine action type (BUY/SELL) - check multiple possible column names
            action_col = None
            for col_name in ['type', 'action', 'trade_type']:
                if col_name in recent_trades.columns:
                    action_col = col_name
                    break
            
            # If no action column, infer from reason field (checking for "sell" keywords)
            if action_col:
                recent_trades['Action'] = recent_trades[action_col].str.upper()
            else:
                # Infer from reason field - check for sell keywords
                if 'reason' in recent_trades.columns:
                    def infer_action(reason):
                        if pd.isna(reason) or reason is None:
                            return 'BUY'  # Default if no reason
                        reason_lower = str(reason).lower()
                        if 'sell' in reason_lower or 'limit sell' in reason_lower or 'market sell' in reason_lower:
                            return 'SELL'
                        return 'BUY'  # Default to BUY if no sell keywords found
                    recent_trades['Action'] = recent_trades['reason'].apply(infer_action)
                else:
                    # No action or reason column - default to BUY
                    recent_trades['Action'] = 'BUY'
            
            # Build display columns
            display_cols = ['date', 'ticker']
            col_rename = {'date': 'Date', 'ticker': 'Ticker'}
            
            if 'company' in recent_trades.columns:
                display_cols.append('company')
                col_rename['company'] = 'Company'
            
            display_cols.extend(['Action', 'shares', 'price'])
            col_rename.update({'Action': 'Action', 'shares': 'Shares', 'price': 'Price'})
            
            # Add P&L if available
            if 'pnl' in recent_trades.columns:
                display_cols.append('pnl')
                col_rename['pnl'] = 'Realized P&L'
            
            # Add reason if available
            if 'reason' in recent_trades.columns:
                display_cols.append('reason')
                col_rename['reason'] = 'Reason'
            
            # Filter to existing columns
            display_cols = [col for col in display_cols if col in recent_trades.columns]
            
            if display_cols:
                display_df = recent_trades[display_cols].copy()
                display_df = display_df.rename(columns=col_rename)
                
                # Format columns
                format_dict = {}
                if 'Shares' in display_df.columns:
                    format_dict['Shares'] = '{:.4f}'
                if 'Price' in display_df.columns:
                    format_dict['Price'] = '${:.2f}'
                if 'Realized P&L' in display_df.columns:
                    format_dict['Realized P&L'] = '${:,.2f}'
                
                # Apply styling
                styled_df = display_df.style.format(format_dict)
                
                # Color-code P&L
                if 'Realized P&L' in display_df.columns:
                    def color_trade_pnl(val):
                        try:
                            if isinstance(val, str):
                                val = float(val.replace('$', '').replace(',', ''))
                            if val > 0:
                                return 'color: #10b981'
                            elif val < 0:
                                return 'color: #ef4444'
                        except:
                            pass
                        return ''
                    styled_df = styled_df.map(color_trade_pnl, subset=['Realized P&L'])
                
                st.dataframe(styled_df, use_container_width=True, height=400)
            else:
                st.dataframe(recent_trades, use_container_width=True, height=400)
        else:
            st.info("No recent trades found")
        
        # Footer with build info
        st.markdown("---")
        # Get build timestamp from environment variable (set by CI) or use current time
        build_timestamp = os.getenv("BUILD_TIMESTAMP")
        if not build_timestamp:
            # Fallback: generate timestamp in Pacific Time
            try:
                from zoneinfo import ZoneInfo
                pacific = ZoneInfo("America/Vancouver")
                now = datetime.now(pacific)
                build_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
            except (ImportError, Exception):
                # If zoneinfo not available (Python < 3.9) or other error, use simple format
                build_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        st.markdown(
            f"""
            <div style='text-align: center; color: #666; font-size: 0.8em;'>
                LLM Micro-Cap Trading Bot Dashboard • Build: {build_timestamp}
            </div>
            """, 
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()

