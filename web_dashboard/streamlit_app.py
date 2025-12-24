#!/usr/bin/env python3
"""
Streamlit Portfolio Performance Dashboard
Displays historical performance graphs and current portfolio data
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import sys
from pathlib import Path
import base64
import json
import time
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Initialize scheduler once per Streamlit worker process (lazy initialization)
# Don't initialize at module load - only when needed after authentication
_scheduler_initialized = False

def _init_scheduler():
    """Initialize background scheduler once per Streamlit worker."""
    global _scheduler_initialized
    if _scheduler_initialized:
        return True
    
    try:
        from scheduler import start_scheduler
        started = start_scheduler()
        if started:
            pass  # Scheduler started successfully
        _scheduler_initialized = True
        return True
    except Exception as e:
        # Fail gracefully - scheduler is optional
        print(f"⚠️ Scheduler initialization failed (non-critical): {e}")
        _scheduler_initialized = True  # Mark as initialized to prevent retry loops
        return False



from streamlit_utils import (
    get_available_funds,
    get_current_positions,
    get_trade_log,
    get_cash_balances,
    calculate_portfolio_value_over_time,
    get_supabase_client,
    get_investor_count,
    get_investor_allocations,
    get_user_investment_metrics,
    get_fund_thesis_data,
    get_realized_pnl,
    get_user_display_currency,
    convert_to_display_currency,
    fetch_latest_rates_bulk,
    display_dataframe_with_copy
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
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
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
    .timestamp-display {
        font-size: 0.9rem;
        margin-top: -0.8rem;
        margin-bottom: 0.5rem;
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
                                set_user_session(
                                    result["access_token"], 
                                    result["user"],
                                    refresh_token=result.get("refresh_token"),
                                    expires_at=result.get("expires_at")
                                )
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
                                set_user_session(
                                    result["access_token"], 
                                    result.get("user"),
                                    refresh_token=result.get("refresh_token"),
                                    expires_at=result.get("expires_at")
                                )
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


def create_timestamp_display_component(timestamp_iso: str, is_market_open: bool, is_today: bool):
    """
    Create a JavaScript component to display timestamp in user's browser timezone.
    
    Args:
        timestamp_iso: ISO format timestamp string (UTC)
        is_market_open: Whether market is currently open
        is_today: Whether timestamp is from today
    """
    import streamlit.components.v1 as components
    
    js_code = f"""
    <div id="timestamp-container" style="font-size: 0.9rem; margin-top: -0.8rem; margin-bottom: 0.5rem; padding-top: 2px; line-height: 1.4; overflow: visible;"></div>
    <script>
    (function() {{
        function formatTimestamp() {{
            // Parse the timestamp
            const timestamp = new Date('{timestamp_iso}');
            const isMarketOpen = {str(is_market_open).lower()};
            const isToday = {str(is_today).lower()};
            
            // Get user's timezone
            const userTZ = Intl.DateTimeFormat().resolvedOptions().timeZone;
            
            // Calculate market close hour in user's timezone
            // Market closes at 4:00 PM EST (16:00 EST)
            // Create a date at 4pm EST on the timestamp date, then convert to user's timezone
            const timestampDate = new Date(timestamp);
            const year = timestampDate.getUTCFullYear();
            const month = timestampDate.getUTCMonth();
            const day = timestampDate.getUTCDate();
            
            // Determine if DST is in effect for EST/EDT
            // DST: 2nd Sunday of March to 1st Sunday of November
            function isDST(date) {{
                const m = date.getUTCMonth();
                if (m >= 3 && m <= 9) return true; // Apr-Oct = EDT
                if (m < 2 || m > 10) return false; // Jan-Feb, Nov-Dec = EST
                // March: check if after 2nd Sunday
                if (m === 2) {{
                    const d = date.getUTCDate();
                    const dow = date.getUTCDay();
                    // Find 2nd Sunday: first find 1st Sunday, then add 7 days
                    const firstSunday = 1 + (7 - dow) % 7;
                    const secondSunday = firstSunday + 7;
                    return d >= secondSunday;
                }}
                // November: check if before 1st Sunday
                if (m === 10) {{
                    const d = date.getUTCDate();
                    const dow = date.getUTCDay();
                    const firstSunday = 1 + (7 - dow) % 7;
                    return d < firstSunday;
                }}
                return false;
            }}
            
            // Market closes at 4pm EST = 20:00 UTC (EDT) or 21:00 UTC (EST)
            const marketCloseHourUTC = isDST(timestampDate) ? 20 : 21;
            
            // Create market close time in UTC
            const marketCloseUTC = new Date(Date.UTC(year, month, day, marketCloseHourUTC, 0, 0));
            
            // Determine if we should show minutes
            const showMinutes = isMarketOpen && isToday;
            
            // If market is closed or not today, use market close time instead of actual timestamp
            let displayTime = timestamp;
            if (!isMarketOpen || !isToday) {{
                // Use the market close time (already calculated in UTC)
                displayTime = marketCloseUTC;
            }}
            
            // Format the timestamp in user's timezone
            const options = {{
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                hour12: true,
                timeZone: userTZ
            }};
            
            if (showMinutes) {{
                options.minute = '2-digit';
            }}
            
            const formatted = new Intl.DateTimeFormat('en-US', options).format(displayTime);
            
            // Display the timestamp
            const container = document.getElementById('timestamp-container');
            if (container) {{
                container.textContent = 'Market data last updated: ' + formatted;
                // Detect if we're in dark mode by checking the iframe's background
                const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
                // Or check if body/container has dark background
                const bodyBg = window.getComputedStyle(document.body).backgroundColor;
                const isDarkBg = bodyBg && (bodyBg.includes('rgb(14, 17, 23)') || bodyBg.includes('rgb(38, 39, 48)') || bodyBg === 'rgb(0, 0, 0)');
                
                if (isDark || isDarkBg) {{
                    container.style.color = 'rgba(255, 255, 255, 0.8)';
                }} else {{
                    container.style.color = 'rgba(0, 0, 0, 0.8)';
                }}
            }}
        }}
        
        // Try to format immediately
        formatTimestamp();
        
        // Also try when DOM is ready (in case script runs before DOM)
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', formatTimestamp);
        }}
    }})();
    </script>
    """
    
    components.html(js_code, height=35)


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


def format_currency_label(currency_code: str) -> str:
    """Format currency code for display in labels.
    
    Args:
        currency_code: Currency code (e.g., 'CAD', 'USD')
        
    Returns:
        Formatted label like "(CAD)" or "(USD)"
    """
    return f"({currency_code})"


def main():
    """Main dashboard function"""
    
    # Generate or retrieve session ID for log tracking
    if 'session_id' not in st.session_state:
        import uuid
        st.session_state.session_id = str(uuid.uuid4())[:8]  # Short 8-char ID
    
    session_id = st.session_state.session_id
    
    # Initialize file-based logging
    try:
        from log_handler import setup_logging, log_message
        setup_logging()
        import time
        start_time = time.time()
        log_message(f"[{session_id}] PERF: Streamlit script run started", level='DEBUG')
    except Exception as e:
        print(f"Warning: Could not initialize logging: {e}")
    
    # Handle magic link token from query params (set by JavaScript hash processor above)
    import base64
    import json
    import time
    
    # ===== TOKEN REFRESH =====
    # Check if token needs to be refreshed (before authentication checks)
    # This ensures users stay logged in when active
    if is_authenticated():
        from auth_utils import refresh_token_if_needed
        try:
            refreshed = refresh_token_if_needed()
            if not refreshed:
                # Refresh failed - token is invalid, clear session
                # User will need to log in again
                if "user_token" in st.session_state:
                    del st.session_state.user_token
                if "refresh_token" in st.session_state:
                    del st.session_state.refresh_token
                if "token_expires_at" in st.session_state:
                    del st.session_state.token_expires_at
        except Exception as e:
            # If refresh check fails, continue anyway (token might still be valid)
            pass
    
    # ===== COOKIE UPDATE STRATEGY =====
    # We don't update the cookie automatically during active use to avoid disruptive redirects.
    # Instead:
    # 1. During active use: Session state is maintained, so cookie staleness doesn't matter
    # 2. On page reload: Cookie is checked and restored (see below)
    # 3. When restoring from cookie: We update it with the current valid token (no redirect needed)
    # 
    # This means the cookie might be slightly stale during active use, but that's fine since
    # we rely on session state. The cookie is only needed for restoration after page reload.
    
    # Clear the update flag - we'll handle cookie updates when restoring from cookie instead
    if "_cookie_needs_update" in st.session_state:
        # Token was refreshed, but we'll update cookie on next page load/restore
        # This avoids disruptive redirects during active use
        del st.session_state._cookie_needs_update
    
    # ===== SESSION PERSISTENCE VIA COOKIES =====
    # Cookie is set in auth_callback.html (regular HTML page, not iframe)
    # Cookie is read here using st.context.cookies (server-side, Streamlit 1.37+)
    
    # Try to restore session from cookie if not already authenticated
    if not is_authenticated():
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
                    
                    current_time = int(time.time())
                    time_until_expiry = exp - current_time
                    
                    if exp > current_time:
                        # Token valid, restore session (skip redirect since we're restoring from cookie)
                        # Note: refresh_token is not stored in cookie for security, so refresh won't work
                        # after page reload, but token refresh will work during active sessions
                        set_user_session(auth_token, skip_cookie_redirect=True, expires_at=exp)
                        
                        # Update cookie proactively on page load to keep it fresh
                        # Refresh if cookie has <= 30 minutes left (keeps it fresh)
                        # This ensures cookie stays valid and prevents logout on next page load
                        # Redirects only happen on page load, not during active use
                        if time_until_expiry <= 1800:  # 30 minutes
                            # Cookie token is getting stale, refresh it proactively
                            from auth_utils import refresh_token_if_needed
                            try:
                                if refresh_token_if_needed():
                                    # Token was refreshed, update cookie with new token
                                    # This happens on page load, so redirect is acceptable
                                    new_token = st.session_state.get("user_token")
                                    if new_token and new_token != auth_token:
                                        # New token is different, update cookie
                                        import urllib.parse
                                        encoded_token = urllib.parse.quote(new_token, safe='')
                                        redirect_url = f'/set_cookie.html?token={encoded_token}'
                                        st.markdown(
                                            f'<meta http-equiv="refresh" content="0; url={redirect_url}">',
                                            unsafe_allow_html=True
                                        )
                                        st.write("Refreshing session...")
                                        st.stop()
                            except Exception:
                                # If refresh fails, continue with restored session
                                pass
                        
                        # Verify user_id was set correctly
                        restored_user_id = get_user_id()
                        if restored_user_id != user_id_from_token:
                            # Session restoration mismatch - silently continue
                            pass
                        # No rerun needed - we're already in the right state
                    # If expired, we could clear the cookie but since st.context.cookies is read-only,
                    # we'd need JavaScript for that. For now, just don't restore expired tokens.
        except (AttributeError, Exception):
            # Cookie restoration failed - silently continue
            pass
    
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
    
    # Initialize scheduler only after authentication (lazy initialization)
    # This prevents blocking the login page
    try:
        _init_scheduler()
    except Exception:
        pass  # Scheduler is optional
    
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
    
    # Custom page navigation links (replaces default Streamlit page names)
    st.sidebar.markdown("### Pages")
    st.sidebar.page_link("streamlit_app.py", label="📈 Dashboard")
    
    # Show admin status
    admin_status = is_admin()
    user_email = get_user_email()
    if user_email:
        if admin_status:
            st.sidebar.success("✅ Admin Access")
            # Admin page link (only visible to admins)
            st.sidebar.page_link("pages/admin.py", label="Admin", icon="⚙️")
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
    
    # Simple time range selector (for performance when data grows)
    time_range = st.sidebar.radio(
        "Time Range",
        options=["All Time", "Last 3 Months"],
        index=0,  # Default to All Time
        help="Filter performance charts by time period. Use 'Last 3 Months' for faster loading with large datasets."
    )
    
    # Convert time range to days parameter
    days_filter = None if time_range == "All Time" else 90  # ~3 months
    
    # Use selected fund directly (no "All Funds" conversion needed)
    fund_filter = selected_fund
    
    # Display fund name
    st.sidebar.info(f"Viewing: **{fund_filter}**")
    
    # Get timestamp first (quick query) to display immediately
    latest_timestamp = None
    is_market_open = False
    is_today = False
    
    try:
        # Quick query to get latest timestamp
        from log_handler import log_message
        positions_df_quick = get_current_positions(fund_filter)
        if not positions_df_quick.empty and 'date' in positions_df_quick.columns:
            try:
                max_date = positions_df_quick['date'].max()
                if isinstance(max_date, str):
                    from dateutil import parser
                    latest_timestamp = parser.parse(max_date)
                elif hasattr(max_date, 'to_pydatetime'):
                    latest_timestamp = max_date.to_pydatetime()
                elif isinstance(max_date, pd.Timestamp):
                    latest_timestamp = max_date.to_pydatetime()
                else:
                    latest_timestamp = max_date
                
                if latest_timestamp.tzinfo is None:
                    latest_timestamp = latest_timestamp.replace(tzinfo=timezone.utc)
                
                # Check market status
                try:
                    from market_data.market_hours import MarketHours
                    market_hours = MarketHours()
                    is_market_open = market_hours.is_market_open()
                except Exception:
                    pass
                
                # Check if today
                today_utc = datetime.now(timezone.utc).date()
                if latest_timestamp.tzinfo is not None:
                    timestamp_utc = latest_timestamp.astimezone(timezone.utc)
                else:
                    timestamp_utc = latest_timestamp.replace(tzinfo=timezone.utc)
                timestamp_date = timestamp_utc.date()
                is_today = timestamp_date == today_utc
            except Exception:
                pass
    except Exception:
        pass
    
    # Display timestamp right after header
    if latest_timestamp:
        try:
            timestamp_iso = latest_timestamp.isoformat()
            create_timestamp_display_component(timestamp_iso, is_market_open, is_today)
        except Exception:
            pass
    
    # Main content
    try:
        # Load data
        from log_handler import log_message
        import time
        
        log_message(f"[{session_id}] PERF: Starting dashboard data load for fund: {fund_filter}", level='INFO')
        data_load_start = time.time()
        
        # Get user's display currency preference (needed for all calculations)
        display_currency = get_user_display_currency()
        
        with st.spinner("Loading portfolio data..."):
            t0 = time.time()
            positions_df = get_current_positions(fund_filter)
            log_message(f"[{session_id}] PERF: get_current_positions took {time.time() - t0:.2f}s", level='INFO')
            
            t0 = time.time()
            trades_df = get_trade_log(limit=1000, fund=fund_filter)
            log_message(f"[{session_id}] PERF: get_trade_log took {time.time() - t0:.2f}s", level='INFO')
            
            t0 = time.time()
            cash_balances = get_cash_balances(fund_filter)
            log_message(f"[{session_id}] PERF: get_cash_balances took {time.time() - t0:.2f}s", level='INFO')
            
            t0 = time.time()
            portfolio_value_df = calculate_portfolio_value_over_time(fund_filter, days=days_filter, display_currency=display_currency)
            log_message(f"[{session_id}] PERF: calculate_portfolio_value_over_time took {time.time() - t0:.2f}s", level='INFO')
        
        log_message(f"[{session_id}] PERF: Total data load took {time.time() - data_load_start:.2f}s", level='INFO')
        
        # Metrics row
        st.markdown("### Performance Metrics")
        
        metrics_start = time.time()
        log_message(f"[{session_id}] PERF: Starting metrics calculations", level='INFO')
        
        with st.spinner("Calculating metrics..."):
            # Check investor count to determine layout (hide if only 1 investor)
            t0 = time.time()
            num_investors = get_investor_count(fund_filter)
            log_message(f"[{session_id}] PERF: get_investor_count took {time.time() - t0:.2f}s", level='INFO')
            show_investors = num_investors > 1
            
            # Calculate total portfolio value from current positions (with currency conversion to display currency)
            portfolio_value_no_cash = 0.0  # Portfolio value without cash (for investment metrics)
            total_value = 0.0
            total_pnl = 0.0
        
        t0 = time.time()
        
        # BULK FETCH OPTIMIZATION: Get all required exchange rates in one go
        # Collect currencies from positions and cash
        all_currencies = set()
        if not positions_df.empty:
            all_currencies.update(positions_df['currency'].fillna('CAD').astype(str).str.upper().unique().tolist())
        all_currencies.update([str(c).upper() for c in cash_balances.keys()])
        
        # Fetch dictionary of rates: {'USD': 1.35, 'CAD': 1.0}
        rate_map = fetch_latest_rates_bulk(list(all_currencies), display_currency)
        
        # Helper to get rate safely (default 1.0)
        def get_rate_safe(curr):
            return rate_map.get(str(curr).upper(), 1.0)
            
        # 1. Calculate Portfolio Value (Vectorized)
        if not positions_df.empty and 'market_value' in positions_df.columns:
            # Create temporary rate column for vector operation
            # Use map for fast lookup
            rates = positions_df['currency'].fillna('CAD').astype(str).str.upper().map(get_rate_safe)
            portfolio_value_no_cash = (positions_df['market_value'].fillna(0) * rates).sum()
        log_message(f"[{session_id}] PERF: market_value calculation (vectorized) took {time.time() - t0:.2f}s", level='INFO')

        # 2. Calculate Total P&L (Vectorized)
        t0 = time.time()
        if not positions_df.empty and 'unrealized_pnl' in positions_df.columns:
            rates = positions_df['currency'].fillna('CAD').astype(str).str.upper().map(get_rate_safe)
            total_pnl = (positions_df['unrealized_pnl'].fillna(0) * rates).sum()
        log_message(f"[{session_id}] PERF: unrealized_pnl calculation (vectorized) took {time.time() - t0:.2f}s", level='INFO')
        
        # 3. Calculate Cash (Fast Loop with Lookup)
        t0 = time.time()
        total_cash_display = 0.0
        for currency, amount in cash_balances.items():
            if amount > 0:
                total_cash_display += amount * get_rate_safe(currency)
        total_value = portfolio_value_no_cash + total_cash_display
        log_message(f"[{session_id}] PERF: cash calculation (lookup) took {time.time() - t0:.2f}s", level='INFO')
        
        # Get user's investment metrics (if they have contributions)
        t0 = time.time()
        user_investment = get_user_investment_metrics(fund_filter, portfolio_value_no_cash, include_cash=True, session_id=session_id, display_currency=display_currency)
        log_message(f"[{session_id}] PERF: get_user_investment_metrics took {time.time() - t0:.2f}s", level='INFO')
        
        # 4. Calculate Last Trading Day P&L (Vectorized)
        t0 = time.time()
        last_day_pnl = 0.0
        last_day_pnl_pct = 0.0
        if not positions_df.empty and 'daily_pnl' in positions_df.columns:
            rates = positions_df['currency'].fillna('CAD').astype(str).str.upper().map(get_rate_safe)
            last_day_pnl = (positions_df['daily_pnl'].fillna(0) * rates).sum()
            
            # Calculate percentage based on yesterday's value (total_value - today's change)
            yesterday_value = total_value - last_day_pnl
            if yesterday_value > 0:
                last_day_pnl_pct = (last_day_pnl / yesterday_value) * 100
        log_message(f"[{session_id}] PERF: daily_pnl calculation (vectorized) took {time.time() - t0:.2f}s", level='INFO')

        # Calculate "Unrealized P&L" (sum of open positions pnl)
        # We already calculated total_pnl above which is exactly this
        unrealized_pnl = total_pnl
        unrealized_pnl_pct = (unrealized_pnl / (portfolio_value_no_cash - unrealized_pnl) * 100) if (portfolio_value_no_cash - unrealized_pnl) > 0 else 0.0

        # Num holdings for display
        num_holdings = len(positions_df) if not positions_df.empty else 0
        
        # Calculate total fund return (matching graph - stock performance only, not including cash drag)
        # This shows the same metric as the graph for consistency
        # Fund return = unrealized P&L / cost basis (same as graph calculation)
        if portfolio_value_no_cash > 0:
            cost_basis = portfolio_value_no_cash - unrealized_pnl
            fund_return_pct = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0.0
            fund_return_dollars = unrealized_pnl
        else:
            fund_return_pct = 0.0
            fund_return_dollars = 0.0


        # --- DYNAMIC LAYOUT LOGIC ---
        
        # Check if we should use Multi-Investor layout or Single Investor layout
        is_multi_investor = show_investors # Calculated earlier as num_investors > 1

        if is_multi_investor:
            # === MULTI-INVESTOR LAYOUT ===
            # Separates "Your Performance" from "Fund Performance"
            
            st.markdown("#### 👤 Your Investment")
            col1, col2, col3, col4 = st.columns(4)
            
            if user_investment:
                # Calculate User's Day Change based on ownership
                user_ownership_ratio = user_investment['ownership_pct'] / 100.0
                user_day_pnl = last_day_pnl * user_ownership_ratio
                
                with col1:
                    st.metric(
                        f"Your Value {format_currency_label(display_currency)}",
                        f"${user_investment['current_value']:,.2f}",
                        help="Current market value of your specific share in the fund."
                    )
                with col2:
                    st.metric(
                        "Your Day Change",
                        f"${user_day_pnl:,.2f}",
                        f"{last_day_pnl_pct:+.2f}%", 
                        help="Estimated change in your investment value since last market close."
                    )
                with col3:
                    st.metric(
                        "Your Return",
                        f"${user_investment['gain_loss']:,.2f}",
                        f"{user_investment['gain_loss_pct']:+.2f}%",
                        help="Total return on your investment (Current Value - Net Contribution)."
                    )
                with col4:
                    st.metric(
                        "Ownership",
                        f"{user_investment['ownership_pct']:.2f}%",
                        help="Your percentage ownership of the total fund assets."
                    )
            else:
                st.info("No contribution data found for your account in this fund.")

            st.markdown("#### 🏦 Fund Overview")
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            
            with f_col1:
                st.metric(
                    f"Fund Total Value {format_currency_label(display_currency)}", 
                    f"${total_value:,.2f}",
                    help="Total value of all assets in the fund (Cash + Positions) for ALL investors."
                )
            with f_col2:
                st.metric(
                    "Fund Return",
                    f"${fund_return_dollars:,.2f}", 
                    f"{fund_return_pct:+.2f}%",
                    help="Total return on all investments in the fund since inception."
                )
            with f_col3:
                st.metric("Investors", f"{num_investors}", help="Total number of distinct investors in this fund.")
            with f_col4:
                st.metric("Holdings", f"{num_holdings}", help="Number of open stock positions.")

        else:
            # === SINGLE INVESTOR LAYOUT ===
            # Consolidated view since User == Fund
            
            # We want 4 main metrics: Value, Total Return (All time), Day P&L, Unrealized P&L
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            
            with m_col1:
                st.metric(
                    f"Portfolio Value {format_currency_label(display_currency)}", 
                    f"${total_value:,.2f}",
                    help="Total current value of your portfolio (Cash + Positions)."
                )
            
            with m_col2:
                # Total Return - Prioritize user_investment calc as it accounts for realized gains
                if user_investment:
                    st.metric(
                        "Total Return",
                        f"{user_investment['gain_loss_pct']:+.2f}%",
                        f"${user_investment['gain_loss']:,.2f}",
                        help="All-time return on investment (Current Value - Net Contribution)."
                    )
                else:
                    # Fallback to unrealized if no contribution data
                    st.metric(
                        "Unrealized Return",
                        f"{unrealized_pnl_pct:+.2f}%",
                        help="Return based on currently held positions only (excludes realized gains/losses)."
                    )

            with m_col3:
                st.metric(
                    f"Day Change {format_currency_label(display_currency)}", 
                    f"${last_day_pnl:,.2f}", 
                    f"{last_day_pnl_pct:+.2f}%",
                    help="Change in portfolio value since the last market close."
                )
                
            with m_col4:
                 st.metric(
                    f"Open P&L {format_currency_label(display_currency)}", 
                    f"${unrealized_pnl:,.2f}",
                    help="Unrealized Profit/Loss from currently held positions."
                )
        
        # Close P&L section (realized gains/losses from closed positions)
        st.markdown("---")
        st.markdown("### Closed Positions P&L")
        
        # Calculate realized P&L
        realized_pnl_data = get_realized_pnl(fund=fund_filter, display_currency=display_currency)
        total_realized = realized_pnl_data.get('total_realized_pnl', 0.0)
        num_closed = realized_pnl_data.get('num_closed_trades', 0)
        winning_trades = realized_pnl_data.get('winning_trades', 0)
        losing_trades = realized_pnl_data.get('losing_trades', 0)
        trades_by_ticker = realized_pnl_data.get('trades_by_ticker', {})
        
        # Debug: Show what we found (only in debug mode)
        if st.checkbox("🔍 Debug: Show trade log info", key="debug_realized_pnl"):
            trades_df = get_trade_log(limit=100, fund=fund_filter)
            if not trades_df.empty:
                st.write(f"**Total trades found:** {len(trades_df)}")
                st.write(f"**Columns:** {list(trades_df.columns)}")
                if 'action' in trades_df.columns:
                    st.write(f"**Unique action values:** {trades_df['action'].astype(str).unique().tolist()}")
                    st.write(f"**SELL trades count:** {len(trades_df[trades_df['action'].astype(str).str.upper() == 'SELL'])}")
                if 'reason' in trades_df.columns:
                    sell_in_reason = trades_df['reason'].astype(str).str.upper().str.contains('SELL', na=False)
                    st.write(f"**Trades with 'SELL' in reason:** {sell_in_reason.sum()}")
                display_dataframe_with_copy(trades_df.head(20), label="Debug Trades", key_suffix="debug")
        
        if num_closed > 0:
            # Display primary metrics (matching console app structure)
            pnl_col1, pnl_col2, pnl_col3, pnl_col4 = st.columns(4)
            
            with pnl_col1:
                st.metric(
                    f"Total Realized P&L {format_currency_label(display_currency)}",
                    f"${total_realized:,.2f}",
                    help="Total realized profit/loss from all closed positions (matches console app)."
                )
            
            with pnl_col2:
                total_shares_sold = realized_pnl_data.get('total_shares_sold', 0.0)
                st.metric(
                    "Total Shares Sold",
                    f"{total_shares_sold:,.2f}",
                    help="Total number of shares sold across all closed positions."
                )
            
            with pnl_col3:
                total_proceeds = realized_pnl_data.get('total_proceeds', 0.0)
                st.metric(
                    f"Total Proceeds {format_currency_label(display_currency)}",
                    f"${total_proceeds:,.2f}",
                    help=f"Total proceeds from all sales in {display_currency}."
                )
            
            with pnl_col4:
                avg_sell_price = realized_pnl_data.get('average_sell_price', 0.0)
                st.metric(
                    f"Avg Sell Price {format_currency_label(display_currency)}",
                    f"${avg_sell_price:,.2f}",
                    help=f"Average sell price per share across all closed positions in {display_currency}."
                )
            
            # Secondary metrics row
            pnl_col5, pnl_col6, pnl_col7, pnl_col8 = st.columns(4)
            
            with pnl_col5:
                st.metric(
                    "Closed Trades",
                    f"{num_closed}",
                    help="Total number of closed positions (sell transactions)."
                )
            
            with pnl_col6:
                st.metric(
                    "Winning Trades",
                    f"{winning_trades}",
                    help="Number of closed positions with positive realized P&L."
                )
            
            with pnl_col7:
                st.metric(
                    "Losing Trades",
                    f"{losing_trades}",
                    help="Number of closed positions with negative realized P&L."
                )
            
            with pnl_col8:
                win_rate = (winning_trades / num_closed * 100) if num_closed > 0 else 0.0
                st.metric(
                    "Win Rate",
                    f"{win_rate:.1f}%",
                    help="Percentage of closed trades with positive P&L."
                )
            
            # Show breakdown by ticker if there are multiple tickers
            if len(trades_by_ticker) > 1:
                st.markdown("#### Realized P&L by Ticker")
                
                # Create DataFrame for display (handle new structure)
                currency_label = format_currency_label(display_currency)
                ticker_data = []
                for ticker, data in trades_by_ticker.items():
                    if isinstance(data, dict):
                        # New structure with detailed breakdown
                        ticker_data.append({
                            'Ticker': ticker,
                            f'Realized P&L {currency_label}': data.get('realized_pnl', 0.0),
                            'Shares Sold': data.get('shares_sold', 0.0),
                            f'Proceeds {currency_label}': data.get('proceeds', 0.0)
                        })
                    else:
                        # Legacy structure (just a number)
                        ticker_data.append({
                            'Ticker': ticker,
                            f'Realized P&L {currency_label}': float(data),
                            'Shares Sold': 0.0,
                            f'Proceeds {currency_label}': 0.0
                        })
                
                ticker_pnl_df = pd.DataFrame(ticker_data)
                pnl_col_name = f'Realized P&L {currency_label}'
                ticker_pnl_df = ticker_pnl_df.sort_values(pnl_col_name, ascending=False)
                
                # Format and color-code
                def color_pnl(val):
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
                
                format_dict = {
                    pnl_col_name: '${:,.2f}',
                    'Shares Sold': '{:,.2f}',
                    f'Proceeds {currency_label}': '${:,.2f}'
                }
                styled_pnl_df = ticker_pnl_df.style.format(format_dict).map(color_pnl, subset=[pnl_col_name])
                
                display_dataframe_with_copy(styled_pnl_df, label="Realized P&L", key_suffix="ticker_pnl", use_container_width=True, height=300)
        else:
            st.info("No closed positions found. Realized P&L will appear here once you close positions.")

        # Investment Thesis section (near top, after metrics)
        if fund_filter:
            thesis_data = get_fund_thesis_data(fund_filter)
            if thesis_data:
                st.markdown("---")
                with st.expander("📋 Investment Thesis", expanded=True):
                    st.markdown(f"### {thesis_data.get('title', 'Investment Thesis')}")
                    st.markdown(thesis_data.get('overview', ''))
                    # Note: Pillars will be shown near sectors chart below

        # Charts section
        st.markdown("---")
        st.markdown("### Performance Charts")
        
        log_message(f"[{session_id}] PERF: Metrics calculations complete, took {time.time() - metrics_start:.2f}s total", level='INFO')
        log_message(f"[{session_id}] PERF: Starting chart section", level='INFO')
        charts_start = time.time()
        
        # Portfolio value over time
        if not portfolio_value_df.empty:
            st.markdown("#### Portfolio Performance (Baseline 100)")
            
            # Chart controls (benchmark selector removed - all benchmarks now available in legend)
            use_solid = st.checkbox("📱 Solid Lines Only (for mobile)", value=False, help="Use solid lines instead of dashed for better mobile readability")
            
            # All benchmarks are now passed to the chart (S&P 500 visible, others in legend)
            all_benchmarks = ['sp500', 'qqq', 'russell2000', 'vti']
            
            # Use normalized performance index (baseline 100) like the console app
            log_message(f"[{session_id}] PERF: Creating portfolio value chart", level='INFO')
            t0 = time.time()
            fig = create_portfolio_value_chart(
                portfolio_value_df, 
                fund_filter,
                show_normalized=True,  # Show percentage change from baseline
                show_benchmarks=all_benchmarks,  # All benchmarks (S&P 500 visible, others in legend)
                show_weekend_shading=True,
                use_solid_lines=use_solid,
                display_currency=display_currency
            )
            log_message(f"[{session_id}] PERF: create_portfolio_value_chart took {time.time() - t0:.2f}s", level='INFO')
            
            t0 = time.time()
            st.plotly_chart(fig, use_container_width=True, key="portfolio_performance_chart")
            log_message(f"[{session_id}] PERF: st.plotly_chart (render) took {time.time() - t0:.2f}s", level='INFO')
            
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
                    # Stock filter dropdown
                    # Dynamically build sector/industry options from data (gracefully handle nulls)
                    sectors = sorted([s for s in holdings_df.get('sector', pd.Series()).dropna().unique() if s])
                    industries = sorted([i for i in holdings_df.get('industry', pd.Series()).dropna().unique() if i])
                    
                    filter_options = [
                        "All stocks",
                        "Winners (↑ total %)",
                        "Losers (↓ total %)",
                        "Daily winners (↑ 1-day %)",
                        "Daily losers (↓ 1-day %)",
                        "Top 5 performers",
                        "Bottom 5 performers",
                        "Canadian (CAD)",
                        "American (USD)",
                        "Stocks only",
                        "ETFs only"
                    ]
                    
                    # Add sector options if data exists
                    if sectors:
                        filter_options.append("--- By Sector ---")
                        filter_options.extend([f"Sector: {s}" for s in sectors])
                    
                    # Add industry options if data exists
                    if industries:
                        filter_options.append("--- By Industry ---")
                        filter_options.extend([f"Industry: {i}" for i in industries])
                    
                    stock_filter = st.selectbox(
                        "📈 Stock filter",
                        options=filter_options,
                        index=0,
                        help="Filter the stocks shown in the chart below"
                    )
                    
                    # Apply filter
                    filtered_df = holdings_df.copy()
                    
                    if stock_filter == "Winners (↑ total %)":
                        if 'return_pct' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['return_pct'].fillna(0) > 0]
                    elif stock_filter == "Losers (↓ total %)":
                        if 'return_pct' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['return_pct'].fillna(0) < 0]
                    elif stock_filter == "Daily winners (↑ 1-day %)":
                        if 'daily_pnl_pct' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['daily_pnl_pct'].fillna(0) > 0]
                    elif stock_filter == "Daily losers (↓ 1-day %)":
                        if 'daily_pnl_pct' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['daily_pnl_pct'].fillna(0) < 0]
                    elif stock_filter == "Top 5 performers":
                        if 'return_pct' in filtered_df.columns:
                            filtered_df = filtered_df.nlargest(5, 'return_pct')
                    elif stock_filter == "Bottom 5 performers":
                        if 'return_pct' in filtered_df.columns:
                            filtered_df = filtered_df.nsmallest(5, 'return_pct')
                    elif stock_filter == "Canadian (CAD)":
                        if 'currency' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['currency'] == 'CAD']
                    elif stock_filter == "American (USD)":
                        if 'currency' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['currency'] == 'USD']
                    elif stock_filter == "Stocks only":
                        if 'ticker' in filtered_df.columns:
                            filtered_df = filtered_df[~filtered_df['ticker'].str.contains('ETF', case=False, na=False)]
                    elif stock_filter == "ETFs only":
                        if 'ticker' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['ticker'].str.contains('ETF', case=False, na=False)]
                    elif stock_filter.startswith("Sector: "):
                        sector_name = stock_filter.replace("Sector: ", "")
                        if 'sector' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['sector'] == sector_name]
                    elif stock_filter.startswith("Industry: "):
                        industry_name = stock_filter.replace("Industry: ", "")
                        if 'industry' in filtered_df.columns:
                            filtered_df = filtered_df[filtered_df['industry'] == industry_name]
                    # Skip separator lines
                    elif stock_filter.startswith("---"):
                        pass  # No filter applied
                    
                    from chart_utils import create_individual_holdings_chart
                    holdings_fig = create_individual_holdings_chart(
                        filtered_df,
                        fund_name=fund_filter,
                        show_benchmarks=all_benchmarks,  # Use same benchmarks as main chart
                        show_weekend_shading=True,
                        use_solid_lines=use_solid
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
                fig = create_pnl_chart(positions_df, fund_filter, display_currency=display_currency)
                st.plotly_chart(fig, use_container_width=True, key="pnl_by_position_chart")
            
            # Currency exposure chart
            if 'currency' in positions_df.columns and 'market_value' in positions_df.columns:
                st.markdown("#### Currency Exposure")
                fig = create_currency_exposure_chart(positions_df, fund_filter)
                st.plotly_chart(fig, use_container_width=True, key="currency_exposure_chart")
            
            # Investment Thesis Pillars (near sectors chart)
            if fund_filter:
                thesis_data = get_fund_thesis_data(fund_filter)
                if thesis_data and thesis_data.get('pillars'):
                    st.markdown("#### Investment Thesis Pillars")
                    pillars = thesis_data['pillars']
                    
                    # Display pillars in columns (2-3 columns depending on number of pillars)
                    num_pillars = len(pillars)
                    if num_pillars <= 2:
                        cols = st.columns(num_pillars)
                    elif num_pillars == 3:
                        cols = st.columns(3)
                    else:
                        cols = st.columns(3)  # Max 3 columns, will wrap
                    
                    for i, pillar in enumerate(pillars):
                        col_idx = i % len(cols)
                        with cols[col_idx]:
                            with st.container():
                                st.markdown(f"**{pillar.get('name', 'Pillar')}** ({pillar.get('allocation', 'N/A')})")
                                st.markdown(pillar.get('thesis', ''))
                                st.markdown("---")
            
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
                    # Create two columns: chart on left, table on right
                    col1, col2 = st.columns([1.2, 0.8])
                    
                    with col1:
                        fig = create_investor_allocation_chart(investors_df, fund_filter)
                        st.plotly_chart(fig, use_container_width=True, key="investor_allocation_chart")
                    
                    with col2:
                        st.markdown("**Investment Amounts**")
                        # Validate required columns exist
                        required_cols = ['contributor_display', 'net_contribution', 'ownership_pct']
                        if not all(col in investors_df.columns for col in required_cols):
                            st.error("Missing required columns in investor data")
                        else:
                            # Format the table with dollar amounts and percentages
                            # Note: get_investor_allocations already sorts by net_contribution, but we ensure it here
                            display_df = investors_df[required_cols].copy()
                            display_df = display_df.sort_values('net_contribution', ascending=False)
                            
                            # Handle NaN/None values in formatting
                            def format_currency(val):
                                """Format currency with NaN handling"""
                                if pd.isna(val) or val is None:
                                    return "$0.00"
                                try:
                                    return f"${float(val):,.2f}"
                                except (ValueError, TypeError):
                                    return "$0.00"
                            
                            def format_percentage(val):
                                """Format percentage with NaN handling"""
                                if pd.isna(val) or val is None:
                                    return "0.00%"
                                try:
                                    return f"{float(val):.2f}%"
                                except (ValueError, TypeError):
                                    return "0.00%"
                            
                            display_df['Investment'] = display_df['net_contribution'].apply(format_currency)
                            display_df['Percentage'] = display_df['ownership_pct'].apply(format_percentage)
                            table_df = display_df[['contributor_display', 'Investment', 'Percentage']].copy()
                            table_df.columns = ['Investor', 'Investment', 'Ownership %']
                            
                            # Display as a styled table
                            display_dataframe_with_copy(
                                table_df,
                                label="Investor Allocation",
                                key_suffix="investor_allocation",
                                use_container_width=True,
                                hide_index=True,
                                height=min(400, 50 + len(table_df) * 35)  # Dynamic height based on rows
                            )
                            
                            # Show total at bottom (handle NaN case)
                            total = investors_df['net_contribution'].sum()
                            if pd.isna(total):
                                total = 0.0
                            st.markdown(f"**Total:** ${total:,.2f}")
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
                
                # Convert currency-denominated columns to display currency
                # The rate_map was already calculated earlier in the function (around line 1156)
                # We need to apply currency conversion to values that are in position's native currency
                if not positions_df.empty and 'currency' in positions_df.columns:
                    # Recalculate rate_map if needed (or reuse from earlier - it's in scope)
                    # Get unique currencies from positions
                    unique_currencies = positions_df['currency'].fillna('CAD').astype(str).str.upper().unique().tolist()
                    display_rate_map = fetch_latest_rates_bulk(unique_currencies, display_currency)
                    
                    def get_display_rate(curr):
                        return display_rate_map.get(str(curr).upper(), 1.0)
                    
                    # Apply currency conversion to currency-denominated columns
                    currency_cols = ['cost_basis', 'market_value', 'unrealized_pnl', 'daily_pnl', 'current_price']
                    for col in currency_cols:
                        if col in display_df.columns:
                            # Get currency for each row and apply conversion rate
                            # Match by index to ensure we get the right currency for each position
                            rates = positions_df.loc[display_df.index, 'currency'].fillna('CAD').astype(str).str.upper().map(get_display_rate)
                            display_df[col] = pd.to_numeric(display_df[col], errors='coerce').fillna(0) * rates
                    
                    # Debug: Log positions with zero P&L after currency conversion
                    if 'unrealized_pnl' in display_df.columns:
                        zero_pnl_mask = display_df['unrealized_pnl'].abs() < 0.01
                        zero_pnl_positions = display_df[zero_pnl_mask]
                        if len(zero_pnl_positions) > 0:
                            log_message(f"[{session_id}] WARNING: Found {len(zero_pnl_positions)} positions with zero P&L after currency conversion: {list(zero_pnl_positions.get('Ticker', zero_pnl_positions.index))}", level='WARNING')
                            # Check if cost_basis equals market_value (which would cause zero P&L)
                            if 'Cost Basis' in display_df.columns and 'Value' in display_df.columns:
                                cost_value_match = (display_df['Cost Basis'] - display_df['Value']).abs() < 0.01
                                matching = display_df[cost_value_match & zero_pnl_mask]
                                if len(matching) > 0:
                                    log_message(f"[{session_id}] WARNING: {len(matching)} positions have cost_basis = market_value: {list(matching.get('Ticker', matching.index))}", level='WARNING')
                
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
                
                display_dataframe_with_copy(
                    styled_df,
                    label="Current Positions",
                    key_suffix="positions_styled",
                    use_container_width=True,
                    height=400
                )
            else:
                display_dataframe_with_copy(positions_df, label="Current Positions", key_suffix="positions_raw", use_container_width=True, height=400)
            
            # Holdings Info table - Company, Sector, Industry
            # Data is already available from latest_positions view (joins with securities table)
            st.markdown("#### Holdings Info")
            if not positions_df.empty:
                # Debug: Log available columns (only in development)
                import logging
                logger = logging.getLogger(__name__)
                if os.environ.get('STREAMLIT_ENV') != 'production':
                    logger.debug(f"Available columns in positions_df: {list(positions_df.columns)}")
                
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
                    display_dataframe_with_copy(holdings_info_df, label="Holdings Info", key_suffix="holdings_info", use_container_width=True, height=300)
                else:
                    st.warning("⚠️ Company, sector, and industry data not available. The database view may need to be updated. See database/fixes/DF_017_restore_securities_to_latest_positions.sql")
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
                
                display_dataframe_with_copy(styled_df, label="Recent Trades", key_suffix="recent_trades_styled", use_container_width=True, height=400)
            else:
                display_dataframe_with_copy(recent_trades, label="Recent Trades", key_suffix="recent_trades_raw", use_container_width=True, height=400)
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



    # Log total execution time
    try:
        duration = time.time() - start_time
        log_message(f"PERF: Streamlit script run finished in {duration:.3f}s", level='INFO' if duration > 1.0 else 'DEBUG')
    except Exception:
        pass

if __name__ == "__main__":
    main()

