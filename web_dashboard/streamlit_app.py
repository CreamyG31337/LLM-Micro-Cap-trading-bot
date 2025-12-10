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

# CRITICAL: Inject JavaScript in page config to run before anything else
# This handles magic link callbacks from URL hash
st.markdown("""
<script>
// Run immediately on page load - must be in head/early body
window.addEventListener('DOMContentLoaded', function() {
    const hash = window.location.hash;
    console.log('[Magic Link] Checking hash:', hash);
    if (hash && hash.length > 1) {
        const hashParams = new URLSearchParams(hash.substring(1));
        
        // Check for errors
        if (hashParams.get('error')) {
            console.log('[Magic Link] Found error, redirecting...');
            const url = new URL(window.location);
            url.hash = '';
            url.searchParams.set('auth_error', hashParams.get('error'));
            if (hashParams.get('error_code')) url.searchParams.set('error_code', hashParams.get('error_code'));
            if (hashParams.get('error_description')) url.searchParams.set('error_desc', decodeURIComponent(hashParams.get('error_description')));
            window.location.replace(url.toString());
            return;
        }
        
        // Check for access_token
        const accessToken = hashParams.get('access_token');
        if (accessToken) {
            console.log('[Magic Link] Found access_token, redirecting...');
            const url = new URL(window.location);
            url.hash = '';
            url.searchParams.set('magic_token', accessToken);
            window.location.replace(url.toString());
            return;
        }
    }
});

// Also try immediately (in case DOMContentLoaded already fired)
(function() {
    const hash = window.location.hash;
    if (hash && hash.length > 1) {
        const hashParams = new URLSearchParams(hash.substring(1));
        if (hashParams.get('access_token') || hashParams.get('error')) {
            console.log('[Magic Link] Immediate check, hash found');
            // Let DOMContentLoaded handler process it
        }
    }
})();
</script>
""", unsafe_allow_html=True)

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

# Inject JavaScript immediately to handle URL hash (magic links and errors)
# This must run before Streamlit renders to catch the hash
st.markdown("""
<script>
// Run immediately, don't wait for anything
(function() {
    const hash = window.location.hash;
    console.log('Checking hash:', hash);
    if (hash && hash.length > 1) {
        const hashParams = new URLSearchParams(hash.substring(1));
        
        // Check for errors first
        if (hashParams.get('error')) {
            const error = hashParams.get('error');
            const errorCode = hashParams.get('error_code') || '';
            const errorDesc = hashParams.get('error_description') || '';
            
            console.log('Found error in hash, redirecting...');
            const url = new URL(window.location);
            url.hash = '';
            url.searchParams.set('auth_error', error);
            if (errorCode) url.searchParams.set('error_code', errorCode);
            if (errorDesc) url.searchParams.set('error_desc', decodeURIComponent(errorDesc));
            window.location.replace(url.toString());
            return;
        }
        
        // Check for access_token (magic link success)
        const accessToken = hashParams.get('access_token');
        if (accessToken) {
            console.log('Found access_token in hash, redirecting...');
            const url = new URL(window.location);
            url.hash = '';
            url.searchParams.set('magic_token', accessToken);
            window.location.replace(url.toString());
            return;
        }
    }
})();
</script>
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
                        if result and "access_token" in result:
                            set_user_session(result["access_token"], result["user"])
                            st.success("Registration successful! Please check your email to confirm your account.")
                            st.rerun()
                        else:
                            error_msg = result.get("error", "Registration failed") if result else "Registration failed"
                            st.error(f"Registration failed: {error_msg}")
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
    
    # Check for magic link token in query params
    query_params = st.query_params
    if "magic_token" in query_params and not is_authenticated():
        access_token = query_params["magic_token"]
        
        # Decode JWT to get user info
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


