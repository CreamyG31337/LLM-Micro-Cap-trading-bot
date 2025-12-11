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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamlit_utils import (
    get_available_funds,
    get_current_positions,
    get_trade_log,
    get_cash_balances,
    calculate_portfolio_value_over_time
)
from chart_utils import (
    create_portfolio_value_chart,
    create_performance_by_fund_chart,
    create_pnl_chart,
    create_trades_timeline_chart
)
from auth_utils import (
    login_user,
    register_user,
    is_authenticated,
    logout_user,
    set_user_session,
    get_user_email,
    get_user_token
)

# Page configuration
st.set_page_config(
    page_title="Portfolio Performance Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
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
            email = st.text_input("Email", type="default")
            
            if not use_magic_link:
                password = st.text_input("Password", type="password")
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


def main():
    """Main dashboard function"""
    
    # Handle magic link token from query params (set by JavaScript hash processor above)
    import base64
    import json
    import time
    
    # Check localStorage for persisted session (before checking authentication)
    if not is_authenticated():
        st.markdown("""
        <script>
        (function() {
            const token = localStorage.getItem('auth_token');
            if (token && !window.location.search.includes('magic_token') && !window.location.search.includes('restore_token')) {
                // Redirect with token to restore session
                const url = new URL(window.location);
                url.searchParams.set('restore_token', token);
                window.location.replace(url.toString());
            }
        })();
        </script>
        """, unsafe_allow_html=True)
        
        # Handle restore_token from localStorage
        if "restore_token" in st.query_params:
            token = st.query_params["restore_token"]
            # Validate token (check expiration)
            try:
                token_parts = token.split('.')
                if len(token_parts) >= 2:
                    payload = token_parts[1]
                    payload += '=' * (4 - len(payload) % 4)
                    decoded = base64.urlsafe_b64decode(payload)
                    user_data = json.loads(decoded)
                    exp = user_data.get("exp", 0)
                    
                    if exp > int(time.time()):
                        # Token valid, restore session
                        set_user_session(token)
                        st.query_params.clear()
                        st.rerun()
                    else:
                        # Token expired, clear localStorage
                        st.markdown("""
                        <script>
                        localStorage.removeItem('auth_token');
                        </script>
                        """, unsafe_allow_html=True)
                        st.query_params.clear()
            except Exception:
                # Invalid token, clear
                st.query_params.clear()
    
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
    
    # Check for magic link or password reset token in query params
    query_params = st.query_params
    if "magic_token" in query_params and not is_authenticated():
        access_token = query_params["magic_token"]
        auth_type = query_params.get("auth_type", "magiclink")
        
        # Handle password reset
        if auth_type == "recovery":
            # Check if password reset already completed
            if st.session_state.get("password_reset_completed"):
                st.info("✅ Password reset already completed. Please log in with your new password.")
                st.query_params.clear()
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
                        st.query_params.clear()
                        return
                else:
                    st.error("❌ **Invalid reset token** - The reset link is invalid.")
                    st.query_params.clear()
                    return
            except Exception as e:
                st.error(f"❌ **Error processing reset token** - {e}")
                st.query_params.clear()
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
                    st.query_params.clear()
                    return
            
            # Show password reset form
            st.markdown("### Reset Your Password")
            st.info("Enter your new password below.")
            
            with st.form("new_password_form"):
                new_password = st.text_input("New Password", type="password", key="new_password")
                confirm_password = st.text_input("Confirm Password", type="password", key="confirm_new_password")
                submit = st.form_submit_button("Update Password")
                
                if submit:
                    if new_password and confirm_password:
                        if new_password != confirm_password:
                            st.error("Passwords do not match")
                        else:
                            # Update password using Supabase client with recovery token
                            try:
                                import os
                                from supabase import create_client
                                
                                supabase_url = os.getenv("SUPABASE_URL")
                                supabase_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
                                
                                if not supabase_url or not supabase_key:
                                    st.error("Error: Supabase configuration missing")
                                    return
                                
                                # Create Supabase client
                                supabase = create_client(supabase_url, supabase_key)
                                
                                # Verify the recovery token using verify_otp() with type "recovery"
                                # This is the correct way to authenticate with a recovery token in Supabase
                                # The access_token from the recovery link needs to be verified first
                                session_verified = False
                                verification_error = None
                                user_email_for_verification = None
                                
                                # Extract email from the access_token for verify_otp
                                try:
                                    token_parts = access_token.split('.')
                                    if len(token_parts) >= 2:
                                        payload = token_parts[1]
                                        payload += '=' * (4 - len(payload) % 4)
                                        decoded = base64.urlsafe_b64decode(payload)
                                        user_data = json.loads(decoded)
                                        user_email_for_verification = user_data.get("email")
                                except Exception as decode_error:
                                    st.error(f"Error: Failed to decode recovery token: {decode_error}. Please request a new reset link.")
                                    return
                                
                                if not user_email_for_verification:
                                    st.error("Error: Could not extract email from recovery token. Please request a new reset link.")
                                    return
                                
                                # Verify the recovery token using verify_otp
                                try:
                                    # verify_otp requires email, token, and type="recovery"
                                    # The access_token from the recovery link is the token to verify
                                    verification_response = supabase.auth.verify_otp({
                                        "email": user_email_for_verification,
                                        "token": access_token,
                                        "type": "recovery"
                                    })
                                    
                                    if verification_response and hasattr(verification_response, 'user') and verification_response.user:
                                        session_verified = True
                                    else:
                                        verification_error = "Verification response was invalid"
                                except Exception as e:
                                    # Verification failed, store error for proper error reporting
                                    verification_error = str(e)
                                
                                # Try to update password using Supabase client
                                user_response = None
                                update_success = False
                                
                                if session_verified:
                                    # Token verified successfully, use client method to update password
                                    try:
                                        user_response = supabase.auth.update_user({"password": new_password})
                                        if user_response and hasattr(user_response, 'user') and user_response.user:
                                            update_success = True
                                    except Exception as update_error:
                                        # Client method failed even with verified session
                                        error_details = str(update_error)
                                        st.error(f"Error: Failed to update password after token verification: {error_details}. Please try again or request a new reset link.")
                                        return
                                else:
                                    # Token verification failed, fall back to REST API with proper error handling
                                    import requests
                                    try:
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
                                        
                                        if response.status_code == 200:
                                            # REST API succeeded
                                            update_success = True
                                            # Create a mock response object for consistency
                                            class MockResponse:
                                                def __init__(self):
                                                    self.user = {"id": "updated"}  # Indicate success
                                            user_response = MockResponse()
                                        else:
                                            # REST API failed
                                            error_data = response.json() if response.text else {}
                                            error_msg = error_data.get("msg") or error_data.get("message") or f"HTTP {response.status_code}"
                                            st.error(f"Error: Failed to update password via API. Token verification failed: {verification_error}. API error: {error_msg}. Please request a new reset link.")
                                            return
                                    except Exception as api_error:
                                        # REST API call itself failed
                                        error_details = str(api_error)
                                        st.error(f"Error: Failed to update password. Token verification failed: {verification_error}. API call failed: {error_details}. Please request a new reset link.")
                                        return
                                
                                # Check if update was successful
                                if update_success and user_response and hasattr(user_response, 'user') and user_response.user:
                                    # Mark password reset as completed
                                    st.session_state.password_reset_completed = True
                                    st.success("✅ Password updated successfully! You can now log in with your new password.")
                                    
                                    # Clear session and query params
                                    logout_user()
                                    if "reset_token" in st.session_state:
                                        del st.session_state.reset_token
                                    
                                    # Clean URL and redirect after a short delay
                                    st.markdown("""
                                    <script>
                                    setTimeout(function() {
                                        window.history.replaceState({}, document.title, window.location.pathname);
                                        window.location.href = window.location.origin;
                                    }, 2000);
                                    </script>
                                    """, unsafe_allow_html=True)
                                    
                                    st.query_params.clear()
                                    st.rerun()
                                else:
                                    st.error("Error: Failed to update password. The response was invalid. Please try again or request a new reset link.")
                            except Exception as e:
                                error_msg = str(e)
                                st.error(f"Error updating password: {error_msg}. Please try again or request a new reset link.")
                    else:
                        st.error("Please fill in both password fields")
        else:
            # Handle magic link login
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
    
    # Check authentication
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
    
    # Sidebar - Fund selector
    st.sidebar.title("Filters")
    
    # Get available funds
    try:
        funds = get_available_funds()
        if not funds:
            st.sidebar.warning("No funds found in database")
            funds = ["All Funds"]
        else:
            funds = ["All Funds"] + funds
    except Exception as e:
        st.sidebar.error(f"Error loading funds: {e}")
        funds = ["All Funds"]
    
    selected_fund = st.sidebar.selectbox(
        "Select Fund",
        funds,
        index=0
    )
    
    # Convert "All Funds" to None
    fund_filter = None if selected_fund == "All Funds" else selected_fund
    
    # Display fund name
    if fund_filter:
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
        col1, col2, col3, col4 = st.columns(4)
        
        # Calculate total portfolio value
        total_value = 0.0
        total_pnl = 0.0
        if not positions_df.empty and 'market_value' in positions_df.columns:
            total_value = float(positions_df['market_value'].sum())
            total_pnl = float(positions_df['pnl'].sum()) if 'pnl' in positions_df.columns else 0.0
        
        # Add cash to total value
        total_value += cash_balances.get('CAD', 0.0) + cash_balances.get('USD', 0.0)
        
        with col1:
            st.metric("Total Portfolio Value", f"${total_value:,.2f}")
        
        with col2:
            pnl_pct = (total_pnl / (total_value - total_pnl) * 100) if (total_value - total_pnl) > 0 else 0.0
            st.metric("Total P&L", f"${total_pnl:,.2f}", f"{pnl_pct:.2f}%")
        
        with col3:
            st.metric("CAD Balance", f"${cash_balances.get('CAD', 0.0):,.2f}")
        
        with col4:
            st.metric("USD Balance", f"${cash_balances.get('USD', 0.0):,.2f}")
        
        # Charts section
        st.markdown("---")
        st.markdown("### Performance Charts")
        
        # Portfolio value over time
        if not portfolio_value_df.empty:
            st.markdown("#### Portfolio Value Over Time")
            fig = create_portfolio_value_chart(portfolio_value_df, fund_filter)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No historical portfolio value data available")
        
        # Trades timeline
        if not trades_df.empty:
            st.markdown("#### Trades Timeline")
            fig = create_trades_timeline_chart(trades_df, fund_filter)
            st.plotly_chart(fig, use_container_width=True)
        
        # Current positions
        st.markdown("---")
        st.markdown("### Current Positions")
        
        if not positions_df.empty:
            # P&L chart
            if 'pnl' in positions_df.columns:
                st.markdown("#### P&L by Position")
                fig = create_pnl_chart(positions_df, fund_filter)
                st.plotly_chart(fig, use_container_width=True)
            
            # Positions table
            st.markdown("#### Positions Table")
            # Select relevant columns for display
            display_cols = ['ticker', 'shares', 'price', 'cost_basis']
            if 'market_value' in positions_df.columns:
                display_cols.append('market_value')
            if 'pnl' in positions_df.columns:
                display_cols.append('pnl')
            if 'pnl_pct' in positions_df.columns:
                display_cols.append('pnl_pct')
            
            # Filter to only columns that exist
            display_cols = [col for col in display_cols if col in positions_df.columns]
            
            if display_cols:
                st.dataframe(
                    positions_df[display_cols].style.format({
                        'shares': '{:.4f}',
                        'price': '${:.2f}',
                        'cost_basis': '${:.2f}',
                        'market_value': '${:.2f}',
                        'pnl': '${:.2f}',
                        'pnl_pct': '{:.2f}%'
                    }),
                    use_container_width=True,
                    height=400
                )
            else:
                st.dataframe(positions_df, use_container_width=True, height=400)
        else:
            st.info("No current positions found")
        
        # Recent trades
        st.markdown("---")
        st.markdown("### Recent Trades")
        
        if not trades_df.empty:
            # Limit to last 50 trades for display
            recent_trades = trades_df.head(50)
            
            # Select relevant columns
            trade_cols = ['date', 'ticker', 'type', 'shares', 'price']
            if 'cost_basis' in recent_trades.columns:
                trade_cols.append('cost_basis')
            if 'pnl' in recent_trades.columns:
                trade_cols.append('pnl')
            
            trade_cols = [col for col in trade_cols if col in recent_trades.columns]
            
            if trade_cols:
                st.dataframe(
                    recent_trades[trade_cols].style.format({
                        'shares': '{:.4f}',
                        'price': '${:.2f}',
                        'cost_basis': '${:.2f}',
                        'pnl': '${:.2f}'
                    }),
                    use_container_width=True,
                    height=400
                )
            else:
                st.dataframe(recent_trades, use_container_width=True, height=400)
        else:
            st.info("No recent trades found")
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.exception(e)


if __name__ == "__main__":
    main()


