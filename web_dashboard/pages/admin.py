#!/usr/bin/env python3
"""
Admin Page for Web Dashboard
Centralized admin functionality for managing users, funds, scheduled tasks, and system status
"""

import streamlit as st
import sys
import os
import time
from pathlib import Path
import pandas as pd
from datetime import datetime

# Try to import psutil for process checking (optional)
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, is_admin, get_user_email
from streamlit_utils import get_supabase_client, get_user_investment_metrics, get_historical_fund_values, get_current_positions, display_dataframe_with_copy
from supabase_client import SupabaseClient

# Page configuration
st.set_page_config(page_title="Admin Dashboard", page_icon="🔧", layout="wide")

# Check authentication - redirect to main page if not logged in
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Refresh token if needed (auto-refresh before expiry)
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    # Token refresh failed - session is invalid, redirect to login
    from auth_utils import logout_user
    logout_user()
    st.error("Your session has expired. Please log in again.")
    st.switch_page("streamlit_app.py")
    st.stop()

# Check admin status
if not is_admin():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Header with cache clearing button
col_header1, col_header2, col_header3 = st.columns([2, 2, 1])
with col_header1:
    st.markdown("# 🔧 Admin Dashboard")
with col_header3:
    st.write("")  # Spacer for alignment
    if st.button("🔄 Clear Cache", help="Force refresh all cached data from database", use_container_width=True):
        from datetime import datetime
        import logging
        
        logger = logging.getLogger(__name__)
        clear_time = datetime.now().isoformat()
        
        try:
            # Get cache stats before clearing (if available)
            logger.info(f"Cache clear initiated by {get_user_email()} at {clear_time}")
            
            # Clear ALL Streamlit data caches
            st.cache_data.clear()
            
            logger.info(f"Cache cleared successfully at {clear_time}")
            
            # Show toast notification that persists across rerun
            st.toast(
                f"✅ Cache cleared by {get_user_email()} at {datetime.now().strftime('%H:%M:%S')}",
                icon="✅"
            )
            
            # Log to file for audit trail
            try:
                from log_handler import log_message
                log_message("INFO", f"Cache cleared by {get_user_email()}")
            except:
                pass  # Logging is optional
            
            st.rerun()
            
        except Exception as e:
            error_msg = f"Failed to clear cache: {e}"
            logger.error(error_msg)
            st.error(f"❌ {error_msg}")

st.caption(f"Logged in as: {get_user_email()}")

# Display build timestamp (from Woodpecker CI environment variable)
import os
build_timestamp = os.getenv("BUILD_TIMESTAMP")
if build_timestamp:
    # Convert UTC timestamp to user's preferred timezone
    try:
        from user_preferences import format_timestamp_in_user_timezone
        build_timestamp = format_timestamp_in_user_timezone(build_timestamp)
    except ImportError:
        # Fallback if user_preferences not available
        if "UTC" in build_timestamp:
            build_timestamp = build_timestamp.replace(" UTC", " PST")
    st.caption(f"🏷️ Build: {build_timestamp}")
else:
    # Development mode - show current time in user's timezone (or PST)
    try:
        from user_preferences import get_user_timezone
        from zoneinfo import ZoneInfo
        user_tz_str = get_user_timezone() or "America/Vancouver"
        user_tz = ZoneInfo(user_tz_str)
        now = datetime.now(user_tz)
        dev_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
        st.caption(f"🏷️ Build: Development ({dev_timestamp})")
    except (ImportError, Exception):
        st.caption(f"🏷️ Build: Development ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

# Custom page navigation in sidebar
from navigation import render_navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# ===== CACHED HELPER FUNCTIONS FOR PERFORMANCE =====
# These functions cache frequently accessed data to reduce database queries

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_funds():
    """Get all funds from database with caching."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        funds_result = client.supabase.table("funds").select("*").order("name").execute()
        return funds_result.data if funds_result.data else []
    except Exception as e:
        st.error(f"Error loading funds: {e}")
        return []

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_fund_names():
    """Get fund names only (lighter query)."""
    funds = get_cached_funds()
    return [f['name'] for f in funds]

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_users():
    """Get all users with their fund assignments."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        result = client.supabase.rpc('list_users_with_funds').execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error loading users: {e}")
        return []

@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_contributors():
    """Get all contributors from database."""
    client = get_supabase_client()
    if not client:
        return []
    try:
        result = client.supabase.table("contributors").select("id, name, email").order("name").execute()
        return result.data if result.data else []
    except Exception as e:
        return []

# Create tabs for different admin sections
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "⏰ Scheduled Tasks",
    "👥 User Management", 
    "🔐 Contributor Access",
    "🏦 Fund Management",
    "📊 System Status",
    "📈 Trade Entry",
    "💰 Contributions",
    "📋 Logs",
    "🤖 AI Settings"
])

# Tab 1: Scheduled Tasks
with tab1:
    st.header("⏰ Scheduled Tasks")
    st.caption("Manage background jobs running in this container")
    
    try:
        # Import from parent directory
        import sys
        from pathlib import Path
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        from scheduler_ui import render_scheduler_admin
        render_scheduler_admin()
    except ImportError as e:
        st.warning(f"Scheduler UI not available: {e}")
        st.info("The scheduler module may not be running in this environment.")
    except Exception as e:
        st.error(f"Error loading scheduler: {e}")

# Tab 2: User Management
with tab2:
    st.header("👥 User Management")
    st.caption("Manage users and their fund assignments")
    
    client = get_supabase_client()
    if not client:
        st.error("Failed to connect to database")
    else:
        # Get all users with their fund assignments (using cache)
        with st.spinner("Loading users..."):
            try:
                users_df = pd.DataFrame(get_cached_users())
                
                if not users_df.empty:
                    # Display users table
                    st.subheader("All Users")
                    display_dataframe_with_copy(
                        users_df,
                        label="All Users",
                        key_suffix="all_users",
                        use_container_width=True,
                        column_config={
                            "email": "Email",
                            "full_name": "Full Name",
                            "funds": st.column_config.ListColumn("Assigned Funds")
                        }
                    )
                    
                    # Delete user section
                    st.subheader("Delete User")
                    st.warning("⚠️ This action cannot be undone. Contributors (users with fund contributions) cannot be deleted.")
                    
                    col_del1, col_del2 = st.columns(2)
                    with col_del1:
                        delete_email = st.selectbox(
                            "Select User to Delete",
                            options=[""] + users_df['email'].tolist(),
                            key="delete_user_select"
                        )
                    
                    with col_del2:
                        confirm_email = st.text_input(
                            "Type email to confirm",
                            key="confirm_delete_email",
                            placeholder="Type the email exactly to confirm"
                        )
                    
                    if st.button("🗑️ Delete User", type="secondary"):
                        if not delete_email:
                            st.error("Please select a user to delete")
                        elif confirm_email != delete_email:
                            st.error("Confirmation email does not match. Please type the email exactly.")
                        else:
                            try:
                                delete_result = client.supabase.rpc(
                                    'delete_user_safe',
                                    {'user_email': delete_email}
                                ).execute()
                                
                                if delete_result.data:
                                    result_data = delete_result.data
                                    if result_data.get('success'):
                                        st.cache_data.clear()  # Clear cache after deletion
                                        st.toast(f"✅ {result_data.get('message')}", icon="✅")
                                        st.rerun()
                                    else:
                                        if result_data.get('is_contributor'):
                                            st.error(f"🚫 {result_data.get('message')}")
                                        else:
                                            st.error(result_data.get('message'))
                                else:
                                    st.error("Failed to delete user")
                            except Exception as e:
                                st.error(f"Error deleting user: {e}")
                    
                    st.divider()
                    
                    # Fund assignment section
                    st.subheader("Assign Fund to User")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Get user emails from the users dataframe
                        user_emails = users_df['email'].tolist() if not users_df.empty else []
                        user_email = st.selectbox("User Email", options=[""] + user_emails, key="assign_user_email")
                    
                    # Get available funds from cache
                    available_funds = get_cached_fund_names()
                    
                    with col2:
                        fund_name = st.selectbox("Fund Name", options=[""] + available_funds, key="assign_fund_name")

                
                if st.button("Assign Fund", type="primary"):
                    if user_email and fund_name:
                        try:
                            assign_result = client.supabase.rpc(
                                'assign_fund_to_user',
                                {'user_email': user_email, 'fund_name': fund_name}
                            ).execute()
                            
                            # Handle JSON response - Supabase RPC returns JSON directly or wrapped in array
                            result_data = assign_result.data
                            if isinstance(result_data, list) and len(result_data) > 0:
                                result_data = result_data[0]
                            
                            if result_data and isinstance(result_data, dict):
                                if result_data.get('success'):
                                    st.toast(f"✅ {result_data.get('message', f'Assigned {fund_name} to {user_email}')}", icon="✅")
                                    st.rerun()
                                elif result_data.get('already_assigned'):
                                    st.warning(f"⚠️ {result_data.get('message', f'Fund {fund_name} is already assigned to {user_email}')}")
                                else:
                                    st.error(f"❌ {result_data.get('message', 'Failed to assign fund')}")
                            else:
                                st.error("Failed to assign fund - invalid response")
                        except Exception as e:
                            st.error(f"Error assigning fund: {e}")
                    else:
                        st.warning("Please enter both email and fund name")
                
                # Remove fund assignment
                st.subheader("Remove Fund Assignment")
                col3, col4 = st.columns(2)
                
                with col3:
                    # Get user emails from the users dataframe
                    remove_user_emails = users_df['email'].tolist() if not users_df.empty else []
                    remove_email = st.selectbox("User Email", options=[""] + remove_user_emails, key="remove_email")
                
                with col4:
                    # Use the same funds list from funds table
                    remove_fund = st.selectbox("Fund Name", options=[""] + available_funds, key="remove_fund")
                
                if st.button("Remove Assignment", type="secondary"):
                    if remove_email and remove_fund:
                        try:
                            # Use RPC function that queries auth.users (same as assign_fund_to_user)
                            # This ensures consistency - both assign and remove use the same user lookup
                            remove_result = client.supabase.rpc(
                                'remove_fund_from_user',
                                {'user_email': remove_email, 'fund_name': remove_fund}
                            ).execute()
                            # Handle boolean result properly (False is valid, None is error)
                            if remove_result.data is not None:
                                if remove_result.data:
                                    st.toast(f"✅ Removed {remove_fund} from {remove_email}", icon="✅")
                                    st.rerun()
                                else:
                                    st.warning(f"No assignment found for {remove_email} → {remove_fund}")
                            else:
                                st.error("Failed to remove fund assignment")
                        except Exception as e:
                            st.error(f"Error removing assignment: {e}")
                    else:
                        st.warning("Please enter both email and fund name")
            else:
                st.info("No users found")
        except Exception as e:
            st.error(f"Error loading users: {e}")
        
        # Unregistered contributors section
        st.divider()
        st.subheader("📨 Unregistered Contributors")
        st.caption("Contributors with fund contributions who haven't created an account yet")
        
        try:
            contrib_result = client.supabase.rpc('list_unregistered_contributors').execute()
            
            if contrib_result.data and len(contrib_result.data) > 0:
                contrib_df = pd.DataFrame(contrib_result.data)
                
                # Display contributors with invite buttons
                for idx, row in contrib_df.iterrows():
                    with st.container():
                        col_info, col_action = st.columns([3, 1])
                        
                        # Handle missing email
                        email_display = row['email'] if row.get('email') else "No Email"
                        has_email = bool(row.get('email'))
                        
                        with col_info:
                            funds_str = ", ".join(row['funds']) if row['funds'] else "None"
                            st.markdown(f"**{row['contributor']}** ({email_display})")
                            st.caption(f"Funds: {funds_str} | Contribution: ${row['total_contribution']:,.2f}")
                        
                        with col_action:
                            if has_email:
                                if st.button("📧 Send Invite", key=f"invite_{idx}"):
                                    try:
                                        from auth_utils import send_magic_link
                                        result = send_magic_link(row['email'])
                                        if result and result.get('success'):
                                            st.success(f"Invite sent to {row['email']}")
                                        else:
                                            error_msg = result.get('error', 'Unknown error') if result else 'Failed to send'
                                            st.error(f"Failed: {error_msg}")
                                    except Exception as e:
                                        st.error(f"Error: {e}")
                            else:
                                st.warning("⚠️ Add email to invite")
                        
                        st.divider()
            else:
                st.success("✅ All contributors have registered accounts!")
        except Exception as e:
            st.warning(f"Could not load unregistered contributors: {e}")
            st.info("You may need to run the `list_unregistered_contributors` SQL function in Supabase.")

# Tab 3: Contributor Access Management
with tab3:
    st.header("🔐 Contributor Access Management")
    st.caption("Manage which users can view/manage which contributors' accounts")
    
    client = get_supabase_client()
    if not client:
        st.error("Failed to connect to database")
    else:
        try:
            # Check if contributors table exists
            # Try a simple query - if it fails, it could be missing table or RLS blocking
            has_contributors_table = False
            table_error = None
            try:
                # Try to query the table (even if empty, this should work if table exists)
                contributors_result = client.supabase.table("contributors").select("id").limit(1).execute()
                has_contributors_table = True
            except Exception as e:
                table_error = str(e)
                # Check if it's a "relation does not exist" error (table actually missing)
                if "does not exist" in table_error.lower() or "relation" in table_error.lower() or "42P01" in table_error:
                    st.warning("⚠️ Contributors table not found. Run migration DF_009 first.")
                else:
                    # Other error - could be RLS, permissions, or table exists but empty
                    # For admins, try to proceed anyway (they should have access)
                    if is_admin():
                        st.info("ℹ️ Note: Contributors table may exist but query returned no results or was blocked by RLS.")
                        st.info("💡 Proceeding anyway - you're admin so you should have access.")
                        has_contributors_table = True  # Assume it exists for admins
                    else:
                        st.warning(f"⚠️ Could not access contributors table: {table_error}")
                        st.info("💡 The table might exist but RLS is blocking access. Contact an admin.")
            
            if has_contributors_table:
                # Get all contributors (using cache)
                contributors_list = get_cached_contributors()
                
                # Get all users (using cache)
                users_list = get_cached_users()
                
                if contributors_list:
                    st.subheader("Grant Access")
                    st.caption("Allow a user to view/manage a contributor's account")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        # Contributor selector
                        contributor_options = {f"{c['name']} ({c['email'] or 'No email'})": c['id'] for c in contributors_list}
                        selected_contributor_display = st.selectbox(
                            "Contributor",
                            options=[""] + list(contributor_options.keys()),
                            key="grant_contributor"
                        )
                        selected_contributor_id = contributor_options.get(selected_contributor_display) if selected_contributor_display else None
                    
                    with col2:
                        # User selector
                        user_options = {u['email']: u['user_id'] for u in users_list if u.get('user_id')}
                        selected_user_email = st.selectbox(
                            "User Email",
                            options=[""] + list(user_options.keys()),
                            key="grant_user"
                        )
                        selected_user_id = user_options.get(selected_user_email) if selected_user_email else None
                    
                    with col3:
                        access_level = st.selectbox(
                            "Access Level",
                            options=["viewer", "manager", "owner"],
                            key="grant_access_level",
                            help="viewer: Can view data | manager: Can view and manage | owner: Full control"
                        )
                    
                    if st.button("🔐 Grant Access", type="primary"):
                        if not selected_contributor_id or not selected_user_id:
                            st.error("Please select both contributor and user")
                        else:
                            try:
                                result = client.supabase.rpc(
                                    'grant_contributor_access',
                                    {
                                        'contributor_email': next((c['email'] for c in contributors_list if c['id'] == selected_contributor_id), ''),
                                        'user_email': selected_user_email,
                                        'access_level': access_level
                                    }
                                ).execute()
                                
                                if result.data:
                                    result_data = result.data[0] if isinstance(result.data, list) else result.data
                                    if result_data.get('success'):
                                        st.toast(f"✅ {result_data.get('message')}", icon="✅")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ {result_data.get('message')}")
                            except Exception as e:
                                st.error(f"Error granting access: {e}")
                    
                    st.divider()
                    
                    # View current access
                    st.subheader("Current Access")
                    st.caption("View all contributor-user access relationships")
                    
                    try:
                        access_result = client.supabase.table("contributor_access").select(
                            "id, contributor_id, user_id, access_level, granted_at"
                        ).execute()
                        
                        if access_result.data:
                            # Get contributor and user details
                            access_list = []
                            for access in access_result.data:
                                # Get contributor details
                                contrib = next((c for c in contributors_list if c['id'] == access['contributor_id']), {})
                                # Get user details
                                user = next((u for u in users_list if u.get('user_id') == access['user_id']), {})
                                
                                access_list.append({
                                    "Contributor": contrib.get('name', 'Unknown'),
                                    "Contributor Email": contrib.get('email', 'No email'),
                                    "User Email": user.get('email', 'Unknown'),
                                    "User Name": user.get('full_name', ''),
                                    "Access Level": access.get('access_level', 'viewer'),
                                    "Granted": access.get('granted_at', '')[:10] if access.get('granted_at') else ''
                                })
                            
                            access_df = pd.DataFrame(access_list)
                            display_dataframe_with_copy(access_df, label="Contributor Access", key_suffix="access", use_container_width=True)
                            
                            # Revoke access section
                            st.subheader("Revoke Access")
                            col_rev1, col_rev2 = st.columns(2)
                            
                            with col_rev1:
                                revoke_contributor = st.selectbox(
                                    "Contributor",
                                    options=[""] + list(contributor_options.keys()),
                                    key="revoke_contributor"
                                )
                            
                            with col_rev2:
                                revoke_user = st.selectbox(
                                    "User Email",
                                    options=[""] + list(user_options.keys()),
                                    key="revoke_user"
                                )
                            
                            if st.button("🚫 Revoke Access", type="secondary"):
                                if not revoke_contributor or not revoke_user:
                                    st.error("Please select both contributor and user")
                                else:
                                    try:
                                        revoke_contributor_id = contributor_options.get(revoke_contributor)
                                        result = client.supabase.rpc(
                                            'revoke_contributor_access',
                                            {
                                                'contributor_email': next((c['email'] for c in contributors_list if c['id'] == revoke_contributor_id), ''),
                                                'user_email': revoke_user
                                            }
                                        ).execute()
                                        
                                        if result.data:
                                            result_data = result.data[0] if isinstance(result.data, list) else result.data
                                            if result_data.get('success'):
                                                st.toast(f"✅ {result_data.get('message')}", icon="✅")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ {result_data.get('message')}")
                                    except Exception as e:
                                        st.error(f"Error revoking access: {e}")
                        else:
                            st.info("No access records found. Grant access to link users to contributors.")
                    except Exception as e:
                        st.warning(f"Could not load access records: {e}")
                        st.info("Make sure the contributor_access table exists (run migration DF_009)")
                else:
                    st.info("No contributors found. Add contributors in the Contributions tab.")
        except Exception as e:
            st.error(f"Error loading contributor access: {e}")

# Tab 4: Fund Management
with tab4:
    st.header("🏦 Fund Management")
    st.caption("Manage funds in the system")
    
    client = get_supabase_client()
    if not client:
        st.error("Failed to connect to database")
    else:
        # Load all funds from cache with spinner
        with st.spinner("Loading funds..."):
            try:
                funds_data = get_cached_funds()
                fund_names = [f['name'] for f in funds_data]
                
                # Get statistics for each fund
                if fund_names:
                    fund_stats = []
                    for fund_name in fund_names:
                        # Get position count
                        pos_count = client.supabase.table("portfolio_positions").select("id", count="exact").eq("fund", fund_name).execute()
                        position_count = pos_count.count if hasattr(pos_count, 'count') else len(pos_count.data) if pos_count.data else 0
                        
                        # Get trade count
                        trade_count = client.supabase.table("trade_log").select("id", count="exact").eq("fund", fund_name).execute()
                        trade_count_val = trade_count.count if hasattr(trade_count, 'count') else len(trade_count.data) if trade_count.data else 0
                        
                        # Get fund details
                        fund_info = next((f for f in funds_data if f['name'] == fund_name), {})
                        
                        fund_stats.append({
                            "Fund Name": fund_name,
                            "Type": fund_info.get('fund_type', 'N/A'),
                            "Currency": fund_info.get('currency', 'N/A'),
                            "Production": "✅" if fund_info.get('is_production') else "❌",
                            "Positions": position_count,
                            "Trades": trade_count_val
                        })
                    
                    funds_df = pd.DataFrame(fund_stats)
                    st.subheader("All Funds")
                    display_dataframe_with_copy(funds_df, label="All Funds", key_suffix="funds", use_container_width=True)
                else:
                    st.info("No funds found in database")

            
            st.divider()
            
            # ===== TOGGLE PRODUCTION FLAG =====
            st.subheader("🏭 Toggle Production Status")
            st.caption("Mark funds as production (included in automated backfill) or test/dev (excluded)")
            with st.expander("Manage production flags", expanded=True):
                if fund_names:
                    for fund_name in fund_names:
                        fund_info = next((f for f in funds_result.data if f['name'] == fund_name), {})
                        is_prod = fund_info.get('is_production', False)
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{fund_name}**")
                        with col2:
                            new_status = st.checkbox(
                                "Production",
                                value=is_prod,
                                key=f"prod_{fund_name}",
                                label_visibility="collapsed"
                            )
                            
                            # Update if changed
                            if new_status != is_prod:
                                try:
                                    client.supabase.table("funds")\
                                        .update({"is_production": new_status})\
                                        .eq("name", fund_name)\
                                        .execute()
                                    st.toast(f"✅ {fund_name} marked as {'production' if new_status else 'test/dev'}", icon="✅")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating {fund_name}: {e}")
                else:
                    st.info("No funds found")
            
            st.divider()
            
            # ===== ADD NEW FUND =====
            st.subheader("➕ Add New Fund")
            with st.expander("Create a new fund", expanded=False):
                col_add1, col_add2 = st.columns(2)
                with col_add1:
                    new_fund_name = st.text_input("Fund Name", placeholder="e.g., TFSA, RRSP", key="new_fund_name")
                    new_fund_type = st.selectbox("Fund Type", options=["investment", "retirement", "tfsa", "test"], key="new_fund_type")
                with col_add2:
                    new_fund_description = st.text_input("Description", placeholder="Description of the fund", key="new_fund_desc")
                    new_fund_currency = st.selectbox("Currency", options=["CAD", "USD"], key="new_fund_currency")
                
                if st.button("➕ Create Fund", type="primary"):
                    if not new_fund_name:
                        st.error("Please enter a fund name")
                    elif new_fund_name in fund_names:
                        st.error(f"Fund '{new_fund_name}' already exists")
                    else:
                        try:
                            # Insert into funds table
                            client.supabase.table("funds").insert({
                                "name": new_fund_name,
                                "description": new_fund_description,
                                "currency": new_fund_currency,
                                "fund_type": new_fund_type
                            }).execute()
                            
                            # Initialize cash balances for the new fund
                            client.supabase.table("cash_balances").upsert([
                                {"fund": new_fund_name, "currency": "CAD", "amount": 0},
                                {"fund": new_fund_name, "currency": "USD", "amount": 0}
                            ]).execute()
                            
                            st.toast(f"✅ Fund '{new_fund_name}' created!", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error creating fund: {e}")
            
            st.divider()
            
            # ===== RENAME FUND =====
            st.subheader("✏️ Rename Fund")
            with st.expander("Rename an existing fund", expanded=False):
                col_ren1, col_ren2 = st.columns(2)
                with col_ren1:
                    rename_fund = st.selectbox("Select Fund to Rename", options=[""] + fund_names, key="rename_fund_select")
                with col_ren2:
                    new_name = st.text_input("New Fund Name", key="rename_new_name")
                
                if st.button("✏️ Rename Fund", type="primary"):
                    if not rename_fund:
                        st.error("Please select a fund to rename")
                    elif not new_name:
                        st.error("Please enter a new name")
                    elif new_name in fund_names:
                        st.error(f"Fund '{new_name}' already exists")
                    else:
                        try:
                            # Update funds table - ON UPDATE CASCADE will update all related tables
                            client.supabase.table("funds").update({"name": new_name}).eq("name", rename_fund).execute()
                            st.toast(f"✅ Fund renamed to '{new_name}'", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error renaming fund: {e}")
            
            st.divider()
            
            # ===== WIPE FUND DATA =====
            st.subheader("🧹 Wipe Fund Data")
            st.warning("⚠️ This clears all positions, trades, and metrics but keeps the fund and contribution records.")
            with st.expander("Wipe data for a fund", expanded=False):
                col_wipe1, col_wipe2 = st.columns(2)
                with col_wipe1:
                    wipe_fund = st.selectbox("Select Fund to Wipe", options=[""] + fund_names, key="wipe_fund_select")
                with col_wipe2:
                    confirm_wipe_name = st.text_input("Type fund name to confirm", key="confirm_wipe_name", 
                                                       placeholder="Type the fund name exactly")
                
                if st.button("🧹 Wipe Fund Data", type="secondary"):
                    if not wipe_fund:
                        st.error("Please select a fund")
                    elif confirm_wipe_name != wipe_fund:
                        st.error("Fund name doesn't match. Please type the fund name exactly to confirm.")
                    else:
                        try:
                            # Check if this is a production fund
                            fund_info = client.supabase.table("funds").select("is_production").eq("name", wipe_fund).execute()
                            is_production = fund_info.data[0].get("is_production", False) if fund_info.data else False
                            
                            # Clear portfolio_positions
                            client.supabase.table("portfolio_positions").delete().eq("fund", wipe_fund).execute()
                            
                            # SAFETY: Only clear trades for NON-production funds
                            if not is_production:
                                client.supabase.table("trade_log").delete().eq("fund", wipe_fund).execute()
                            else:
                                st.warning("⚠️ Trade log NOT wiped (production fund - use 'Wipe Portfolio Positions Only' instead)")
                            
                            # Clear performance_metrics
                            client.supabase.table("performance_metrics").delete().eq("fund", wipe_fund).execute()
                            # Reset cash_balances to 0
                            client.supabase.table("cash_balances").update({"amount": 0}).eq("fund", wipe_fund).execute()
                            
                            st.toast(f"✅ Data wiped for '{wipe_fund}'", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error wiping fund data: {e}")
            
            st.divider()
            
            # ===== WIPE PORTFOLIO POSITIONS ONLY (SAFE) =====
            st.subheader("🔄 Wipe Portfolio Positions Only")
            st.info("✅ SAFE: Clears only portfolio_positions. Keeps trades, so you can rebuild.")
            with st.expander("Wipe portfolio positions only", expanded=False):
                wipe_pos_fund = st.selectbox("Select Fund", options=[""] + fund_names, key="wipe_pos_fund_select")
                
                if st.button("🔄 Wipe Portfolio Positions Only", type="primary"):
                    if not wipe_pos_fund:
                        st.error("Please select a fund")
                    else:
                        try:
                            # Use service role to bypass RLS
                            service_client = SupabaseClient(use_service_role=True)
                            
                            # Delete in batches (safe for large datasets)
                            deleted_total = 0
                            while True:
                                batch = service_client.supabase.table("portfolio_positions") \
                                    .select("id") \
                                    .eq("fund", wipe_pos_fund) \
                                    .limit(500) \
                                    .execute()
                                
                                if not batch.data:
                                    break
                                
                                ids = [r['id'] for r in batch.data]
                                service_client.supabase.table("portfolio_positions") \
                                    .delete() \
                                    .in_("id", ids) \
                                    .execute()
                                
                                deleted_total += len(ids)
                                
                                if len(batch.data) < 500:
                                    break
                            
                            st.toast(f"✅ Wiped {deleted_total} portfolio positions for '{wipe_pos_fund}'", icon="✅")
                            st.success(f"Trades and contributions preserved. Use 'Rebuild Portfolio' to regenerate.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error wiping portfolio positions: {e}")
            
            st.divider()
            
            # ===== REBUILD PORTFOLIO FROM TRADES =====
            st.subheader("🔧 Rebuild Portfolio from Trades")
            st.info("Regenerates all portfolio_positions from trade log with proper columns.")
            with st.expander("Rebuild portfolio data", expanded=False):
                rebuild_fund = st.selectbox("Select Fund to Rebuild", options=[""] + fund_names, key="rebuild_fund_select")
                
                if rebuild_fund:
                    # Check if trades exist in database
                    trade_count = client.supabase.table("trade_log") \
                        .select("count", count="exact") \
                        .eq("fund", rebuild_fund) \
                        .execute()
                    
                    if trade_count.count and trade_count.count > 0:
                        st.success(f"✅ Found {trade_count.count} trades in database")
                    else:
                        st.error(f"❌ No trades found in database for {rebuild_fund}")
                
                if st.button("🔧 Rebuild Portfolio", type="primary"):
                    if not rebuild_fund:
                        st.error("Please select a fund")
                    else:
                        # Check if trades exist
                        trade_count = client.supabase.table("trade_log") \
                            .select("count", count="exact") \
                            .eq("fund", rebuild_fund) \
                            .execute()
                        
                        if not trade_count.count or trade_count.count == 0:
                            st.error(f"No trades found in database for {rebuild_fund}")
                        else:
                            import subprocess
                            import tempfile
                            
                            # Lock file to prevent concurrent execution
                            # Use a global lock file (not per-fund) to prevent any concurrent rebuilds
                            lock_file_path = Path(tempfile.gettempdir()) / "portfolio_rebuild.lock"
                            
                            # Check if rebuild is already running
                            rebuild_running = False
                            if lock_file_path.exists():
                                # Check if the process in the lock file is still running
                                try:
                                    with open(lock_file_path, 'r') as f:
                                        pid = int(f.read().strip())
                                    
                                    if PSUTIL_AVAILABLE:
                                        if psutil.pid_exists(pid):
                                            # Check if it's actually the rebuild script
                                            try:
                                                proc = psutil.Process(pid)
                                                cmdline = ' '.join(proc.cmdline())
                                                if 'rebuild_portfolio_complete.py' in cmdline:
                                                    rebuild_running = True
                                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                                # Process doesn't exist or we can't access it - remove stale lock
                                                try:
                                                    lock_file_path.unlink()
                                                except:
                                                    pass
                                        else:
                                            # Process doesn't exist - remove stale lock
                                            try:
                                                lock_file_path.unlink()
                                            except:
                                                pass
                                    else:
                                        # psutil not available - just check if lock file exists and is recent (< 30 min)
                                        # This is a fallback for systems without psutil
                                        try:
                                            lock_age = time.time() - lock_file_path.stat().st_mtime
                                            if lock_age < 1800:  # Lock file is less than 30 minutes old
                                                rebuild_running = True
                                            else:
                                                # Stale lock file - remove it
                                                lock_file_path.unlink()
                                        except:
                                            pass
                                except (ValueError, FileNotFoundError, OSError):
                                    # Lock file is invalid or missing - remove it
                                    try:
                                        lock_file_path.unlink()
                                    except:
                                        pass
                            
                            if rebuild_running:
                                st.warning("⚠️ A portfolio rebuild is already running. Please wait for it to complete before starting another.")
                            else:
                                # The rebuild script still needs a data directory for CSV operations
                                # But it will use database trades as the source
                                data_dir = f"trading_data/funds/{rebuild_fund}"
                                
                                # Determine project root and script path
                                # In Docker: /app is project root, script is at /app/debug/rebuild_portfolio_complete.py
                                # In local dev: script is at project_root/debug/rebuild_portfolio_complete.py
                                # admin.py is at web_dashboard/pages/admin.py, so go up 2 levels to get project root
                                admin_file = Path(__file__).resolve()
                                # admin.py is in web_dashboard/pages/, so:
                                #   parent = web_dashboard/pages/
                                #   parent.parent = web_dashboard/
                                #   parent.parent.parent = project root
                                project_root = admin_file.parent.parent.parent
                                rebuild_script = project_root / "debug" / "rebuild_portfolio_complete.py"
                                
                                # Also try alternative paths in case the structure is different
                                if not rebuild_script.exists():
                                    # Try going up one less level (in case we're already at project root)
                                    alt_project_root = admin_file.parent.parent
                                    alt_script = alt_project_root / "debug" / "rebuild_portfolio_complete.py"
                                    if alt_script.exists():
                                        project_root = alt_project_root
                                        rebuild_script = alt_script
                                    else:
                                        # Try absolute path from /app (Docker)
                                        docker_script = Path("/app/debug/rebuild_portfolio_complete.py")
                                        if docker_script.exists():
                                            project_root = Path("/app")
                                            rebuild_script = docker_script
                                
                                if not rebuild_script.exists():
                                    st.error(f"❌ Rebuild script not found!")
                                    st.error(f"Tried paths:")
                                    st.error(f"  - {project_root / 'debug' / 'rebuild_portfolio_complete.py'}")
                                    st.error(f"  - {admin_file.parent.parent / 'debug' / 'rebuild_portfolio_complete.py'}")
                                    st.error(f"  - /app/debug/rebuild_portfolio_complete.py")
                                    st.error(f"Admin file location: {admin_file}")
                                    st.error(f"Project root: {project_root}")
                                    st.error(f"Current working directory: {os.getcwd()}")
                                    st.error(f"Python path: {sys.path[:3]}")
                                else:
                                    try:
                                        # Create lock file with current process PID
                                        # Note: On Windows, we'll use a simpler approach since fcntl isn't available
                                        try:
                                            with open(lock_file_path, 'w') as f:
                                                f.write(str(os.getpid()))
                                        except Exception as lock_error:
                                            st.warning(f"Could not create lock file: {lock_error}. Proceeding anyway...")
                                        
                                        # Run rebuild script in background so it continues even if user navigates away
                                        # Use Popen with start_new_session to detach from Streamlit process
                                        import subprocess as sp
                                        
                                        st.info(f"🚀 Starting rebuild for {rebuild_fund}... This will run in the background.")
                                        st.info("💡 You can navigate away or log out - the rebuild will continue running.")
                                        st.info("📋 Check Application Logs tab to monitor progress.")
                                        
                                        try:
                                            # Start process in background with new session (detached from Streamlit)
                                            # This ensures it continues even if user logs out or navigates away
                                            if os.name == 'nt':  # Windows
                                                # Windows: Use CREATE_NEW_PROCESS_GROUP to detach
                                                process = sp.Popen(
                                                    ["python", str(rebuild_script), data_dir, rebuild_fund],
                                                    cwd=str(project_root),
                                                    stdout=sp.PIPE,
                                                    stderr=sp.PIPE,
                                                    text=True,
                                                    creationflags=sp.CREATE_NEW_PROCESS_GROUP
                                                )
                                            else:  # Unix/Linux/Docker
                                                # Unix: Use start_new_session to detach from parent
                                                process = sp.Popen(
                                                    ["python", str(rebuild_script), data_dir, rebuild_fund],
                                                    cwd=str(project_root),
                                                    stdout=sp.PIPE,
                                                    stderr=sp.PIPE,
                                                    text=True,
                                                    start_new_session=True
                                                )
                                            
                                            st.success(f"✅ Rebuild started in background (PID: {process.pid})")
                                            st.info("📋 The rebuild will continue running even if you navigate away.")
                                            st.info("💡 Check the Application Logs tab to see progress updates.")
                                            st.info("⏱️  This may take up to 30 minutes for large funds.")
                                            
                                            # Don't wait for completion - let it run in background
                                            # User can check logs to see when it completes
                                            # Lock file will be removed when process completes (handled by script cleanup)
                                            
                                        except Exception as e:
                                            st.error(f"Error starting rebuild: {e}")
                                            import traceback
                                            with st.expander("Exception details"):
                                                st.code(traceback.format_exc())
                                            # Only remove lock file if we failed to start the process
                                            try:
                                                if lock_file_path.exists():
                                                    lock_file_path.unlink()
                                            except Exception:
                                                pass
                                        # Note: Lock file is NOT removed here when process starts successfully
                                        # The lock file will be cleaned up by the process when it completes
                                        # or can be manually removed if the process crashes
                                    except Exception as e:
                                        st.error(f"Error during rebuild setup: {e}")
                                        import traceback
                                        with st.expander("Exception details"):
                                            st.code(traceback.format_exc())
                                        # Remove lock file if setup failed
                                        try:
                                            if lock_file_path.exists():
                                                lock_file_path.unlink()
                                        except Exception:
                                            pass
            
            st.divider()
            
            # ===== DELETE FUND =====
            st.subheader("🗑️ Delete Fund")
            st.error("⚠️ DANGER: This permanently deletes the fund and ALL its data including contributions!")
            with st.expander("Permanently delete a fund", expanded=False):
                col_del1, col_del2 = st.columns(2)
                with col_del1:
                    delete_fund = st.selectbox("Select Fund to Delete", options=[""] + fund_names, key="delete_fund_select")
                with col_del2:
                    confirm_delete_name = st.text_input("Type fund name to confirm", key="confirm_delete_name",
                                                         placeholder="Type the fund name exactly")
                
                # Show what will be deleted
                if delete_fund:
                    pos_count = client.supabase.table("portfolio_positions").select("id", count="exact").eq("fund", delete_fund).execute()
                    trade_count = client.supabase.table("trade_log").select("id", count="exact").eq("fund", delete_fund).execute()
                    contrib_count = client.supabase.table("fund_contributions").select("id", count="exact").eq("fund", delete_fund).execute()
                    
                    pos_val = pos_count.count if hasattr(pos_count, 'count') else 0
                    trade_val = trade_count.count if hasattr(trade_count, 'count') else 0
                    contrib_val = contrib_count.count if hasattr(contrib_count, 'count') else 0
                    
                    st.info(f"📊 Records to delete: {pos_val} positions, {trade_val} trades, {contrib_val} contributions")
                
                if st.button("🗑️ Delete Fund Permanently", type="secondary"):
                    if not delete_fund:
                        st.error("Please select a fund")
                    elif confirm_delete_name != delete_fund:
                        st.error("Fund name doesn't match. Please type the fund name exactly to confirm.")
                    else:
                        try:
                            # First clear all dependent data (FK constraints use ON DELETE RESTRICT)
                            client.supabase.table("portfolio_positions").delete().eq("fund", delete_fund).execute()
                            client.supabase.table("trade_log").delete().eq("fund", delete_fund).execute()
                            client.supabase.table("performance_metrics").delete().eq("fund", delete_fund).execute()
                            client.supabase.table("cash_balances").delete().eq("fund", delete_fund).execute()
                            client.supabase.table("fund_contributions").delete().eq("fund", delete_fund).execute()
                            # Try to delete fund_thesis if it exists
                            try:
                                client.supabase.table("fund_thesis").delete().eq("fund", delete_fund).execute()
                            except:
                                pass  # Table may not exist
                            
                            # Now delete the fund itself
                            client.supabase.table("funds").delete().eq("name", delete_fund).execute()
                            
                            st.toast(f"✅ Fund '{delete_fund}' permanently deleted", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting fund: {e}")
                            
        except Exception as e:
            st.error(f"Error loading funds: {e}")

# Tab 5: System Status
with tab5:
    st.header("📊 System Status")
    st.caption("Monitor system health and status")
    
    client = get_supabase_client()
    if not client:
        st.error("❌ Database: Connection Failed")
    else:
        # Database connection status
        st.subheader("Database Status")
        try:
            # Test connection with a simple query
            test_result = client.supabase.table("user_profiles").select("user_id").limit(1).execute()
            st.success("✅ Database: Connected")
        except Exception as e:
            st.error(f"❌ Database: Connection Error - {e}")
        
        # Exchange rates status
        st.subheader("Exchange Rates")
        try:
            rates_result = client.supabase.table("exchange_rates").select("timestamp").order("timestamp", desc=True).limit(1).execute()
            if rates_result.data:
                latest_rate_date = rates_result.data[0]['timestamp']
                st.info(f"Latest rate: {latest_rate_date}")
            else:
                st.warning("No exchange rates found")
        except Exception as e:
            st.error(f"Error checking exchange rates: {e}")
        
        # Performance metrics status
        st.subheader("Performance Metrics")
        try:
            metrics_result = client.supabase.table("performance_metrics").select("date").order("date", desc=True).limit(1).execute()
            if metrics_result.data:
                latest_metrics_date = metrics_result.data[0]['date']
                st.info(f"Latest metrics: {latest_metrics_date}")
            else:
                st.warning("No performance metrics found")
        except Exception as e:
            st.error(f"Error checking performance metrics: {e}")
        
        # Postgres (Research Repository) status
        st.subheader("Postgres (Research Repository)")
        try:
            from web_dashboard.postgres_client import PostgresClient
            from web_dashboard.research_repository import ResearchRepository
            
            pg_client = PostgresClient()
            if pg_client.test_connection():
                st.success("✅ Postgres: Connected")
                
                # Get stats
                repo = ResearchRepository(pg_client)
                stats_result = pg_client.execute_query("SELECT COUNT(*) as count FROM research_articles")
                total = stats_result[0]['count'] if stats_result else 0
                st.info(f"Total research articles: {total}")
                
                # Recent articles
                recent_result = pg_client.execute_query("""
                    SELECT COUNT(*) as count 
                    FROM research_articles 
                    WHERE fetched_at >= NOW() - INTERVAL '7 days'
                """)
                recent = recent_result[0]['count'] if recent_result else 0
                st.info(f"Articles (last 7 days): {recent}")
            else:
                st.error("❌ Postgres: Connection Failed")
        except ImportError:
            st.warning("⚠️ Postgres client not available (psycopg2 not installed)")
        except Exception as e:
            st.error(f"❌ Postgres: Error - {str(e)[:100]}")
        
        # Job execution logs (from scheduler)
        st.subheader("Recent Job Executions")
        try:
            from scheduler.scheduler_core import get_job_logs
            all_jobs = ['exchange_rates', 'performance_metrics']
            
            for job_id in all_jobs:
                logs = get_job_logs(job_id, limit=5)
                if logs:
                    st.write(f"**{job_id}**")
                    for log in logs:
                        status = "✅" if log['success'] else "❌"
                        time_str = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        st.text(f"{status} {time_str} - {log['message'][:50]}")
        except ImportError:
            st.info("Scheduler module not available")
        except Exception as e:
            st.warning(f"Could not load job logs: {e}")

# Tab 6: Trade Entry
with tab6:
    st.header("📈 Trade Entry")
    st.caption("Add buy or sell trades to a fund")
    
    client = get_supabase_client()
    if not client:
        st.error("Failed to connect to database")
    else:
        try:
            # Get available funds
            funds_result = client.supabase.table("funds").select("name").order("name").execute()
            fund_names = [row['name'] for row in funds_result.data] if funds_result.data else []
            
            if not fund_names:
                st.warning("No funds available. Create a fund first in Fund Management.")
            else:
                # Trade form
                st.subheader("Enter Trade")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    trade_fund = st.selectbox("Fund", options=fund_names, key="trade_fund")
                    trade_action = st.selectbox("Action", options=["BUY", "SELL"], key="trade_action")
                    trade_ticker = st.text_input("Ticker Symbol", placeholder="e.g., AAPL, MSFT", key="trade_ticker").upper()
                
                with col2:
                    trade_shares = st.number_input("Shares", min_value=0.000001, value=1.0, step=1.0, format="%.6f", key="trade_shares")
                    trade_price = st.number_input("Price ($)", min_value=0.01, value=100.0, step=0.01, format="%.2f", key="trade_price")
                    trade_currency = st.selectbox("Currency", options=["USD", "CAD"], key="trade_currency")
                
                # Optional fields
                with st.expander("Additional Options", expanded=False):
                    trade_reason = st.text_input("Reason/Notes", placeholder="e.g., Limit order filled", key="trade_reason")
                    trade_date = st.date_input("Trade Date", value=datetime.now(), key="trade_date")
                    trade_time = st.time_input("Trade Time", value=datetime.now().time(), key="trade_time")
                
                # Ticker validation
                if trade_ticker:
                    ticker_check = client.supabase.table("securities").select("ticker, company_name, currency").eq("ticker", trade_ticker).execute()
                    if ticker_check.data:
                        st.success(f"✅ {ticker_check.data[0].get('company_name', trade_ticker)} ({ticker_check.data[0].get('currency', 'USD')})")
                    else:
                        st.warning(f"⚠️ Ticker '{trade_ticker}' not in securities table. Will be added.")
                
                # Calculate totals
                total_value = trade_shares * trade_price
                st.info(f"💵 Total Value: ${total_value:,.2f} {trade_currency}")
                
                if st.button("📈 Submit Trade", type="primary"):
                    if not trade_ticker:
                        st.error("Please enter a ticker symbol")
                    elif trade_shares <= 0:
                        st.error("Shares must be greater than 0")
                    elif trade_price <= 0:
                        st.error("Price must be greater than 0")
                    else:
                        try:
                            # Combine date and time
                            trade_datetime = datetime.combine(trade_date, trade_time)
                            
                            # Ensure ticker exists in securities table
                            if not ticker_check.data:
                                client.supabase.table("securities").insert({
                                    "ticker": trade_ticker,
                                    "company_name": trade_ticker,
                                    "currency": trade_currency
                                }).execute()
                            
                            # Calculate cost basis and P&L
                            cost_basis = trade_shares * trade_price
                            pnl = 0
                            
                            # Calculate P&L for SELL trades using FIFO
                            if trade_action == "SELL":
                                try:
                                    from collections import deque
                                    from decimal import Decimal
                                    
                                    # Get existing trades for this ticker (FIFO order)
                                    existing_trades = client.supabase.table("trade_log") \
                                        .select("shares, price, action, reason") \
                                        .eq("fund", trade_fund) \
                                        .eq("ticker", trade_ticker) \
                                        .order("date") \
                                        .execute()
                                    
                                    # Build FIFO lot queue
                                    lots = deque()
                                    for t in (existing_trades.data or []):
                                        is_buy = (t.get('action') == 'BUY' or 'BUY' in str(t.get('reason', '')).upper())
                                        is_sell = (t.get('action') == 'SELL' or 'SELL' in str(t.get('reason', '')).upper())
                                        
                                        if is_buy:
                                            lots.append((Decimal(str(t['shares'])), Decimal(str(t['price']))))
                                        elif is_sell:
                                            # Remove from lots (FIFO)
                                            remaining = Decimal(str(t['shares']))
                                            while remaining > 0 and lots:
                                                lot_shares, lot_price = lots[0]
                                                if lot_shares <= remaining:
                                                    remaining -= lot_shares
                                                    lots.popleft()
                                                else:
                                                    lots[0] = (lot_shares - remaining, lot_price)
                                                    remaining = Decimal('0')
                                    
                                    # Calculate P&L for this SELL
                                    sell_shares = Decimal(str(trade_shares))
                                    total_cost = Decimal('0')
                                    remaining = sell_shares
                                    
                                    while remaining > 0 and lots:
                                        lot_shares, lot_price = lots[0]
                                        if lot_shares <= remaining:
                                            total_cost += lot_shares * lot_price
                                            remaining -= lot_shares
                                            lots.popleft()
                                        else:
                                            total_cost += remaining * lot_price
                                            lots[0] = (lot_shares - remaining, lot_price)
                                            remaining = Decimal('0')
                                    
                                    proceeds = Decimal(str(trade_shares * trade_price))
                                    pnl = float(proceeds - total_cost)
                                    
                                except Exception as calc_error:
                                    # If P&L calculation fails, log but continue with pnl=0
                                    import logging
                                    logging.getLogger(__name__).warning(f"Could not calculate P&L for SELL: {calc_error}")
                                    pnl = 0

                            
                            # Insert trade
                            trade_data = {
                                "fund": trade_fund,
                                "ticker": trade_ticker,
                                "action": trade_action,
                                "shares": float(trade_shares),
                                "price": float(trade_price),
                                "cost_basis": float(cost_basis),
                                "pnl": float(pnl),
                                "reason": trade_reason or f"{trade_action} order",
                                "currency": trade_currency,
                                "date": trade_datetime.isoformat()
                            }
                            
                            client.supabase.table("trade_log").insert(trade_data).execute()
                            
                            # Clear data caches to prevent stale data (particularly get_trade_log which is cached forever)
                            st.cache_data.clear()
                            
                            st.success(f"✅ Trade recorded: {trade_action} {trade_shares} shares of {trade_ticker} @ ${trade_price}")
                            st.info("💡 Note: Run portfolio rebuild to update positions based on trade log.")
                            
                        except Exception as e:
                            st.error(f"Error recording trade: {e}")
                
                # Recent trades
                st.divider()
                st.subheader("Recent Trades")
                recent_trades = client.supabase.table("trade_log").select("*").order("date", desc=True).limit(10).execute()
                if recent_trades.data:
                    trades_df = pd.DataFrame(recent_trades.data)
                    display_cols = ["date", "fund", "ticker", "action", "shares", "price", "currency"]
                    available_cols = [c for c in display_cols if c in trades_df.columns]
                    display_dataframe_with_copy(trades_df[available_cols], label="Recent Trades", key_suffix="admin_recent_trades", use_container_width=True)
                else:
                    st.info("No recent trades")
                
                # ===== EMAIL TRADE ENTRY =====
                st.divider()
                st.subheader("📧 Email Trade Entry")
                st.caption("Paste a trade confirmation email to auto-parse and add the trade")
                
                # Initialize session state for parsed trade
                if 'parsed_trade' not in st.session_state:
                    st.session_state.parsed_trade = None
                if 'email_text_input' not in st.session_state:
                    st.session_state.email_text_input = ""
                
                email_fund = st.selectbox("Fund for Email Trade", options=fund_names, key="email_trade_fund")
                
                email_text = st.text_area(
                    "Paste email content here",
                    height=150,
                    placeholder="""Your order has been filled
Symbol: AAPL
Type: Buy
Shares: 10
Average price: US$150.00
Total cost: $1,500.00
Time: December 19, 2025 09:30 EST""",
                    key="email_trade_text"
                )
                
                col_parse, col_clear = st.columns([1, 1])
                
                with col_parse:
                    if st.button("🔍 Parse Email", type="secondary"):
                        if not email_text.strip():
                            st.error("Please paste email content first")
                        else:
                            try:
                                # Import the email parser
                                import sys
                                from pathlib import Path
                                project_root = Path(__file__).parent.parent.parent
                                if str(project_root) not in sys.path:
                                    sys.path.insert(0, str(project_root))
                                
                                from utils.email_trade_parser import EmailTradeParser
                                
                                parser = EmailTradeParser()
                                trade = parser.parse_email_trade(email_text)
                                
                                if trade:
                                    st.session_state.parsed_trade = trade
                                    st.success("✅ Trade parsed successfully!")
                                else:
                                    st.error("❌ Could not parse trade from email. Check the format and try again.")
                                    st.session_state.parsed_trade = None
                                    
                            except Exception as e:
                                st.error(f"Error parsing email: {e}")
                                st.session_state.parsed_trade = None
                
                with col_clear:
                    if st.button("🗑️ Clear", type="secondary"):
                        st.session_state.parsed_trade = None
                        st.rerun()
                
                # Show parsed trade preview
                if st.session_state.parsed_trade:
                    trade = st.session_state.parsed_trade
                    
                    st.markdown("### 📋 Parsed Trade Preview")
                    
                    # Currency validation check
                    canadian_suffixes = ['.TO', '.V', '.CN', '.NE']
                    is_canadian_ticker = any(trade.ticker.upper().endswith(suffix) for suffix in canadian_suffixes)
                    currency_warning = None
                    
                    if is_canadian_ticker and trade.currency.upper() != 'CAD':
                        currency_warning = f"⚠️ **Currency mismatch**: {trade.ticker} appears to be a Canadian stock but currency is {trade.currency}"
                    elif not is_canadian_ticker and trade.currency.upper() == 'CAD':
                        currency_warning = f"ℹ️ **Note**: {trade.ticker} has no Canadian suffix but currency is CAD. Verify this is correct."
                    
                    if currency_warning:
                        st.warning(currency_warning)
                    
                    # Display trade details in a nice format
                    col_left, col_right = st.columns(2)
                    
                    with col_left:
                        st.write(f"**Ticker:** {trade.ticker}")
                        st.write(f"**Action:** {trade.action}")
                        st.write(f"**Shares:** {trade.shares}")
                    
                    with col_right:
                        st.write(f"**Price:** ${trade.price}")
                        st.write(f"**Currency:** {trade.currency}")
                        st.write(f"**Total:** ${trade.cost_basis:.2f}")
                    
                    st.write(f"**Timestamp:** {trade.timestamp}")
                    
                    # Editable currency override
                    override_currency = st.selectbox(
                        "Override Currency (if needed)",
                        options=[trade.currency, "USD" if trade.currency == "CAD" else "CAD"],
                        index=0,
                        key="override_currency"
                    )
                    
                    # Confirm and save button
                    if st.button("✅ Confirm & Save Trade", type="primary"):
                        try:
                            # Use override currency if changed
                            final_currency = override_currency
                            
                            # Ensure ticker exists in securities table
                            ticker_check = client.supabase.table("securities").select("ticker").eq("ticker", trade.ticker).execute()
                            if not ticker_check.data:
                                client.supabase.table("securities").insert({
                                    "ticker": trade.ticker,
                                    "company_name": trade.ticker,
                                    "currency": final_currency
                                }).execute()
                            
                            # Calculate P&L for SELL trades using FIFO
                            final_pnl = float(trade.pnl) if trade.pnl else 0
                            
                            if trade.action == "SELL":
                                try:
                                    from collections import deque
                                    from decimal import Decimal
                                    
                                    # Get existing trades for this ticker (FIFO order)
                                    existing_trades = client.supabase.table("trade_log") \
                                        .select("shares, price, action, reason") \
                                        .eq("fund", email_fund) \
                                        .eq("ticker", trade.ticker) \
                                        .order("date") \
                                        .execute()
                                    
                                    # Build FIFO lot queue
                                    lots = deque()
                                    for t in (existing_trades.data or []):
                                        is_buy = (t.get('action') == 'BUY' or 'BUY' in str(t.get('reason', '')).upper())
                                        is_sell = (t.get('action') == 'SELL' or 'SELL' in str(t.get('reason', '')).upper())
                                        
                                        if is_buy:
                                            lots.append((Decimal(str(t['shares'])), Decimal(str(t['price']))))
                                        elif is_sell:
                                            # Remove from lots (FIFO)
                                            remaining = Decimal(str(t['shares']))
                                            while remaining > 0 and lots:
                                                lot_shares, lot_price = lots[0]
                                                if lot_shares <= remaining:
                                                    remaining -= lot_shares
                                                    lots.popleft()
                                                else:
                                                    lots[0] = (lot_shares - remaining, lot_price)
                                                    remaining = Decimal('0')
                                    
                                    # Calculate P&L for this SELL
                                    sell_shares = Decimal(str(trade.shares))
                                    total_cost = Decimal('0')
                                    remaining = sell_shares
                                    
                                    while remaining > 0 and lots:
                                        lot_shares, lot_price = lots[0]
                                        if lot_shares <= remaining:
                                            total_cost += lot_shares * lot_price
                                            remaining -= lot_shares
                                            lots.popleft()
                                        else:
                                            total_cost += remaining * lot_price
                                            lots[0] = (lot_shares - remaining, lot_price)
                                            remaining = Decimal('0')
                                    
                                    proceeds = Decimal(str(float(trade.shares) * float(trade.price)))
                                    final_pnl = float(proceeds - total_cost)
                                    
                                except Exception as calc_error:
                                    # If P&L calculation fails, log but continue with pnl=0
                                    import logging
                                    logging.getLogger(__name__).warning(f"Could not calculate P&L for email SELL: {calc_error}")
                                    final_pnl = 0
                            
                            # Insert the trade
                            trade_data = {
                                "fund": email_fund,
                                "ticker": trade.ticker,
                                "shares": float(trade.shares),
                                "price": float(trade.price),
                                "cost_basis": float(trade.cost_basis),
                                "pnl": final_pnl,
                                "reason": trade.reason or f"EMAIL TRADE - {trade.action}",
                                "currency": final_currency,
                                "date": trade.timestamp.isoformat()
                            }

                            
                            client.supabase.table("trade_log").insert(trade_data).execute()
                            
                            st.toast(f"✅ Trade saved: {trade.action} {trade.shares} {trade.ticker} @ ${trade.price}", icon="✅")
                            
                            # Clear the parsed trade
                            st.session_state.parsed_trade = None
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error saving trade: {e}")
                    
        except Exception as e:
            st.error(f"Error loading trade entry: {e}")

# Tab 7: Contributions
with tab7:
    st.header("💰 Contribution Management")
    st.caption("Manage investor records and transaction history")
    
    client = get_supabase_client()
    if not client:
        st.error("Failed to connect to database")
    else:
        try:
            # Get available funds
            funds_result = client.supabase.table("funds").select("name").order("name").execute()
            fund_names = [row['name'] for row in funds_result.data] if funds_result.data else []
            
            if not fund_names:
                st.warning("No funds available. Create a fund first in Fund Management.")
            else:
                # 1. Global Selectors
                col_ctrl1, col_ctrl2 = st.columns([1, 2])
                with col_ctrl1:
                    selected_fund = st.selectbox("Select Fund", options=fund_names, key="main_contrib_fund")
                
                # Get existing contributors for this fund
                contributors_query = client.supabase.table("fund_contributions").select("contributor").eq("fund", selected_fund).execute()
                all_contributors = sorted(list(set([r['contributor'] for r in contributors_query.data if r.get('contributor')]))) if contributors_query.data else []
                
                with col_ctrl2:
                    selected_contributor = st.selectbox(
                        "Select Contributor", 
                        options=[""] + all_contributors, 
                        format_func=lambda x: "Choose a contributor..." if x == "" else x,
                        key="main_selected_contributor"
                    )

                if selected_contributor:
                    st.divider()
                    
                    # 2. Contributor Overview & Summary
                    summary_result = client.supabase.table("contributor_ownership").select("*").eq("fund", selected_fund).eq("contributor", selected_contributor).maybe_single().execute()
                    
                    if summary_result.data:
                        s = summary_result.data
                        st.subheader(f"👤 {selected_contributor}")
                        
                        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                        col_m1.metric("Net Capital", f"${s['net_contribution']:,.2f}")
                        col_m2.metric("Contributed", f"${s['total_contributions']:,.2f}")
                        col_m3.metric("Withdrawn", f"${s['total_withdrawals']:,.2f}")
                        col_m4.metric("Transactions", s['transaction_count'])
                        
                        st.caption(f"📧 Email: {s.get('email', 'No email linked')}")
                    
                    # 3. Editable Transaction History
                    st.markdown("### 📓 Transaction History")
                    st.caption("Edit values directly in the table or delete rows. Changes are saved when you click 'Save Changes'.")
                    
                    # Fetch records
                    records_query = client.supabase.table("fund_contributions")\
                        .select("*")\
                        .eq("fund", selected_fund)\
                        .eq("contributor", selected_contributor)\
                        .order("timestamp", desc=True)\
                        .execute()
                    
                    if records_query.data:
                        records_df = pd.DataFrame(records_query.data)
                        # Keep ID for updates but hide it
                        # Convert timestamp to datetime for editor
                        records_df['timestamp'] = pd.to_datetime(records_df['timestamp'], format='ISO8601')
                        
                        edited_data = st.data_editor(
                            records_df,
                            column_config={
                                "id": None, # Hide ID
                                "fund": None, # Hide fund (redundant)
                                "contributor": None, # Hide contributor (redundant)
                                "email": None, # Hide email (managed separately)
                                "timestamp": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                                "contribution_type": st.column_config.SelectboxColumn("Type", options=["CONTRIBUTION", "WITHDRAWAL"]),
                                "amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f", min_value=0),
                                "notes": st.column_config.TextColumn("Notes", width="large"),
                                "created_at": None,
                                "updated_at": None,
                                "contributor_id": None,
                                "fund_id": None
                            },
                            num_rows="dynamic",
                            use_container_width=True,
                            key=f"editor_{selected_fund}_{selected_contributor}"
                        )
                        
                        # Save Changes Button
                        if st.button("💾 Save Changes", type="primary", key=f"save_{selected_fund}_{selected_contributor}"):
                            # Handle state changes from data_editor
                            editor_key = f"editor_{selected_fund}_{selected_contributor}"
                            state = st.session_state.get(editor_key)
                            
                            # Debugging: check what the state looks like
                            # st.write(f"DEBUG state type: {type(state)}, state: {state}") # Uncomment to debug
                            
                            # data_editor stores changes as a dict with 'edited_rows', 'added_rows', 'deleted_rows'
                            if state is not None and isinstance(state, dict):
                                edits = state.get("edited_rows", {})
                                deletes = state.get("deleted_rows", [])
                                adds = state.get("added_rows", [])
                                
                                if not edits and not deletes and not adds:
                                    st.warning("No changes detected. Make edits in the table first, then click Save.")
                                else:
                                    try:
                                        # Process deletes
                                        for idx in deletes:
                                            row_id = records_df.iloc[idx]['id']
                                            client.supabase.table("fund_contributions").delete().eq("id", row_id).execute()
                                        
                                        # Process edits
                                        for idx, changes in edits.items():
                                            row_id = records_df.iloc[int(idx)]['id']
                                            # Only include changed fields
                                            update_payload = {}
                                            if 'amount' in changes: update_payload['amount'] = float(changes['amount'])
                                            if 'contribution_type' in changes: update_payload['contribution_type'] = changes['contribution_type']
                                            if 'notes' in changes: update_payload['notes'] = changes['notes']
                                            if 'timestamp' in changes: 
                                                # Handle datetime object or string
                                                ts = changes['timestamp']
                                                update_payload['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else ts
                                            
                                            if update_payload:
                                                client.supabase.table("fund_contributions").update(update_payload).eq("id", row_id).execute()
                                        
                                        # Process adds (quick add via table)
                                        # Try to get reference IDs from first existing record
                                        # Use .item() to convert from numpy.int64 to native Python int
                                        ref_fund_id = records_df.iloc[0]['fund_id'] if not records_df.empty and 'fund_id' in records_df.columns else None
                                        if hasattr(ref_fund_id, 'item'): ref_fund_id = ref_fund_id.item()
                                        
                                        ref_contributor_id = records_df.iloc[0]['contributor_id'] if not records_df.empty and 'contributor_id' in records_df.columns else None
                                        if hasattr(ref_contributor_id, 'item'): ref_contributor_id = ref_contributor_id.item()
                                        
                                        ref_email = records_df.iloc[0]['email'] if not records_df.empty else None
                                        
                                        # Fallback if no records exist (shouldn't happen here but for safety)
                                        if not ref_fund_id:
                                            f_lookup = client.supabase.table("funds").select("id").eq("name", selected_fund).maybe_single().execute()
                                            if f_lookup.data: ref_fund_id = int(f_lookup.data['id'])
                                        
                                        if not ref_contributor_id:
                                            c_lookup = client.supabase.table("contributors").select("id").eq("name", selected_contributor).execute()
                                            if c_lookup.data: ref_contributor_id = int(c_lookup.data[0]['id'])

                                        for row in adds:
                                            if 'amount' in row:
                                                new_record = {
                                                    "fund": selected_fund,
                                                    "contributor": selected_contributor,
                                                    "email": ref_email,
                                                    "amount": float(row.get('amount', 0)),
                                                    "contribution_type": row.get('contribution_type') or 'CONTRIBUTION',
                                                    "timestamp": row.get('timestamp', datetime.now().isoformat()),
                                                    "notes": row.get('notes') or f"Added via management table"
                                                }
                                                # Include IDs if we have them
                                                if ref_fund_id: new_record["fund_id"] = ref_fund_id
                                                if ref_contributor_id: new_record["contributor_id"] = ref_contributor_id
                                                
                                                client.supabase.table("fund_contributions").insert(new_record).execute()
                                        
                                        # Clear relevant caches so metrics update immediately
                                        import logging
                                        logging.getLogger(__name__).info(f"Cache cleared after contribution record updates for {selected_contributor}")
                                        st.cache_data.clear()
                                        
                                        st.toast(f"✅ Records successfully updated for {selected_contributor}!", icon="✅")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error saving changes: {e}")
                            else:
                                st.warning("Could not retrieve editor state. Please try making your edits again.")

                    
                    st.divider()
                    
                    # 4. Profile Management & Actions
                    with st.expander("🛠️ Manage Contributor Profile"):
                        col_p1, col_p2 = st.columns(2)
                        
                        with col_p1:
                            st.markdown("#### Rename Contributor")
                            new_name = st.text_input("New Name", value=selected_contributor)
                            if st.button("Update Name", use_container_width=True):
                                if new_name and new_name != selected_contributor:
                                    client.supabase.table("fund_contributions").update({"contributor": new_name}).eq("contributor", selected_contributor).execute()
                                    # Clear caches
                                    import logging
                                    logging.getLogger(__name__).info(f"Cache cleared after renaming contributor {selected_contributor} to {new_name}")
                                    st.cache_data.clear()
                                    st.toast(f"✅ Renamed to {new_name}", icon="✅")
                                    st.rerun()
                        
                        with col_p2:
                            st.markdown("#### Update Email")
                            current_email = s.get('email', '') if summary_result.data else ""
                            new_email = st.text_input("New Email", value=current_email)
                            if st.button("Update Email", use_container_width=True):
                                client.supabase.table("fund_contributions").update({"email": new_email}).eq("contributor", selected_contributor).execute()
                                # Clear caches
                                import logging
                                logging.getLogger(__name__).info(f"Cache cleared after email update for {selected_contributor}")
                                st.cache_data.clear()
                                st.toast(f"✅ Email updated to {new_email}", icon="✅")
                                st.rerun()
                
                else:
                    # 5. Add New Contributor Section (when none selected)
                    st.info("Choose an existing contributor above or add a new one below.")
                    st.divider()
                    st.subheader("➕ Add New Contributor")
                    
                    with st.form("new_contributor_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            new_name = st.text_input("Contributor Name*", placeholder="e.g., John Smith")
                            new_email = st.text_input("Email", placeholder="email@example.com")
                        with col2:
                            new_amount = st.number_input("Initial Amount ($)*", min_value=0.01, step=100.0)
                            new_type = st.selectbox("Transaction Type", options=["CONTRIBUTION", "WITHDRAWAL"])
                        
                        new_date = st.date_input("Date", value=datetime.now())
                        new_notes = st.text_area("Notes", placeholder="Optional details...")
                        
                        if st.form_submit_button("Record Initial Contribution", type="primary"):
                            if not new_name:
                                st.error("Name is required")
                            else:
                                try:
                                    # 1. Get Fund ID
                                    fund_id = None
                                    fund_lookup = client.supabase.table("funds").select("id").eq("name", selected_fund).maybe_single().execute()
                                    if fund_lookup.data:
                                        fund_id = int(fund_lookup.data['id'])
                                    
                                    # 2. Get or Create Contributor ID
                                    contributor_id = None
                                    if new_email:
                                        # Try by email first
                                        c_lookup = client.supabase.table("contributors").select("id").eq("email", new_email).maybe_single().execute()
                                        if c_lookup.data:
                                            contributor_id = int(c_lookup.data['id'])
                                    
                                    if not contributor_id:
                                        # Try by name if no email match
                                        c_lookup = client.supabase.table("contributors").select("id").eq("name", new_name).execute()
                                        if c_lookup.data:
                                            contributor_id = c_lookup.data[0]['id']
                                    
                                    if not contributor_id:
                                        # Create new contributor record
                                        new_c = client.supabase.table("contributors").insert({
                                            "name": new_name,
                                            "email": new_email if new_email else None
                                        }).execute()
                                        if new_c.data:
                                            contributor_id = int(new_c.data[0]['id'])

                                    # 3. Final Insert
                                    insert_payload = {
                                        "fund": selected_fund,
                                        "contributor": new_name,
                                        "email": new_email if new_email else None,
                                        "amount": float(new_amount),
                                        "contribution_type": new_type,
                                        "timestamp": datetime.combine(new_date, datetime.min.time()).isoformat(),
                                        "notes": new_notes if new_notes else None
                                    }
                                    if fund_id: insert_payload["fund_id"] = fund_id
                                    if contributor_id: insert_payload["contributor_id"] = contributor_id

                                    client.supabase.table("fund_contributions").insert(insert_payload).execute()
                                    
                                    # Clear relevant caches so metrics update immediately
                                    import logging
                                    logging.getLogger(__name__).info(f"Cache cleared after adding new contributor {new_name}")
                                    st.cache_data.clear()
                                    
                                    st.toast(f"✅ Welcome {new_name}! First {new_type.lower()} recorded.", icon="✅")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error adding contributor: {e}")
                
                # 6. All Contributions View
                st.divider()
                st.subheader("📊 All Contributions Overview")
                st.caption("View all contribution records across all contributors for this fund")
                
                view_all_fund = st.selectbox("View Fund", options=fund_names, key="view_all_fund", index=fund_names.index(selected_fund) if selected_fund in fund_names else 0)
                
                # Fetch all contributions for the selected fund
                all_contribs_query = client.supabase.table("fund_contributions")\
                    .select("*")\
                    .eq("fund", view_all_fund)\
                    .order("timestamp", desc=True)\
                    .execute()
                
                if all_contribs_query.data:
                    all_df = pd.DataFrame(all_contribs_query.data)
                    all_df['timestamp'] = pd.to_datetime(all_df['timestamp'], format='ISO8601')
                    
                    # Display summary metrics
                    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                    total_contribs = all_df[all_df['contribution_type'] == 'CONTRIBUTION']['amount'].sum()
                    total_withdrawals = all_df[all_df['contribution_type'] == 'WITHDRAWAL']['amount'].sum()
                    col_s1.metric("Total Records", len(all_df))
                    col_s2.metric("Total Contributions", f"${total_contribs:,.2f}")
                    col_s3.metric("Total Withdrawals", f"${total_withdrawals:,.2f}")
                    col_s4.metric("Net", f"${total_contribs - total_withdrawals:,.2f}")
                    
                    # Display editable table
                    edited_all_df = st.data_editor(
                        all_df[['id', 'timestamp', 'contributor', 'contribution_type', 'amount', 'notes', 'email']],
                        column_config={
                            "id": None,  # Hide ID
                            "timestamp": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
                            "contributor": st.column_config.TextColumn("Contributor", disabled=True),
                            "contribution_type": st.column_config.TextColumn("Type", disabled=True),
                            "amount": st.column_config.NumberColumn("Amount ($)", format="$%.2f", disabled=True),
                            "notes": st.column_config.TextColumn("Notes", width="large"),
                            "email": st.column_config.TextColumn("Email", disabled=True)
                        },
                        use_container_width=True,
                        hide_index=True,
                        key=f"all_contribs_editor_{view_all_fund}"
                    )
                    
                    # Save button for notes updates
                    if st.button("💾 Save Changes", key=f"save_all_notes_{view_all_fund}"):
                        editor_state = st.session_state.get(f"all_contribs_editor_{view_all_fund}")
                        if editor_state and isinstance(editor_state, dict):
                            edits = editor_state.get("edited_rows", {})
                            if edits:
                                try:
                                    for idx, changes in edits.items():
                                        row_id = all_df.iloc[int(idx)]['id']
                                        # Convert numpy types to native Python
                                        if hasattr(row_id, 'item'):
                                            row_id = row_id.item()
                                        
                                        update_payload = {}
                                        if 'notes' in changes:
                                            update_payload['notes'] = changes['notes']
                                        if 'timestamp' in changes:
                                            ts = changes['timestamp']
                                            update_payload['timestamp'] = ts.isoformat() if hasattr(ts, 'isoformat') else ts
                                        
                                        if update_payload:
                                            client.supabase.table("fund_contributions").update(update_payload).eq("id", row_id).execute()
                                    
                                    # Clear caches
                                    import logging
                                    logging.getLogger(__name__).info(f"Cache cleared after notes/timestamp updates in All Contributions view for {view_all_fund}")
                                    st.cache_data.clear()
                                    
                                    st.toast("✅ Changes saved successfully!", icon="✅")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error saving changes: {e}")
                            else:
                                st.warning("No changes detected.")
                    
                    # Download button
                    csv_data = all_df[['timestamp', 'contributor', 'contribution_type', 'amount', 'notes', 'email']].to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv_data,
                        file_name=f"{view_all_fund}_contributions_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info(f"No contributions found for {view_all_fund}")

        except Exception as e:
            st.error(f"Error loading contributions management: {e}")
            import traceback
            st.code(traceback.format_exc())

# Tab 8: Logs
with tab8:
    st.header("📋 Application Logs")
    st.caption("View recent application logs with filtering")
    
    try:
        from log_handler import read_logs_from_file, log_message
        import os
        
        # Controls row
        col1, col2, col3, col4, col5, col6 = st.columns([1, 1, 1, 1, 2, 1])
        
        with col1:
            auto_refresh = st.checkbox("🔄 Auto-refresh", value=False, help="Refresh logs every 5 seconds")
        
        with col2:
            level_filter = st.selectbox(
                "Level",
                options=["All", "DEBUG", "PERF", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=0  # Default to "All"
            )
        
        with col3:
            num_logs = st.selectbox(
                "Show",
                options=[50, 100, 200, 500, 1000],
                index=1  # Default to 100
            )
        
        with col4:
            sort_order = st.selectbox(
                "Sort",
                options=["Newest First", "Oldest First"],
                index=0  # Default to newest first
            )
        
        with col5:
            search_text = st.text_input("🔍 Search", placeholder="Filter by text...", label_visibility="collapsed")
        
        with col6:
            if st.button("🗑️ Clear Logs"):
                # Clear log file content
                try:
                    log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'app.log')
                    if os.path.exists(log_file):
                        with open(log_file, 'w', encoding='utf-8') as f:
                            f.write("")
                    st.toast("✅ Logs cleared", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear logs: {e}")
        
        # Get logs with filters (with spinner for better UX)
        with st.spinner("Loading logs..."):
            level = None if level_filter == "All" else level_filter
            
            # Use file-based reader (now optimized to read from end)
            logs = read_logs_from_file(
                n=num_logs,
                level=level,
                search=search_text if search_text else None
            )
            
            # Apply sort order (default from file is oldest first)
            if sort_order == "Newest First" and logs:
                logs = list(reversed(logs))
        
        # Display logs in a code block for better formatting
        if logs:
            st.caption(f"Showing {len(logs)} log entries ({sort_order.lower()})")
            
            # Create formatted log output
            log_lines = []
            for log in logs:
                timestamp = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                level_str = log['level'].ljust(8)
                module = log['module'][:30].ljust(30)  # Limit module name width
                message = log['message']
                
                # Add emoji indicators for levels
                emoji = {
                    'DEBUG': '🔍',
                    'INFO': 'ℹ️',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'CRITICAL': '🔥'
                }.get(log['level'], '•')
                
                log_lines.append(f"{emoji} {timestamp} | {level_str} | {module} | {message}")
            
            # Display in code block
            log_text = "\n".join(log_lines)
            st.code(log_text, language=None)
            
            # Download button
            if st.download_button(
                label="⬇️ Download Logs",
                data=log_text,
                file_name=f"app_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            ):
                st.success("Logs downloaded!")
        else:
            st.info("No logs found matching the filters")
        
        # Auto-refresh
        if auto_refresh:
            import time
            time.sleep(5)
            st.rerun()
            
    except ImportError:
        st.error("❌ Log handler not available")
        st.info("The logging module may not be initialized. Check streamlit_app.py configuration.")
    except Exception as e:
        st.error(f"Error loading logs: {e}")


# Tab 9: AI Settings
with tab9:
    st.header("🤖 AI Assistant Settings")
    st.caption("Configure Ollama AI integration and performance parameters")
    
    try:
        from ollama_client import check_ollama_health, list_available_models, get_ollama_client
        
        # Check Ollama connection
        st.subheader("Connection Status")
        if check_ollama_health():
            st.success("✅ Ollama API is reachable")
            
            # List available models
            models = list_available_models()
            if models:
                st.info(f"Available models: {', '.join(models)}")
            else:
                st.warning("No models found. Pull a model first (e.g., `ollama pull llama3`)")
        else:
            st.error("❌ Cannot connect to Ollama API")
            st.info("Make sure Ollama is running and accessible at the configured URL.")
        
        st.markdown("---")
        
        # AI Settings Configuration
        st.subheader("Configuration")
        
        # Get current settings from environment or database
        ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        enabled = os.getenv("OLLAMA_ENABLED", "true").lower() == "true"
        
        # Get default model from database, fallback to env var
        try:
            from settings import get_system_setting, set_system_setting
            default_model = get_system_setting("ai_default_model", os.getenv("OLLAMA_MODEL", "llama3"))
        except Exception as e:
            st.warning(f"Could not load default model from database: {e}")
            default_model = os.getenv("OLLAMA_MODEL", "llama3")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### Base Settings")
            new_base_url = st.text_input(
                "Ollama Base URL",
                value=ollama_base_url,
                help="URL where Ollama API is accessible (e.g., http://localhost:11434)",
                disabled=True  # Read-only, set via environment
            )
            
            # Model selection dropdown (populated from available models)
            if check_ollama_health() and models:
                # Ensure current default is in the list
                model_options = models if default_model in models else [default_model] + models
                current_index = model_options.index(default_model) if default_model in model_options else 0
                
                new_default_model = st.selectbox(
                    "Default AI Model",
                    options=model_options,
                    index=current_index,
                    help="Default model for new users and system prompts"
                )
                
                # Save button for model selection
                if new_default_model != default_model:
                    if st.button("💾 Save Default Model", type="primary"):
                        try:
                            from settings import set_system_setting
                            if set_system_setting("ai_default_model", new_default_model, "Default AI model for new users"):
                                st.toast(f"✅ Default model set to {new_default_model}", icon="✅")
                                st.rerun()
                            else:
                                st.error("Failed to save model setting")
                        except Exception as e:
                            st.error(f"Error saving model: {e}")
            else:
                st.text_input(
                    "Default Model",
                    value=default_model,
                    help="Default model name (Ollama not connected - cannot list models)",
                    disabled=True
                )
            
                new_enabled = st.checkbox(
                "AI Assistant Enabled",
                value=enabled,
                help="Enable or disable AI assistant globally",
                disabled=True  # Read-only, set via environment
            )
            
            # Summarizing model selection
            from settings import get_summarizing_model, set_system_setting
            summarizing_model = get_summarizing_model()
            
            if check_ollama_health() and models:
                # Ensure current summarizing model is in the list
                summarizing_options = models if summarizing_model in models else [summarizing_model] + models
                summarizing_index = summarizing_options.index(summarizing_model) if summarizing_model in summarizing_options else 0
                
                new_summarizing_model = st.selectbox(
                    "Summarizing Model",
                    options=summarizing_options,
                    index=summarizing_index,
                    help="Model used for generating article summaries (default: granite3.3:8b)"
                )
                
                # Save button for summarizing model selection
                if new_summarizing_model != summarizing_model:
                    if st.button("💾 Save Summarizing Model", type="primary", key="save_summarizing_model"):
                        try:
                            if set_system_setting("ai_summarizing_model", new_summarizing_model, "Model for generating article summaries"):
                                st.toast(f"✅ Summarizing model set to {new_summarizing_model}", icon="✅")
                                st.rerun()
                            else:
                                st.error("Failed to save summarizing model setting")
                        except Exception as e:
                            st.error(f"Error saving summarizing model: {e}")
            else:
                st.text_input(
                    "Summarizing Model",
                    value=summarizing_model,
                    help="Model name for summarization (Ollama not connected - cannot list models)",
                    disabled=True
                )
        
        with col2:
            st.markdown("##### Model-Specific Settings")
            
            # Get model-specific defaults from JSON config
            client = get_ollama_client()
            if client and default_model:
                model_settings = client.get_model_settings(default_model)
                model_desc = client.get_model_description(default_model)
                
                if model_desc:
                    st.caption(f"ℹ️ {model_desc}")
                
                # Load any database overrides
                from settings import get_system_setting
                
                # Temperature
                db_temp = get_system_setting(f"model_{default_model}_temperature", default=None)
                default_temp = db_temp if db_temp is not None else model_settings.get('temperature', 0.7)
                
                new_temperature = st.slider(
                    "Temperature",
                    min_value=0.0,
                    max_value=2.0,
                    value=float(default_temp),
                    step=0.1,
                    help=f"Model temperature (JSON default: {model_settings.get('temperature', 0.7)})"
                )
                
                # Context window
                db_ctx = get_system_setting(f"model_{default_model}_num_ctx", default=None)
                default_ctx = db_ctx if db_ctx is not None else model_settings.get('num_ctx', 4096)
                
                new_num_ctx = st.number_input(
                    "Context Window (num_ctx)",
                    min_value=512,
                    max_value=32768,
                    value=int(default_ctx),
                    step=512,
                    help=f"Context window size in tokens (JSON default: {model_settings.get('num_ctx', 4096)})"
                )
                
                # Max output tokens
                db_predict = get_system_setting(f"model_{default_model}_num_predict", default=None)
                default_predict = db_predict if db_predict is not None else model_settings.get('num_predict', 2048)
                
                new_num_predict = st.number_input(
                    "Max Output Tokens (num_predict)",
                    min_value=256,
                    max_value=8192,
                    value=int(default_predict),
                    step=256,
                    help=f"Maximum tokens in response (JSON default: {model_settings.get('num_predict', 2048)})"
                )
                
                # Save button for model-specific settings
                if st.button("💾 Save Model Settings", type="primary", key="save_model_settings"):
                    try:
                        from settings import set_system_setting
                        success = True
                        
                        # Save temperature
                        if not set_system_setting(f"model_{default_model}_temperature", new_temperature, f"Temperature override for {default_model}"):
                            success = False
                        
                        # Save context window
                        if not set_system_setting(f"model_{default_model}_num_ctx", new_num_ctx, f"Context window override for {default_model}"):
                            success = False
                        
                        # Save max tokens
                        if not set_system_setting(f"model_{default_model}_num_predict", new_num_predict, f"Max tokens override for {default_model}"):
                            success = False
                        
                        if success:
                            st.toast(f"✅ Settings saved for {default_model}", icon="✅")
                            st.rerun()
                        else:
                            st.error("Failed to save some settings")
                    except Exception as e:
                        st.error(f"Error saving settings: {e}")
                
                # Reset to defaults button
                if st.button("🔄 Reset to JSON Defaults", key="reset_model_settings"):
                    try:
                        from streamlit_utils import get_supabase_client
                        client_db = get_supabase_client()
                        if client_db:
                            # Delete overrides
                            client_db.supabase.table('system_settings').delete().eq('key', f"model_{default_model}_temperature").execute()
                            client_db.supabase.table('system_settings').delete().eq('key', f"model_{default_model}_num_ctx").execute()
                            client_db.supabase.table('system_settings').delete().eq('key', f"model_{default_model}_num_predict").execute()
                            st.toast(f"✅ Reset {default_model} to JSON defaults", icon="✅")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error resetting: {e}")
            else:
                st.info("Select a model to configure settings")
            
            st.markdown("---")
            st.markdown("##### Connection Settings")
            
            new_timeout = st.number_input(
                "Request Timeout (seconds)",
                min_value=30,
                max_value=300,
                value=timeout,
                step=10,
                help="Timeout for AI requests"
            )
        
        st.markdown("---")
        st.info("ℹ️ **Configuration Priority:**\n"
                "1. **Docker environment variables** (set in `.woodpecker.yml` or Woodpecker secrets)\n"
                "2. **`.env` file** (for local development - loaded by python-dotenv)\n"
                "3. **Python defaults** (hardcoded fallbacks)\n\n"
                "To change settings:\n"
                "- **Production**: Set Woodpecker secrets (`ollama_base_url`, `ollama_model`, `ollama_enabled`) or edit `.woodpecker.yml`\n"
                "- **Local dev**: Create `web_dashboard/.env` file from `env.example`\n"
                "- **Model-specific settings**: Configure below (stored in database)")
        
        # Show current environment variables
        with st.expander("📋 Current Environment Variables (Read-Only)"):
            st.code(f"""OLLAMA_BASE_URL={ollama_base_url}
OLLAMA_MODEL={default_model}
OLLAMA_TIMEOUT={timeout}
OLLAMA_ENABLED={enabled}""")
        
        # Domain Health Monitor
        st.markdown("---")
        st.markdown("##### 📊 Domain Health Monitor")
        st.caption("Track extraction success rates and identify problematic domains")
        
        try:
            from research_domain_health import DomainHealthTracker
            from settings import get_system_setting
            
            tracker = DomainHealthTracker()
            unhealthy_domains = tracker.get_unhealthy_domains(min_failures=1)
            threshold = get_system_setting("auto_blacklist_threshold", default=4)
            
            if unhealthy_domains:
                # Build table data
                health_data = []
                for record in unhealthy_domains:
                    domain = record.get('domain', '')
                    total_attempts = record.get('total_attempts', 0)
                    total_successes = record.get('total_successes', 0)
                    consecutive_failures = record.get('consecutive_failures', 0)
                    auto_blacklisted = record.get('auto_blacklisted', False)
                    last_failure_reason = record.get('last_failure_reason', 'unknown')
                    
                    # Calculate success rate
                    success_rate = (total_successes / total_attempts * 100) if total_attempts > 0 else 0
                    
                    # Determine health status
                    if auto_blacklisted:
                        status = "🔴 Auto-blacklisted"
                    elif consecutive_failures >= threshold:
                        status = "🔴 Critical"
                    elif consecutive_failures >= threshold - 1:
                        status = "🟡 Warning"
                    else:
                        status = "🟢 Monitoring"
                    
                    health_data.append({
                        "Domain": domain,
                        "Attempts": total_attempts,
                        "Success Rate": f"{success_rate:.0f}%",
                        "Consecutive Failures": f"{consecutive_failures}/{threshold}",
                        "Last Failure": last_failure_reason,
                        "Status": status
                    })
                
                # Display as DataFrame
                import pandas as pd
                health_df = pd.DataFrame(health_data)
                
                st.dataframe(
                    health_df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Domain": st.column_config.TextColumn("Domain", width="medium"),
                        "Attempts": st.column_config.NumberColumn("Attempts", width="small"),
                        "Success Rate": st.column_config.TextColumn("Success Rate", width="small"),
                        "Consecutive Failures": st.column_config.TextColumn("Consecutive Failures", width="small"),
                        "Last Failure": st.column_config.TextColumn("Last Failure", width="medium"),
                        "Status": st.column_config.TextColumn("Status", width="medium")
                    }
                )
                
                st.caption(f"ℹ️ Auto-blacklist threshold: {threshold} consecutive failures")
                
            else:
                st.success("✅ All domains are healthy!")
                st.caption("No domains with extraction failures found.")
        
        except Exception as e:
            st.warning(f"Could not load domain health data: {e}")
            st.caption("Make sure the research_domain_health table exists (run migration 10_domain_health_tracking.sql)")
        
        # Research Domain Blacklist Management
        st.markdown("---")
        st.markdown("##### 🚫 Research Domain Blacklist")
        st.caption("Domains to skip during market research article extraction")
        
        try:
            from settings import get_research_domain_blacklist, set_system_setting
            
            current_blacklist = get_research_domain_blacklist()
            
            # Display current blacklist
            if current_blacklist:
                st.write("**Current Blacklisted Domains:**")
                for idx, domain in enumerate(current_blacklist):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.text(f"• {domain}")
                    with col2:
                        if st.button("❌", key=f"remove_domain_{idx}", help=f"Remove {domain}"):
                            try:
                                updated_list = [d for d in current_blacklist if d != domain]
                                if set_system_setting("research_domain_blacklist", updated_list, 
                                                     "Domains to skip during market research article extraction (JSON array)"):
                                    st.toast(f"✅ Removed {domain} from blacklist", icon="✅")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to remove {domain}")
                            except Exception as e:
                                st.error(f"Error removing domain: {e}")
            else:
                st.info("No domains blacklisted")
            
            # Add new domain
            st.write("**Add New Domain:**")
            col_add1, col_add2 = st.columns([3, 1])
            with col_add1:
                new_domain = st.text_input(
                    "Domain",
                    placeholder="example.com",
                    key="new_blacklist_domain",
                    label_visibility="collapsed"
                )
            with col_add2:
                if st.button("➕ Add", type="primary", use_container_width=True):
                    if not new_domain:
                        st.error("Please enter a domain")
                    elif new_domain in current_blacklist:
                        st.warning(f"{new_domain} is already blacklisted")
                    else:
                        try:
                            updated_list = current_blacklist + [new_domain.strip().lower()]
                            if set_system_setting("research_domain_blacklist", updated_list,
                                                 "Domains to skip during market research article extraction (JSON array)"):
                                st.toast(f"✅ Added {new_domain} to blacklist", icon="✅")
                                st.rerun()
                            else:
                                st.error("Failed to add domain")
                        except Exception as e:
                            st.error(f"Error adding domain: {e}")
            
            # Show stats from last job run
            try:
                from streamlit_utils import get_supabase_client
                client_stats = get_supabase_client()
                if client_stats:
                    # Get last market_research job execution
                    job_result = client_stats.supabase.table("job_executions") \
                        .select("message, completed_at") \
                        .eq("job_id", "market_research") \
                        .eq("success", True) \
                        .order("completed_at", desc=True) \
                        .limit(1) \
                        .execute()
                    
                    if job_result.data and len(job_result.data) > 0:
                        last_job = job_result.data[0]
                        message = last_job.get("message", "")
                        # Parse message like: "Processed 5 articles: 3 saved, 1 skipped, 1 blacklisted"
                        if "blacklisted" in message:
                            st.caption(f"📊 Last run: {message}")
            except Exception:
                pass  # Don't fail if stats unavailable
        
        except Exception as e:
            st.error(f"Error loading blacklist settings: {e}")
        
        # Test connection button
        st.markdown("---")
        if st.button("🔄 Test Connection", use_container_width=True):
            if check_ollama_health():
                st.success("✅ Connection successful!")
            else:
                st.error("❌ Connection failed. Check the base URL and ensure Ollama is running.")
        
    except ImportError as e:
        st.error(f"Error importing Ollama client: {e}")
        st.info("Make sure ollama_client.py is available.")
    except Exception as e:
        st.error(f"Error loading AI settings: {e}")
        import traceback
        st.code(traceback.format_exc())

# Display Streamlit version at the bottom of the page
st.markdown("---")
try:
    streamlit_version = st.__version__
    st.caption(f"Streamlit v{streamlit_version}")
except AttributeError:
    # Fallback if __version__ is not available
    try:
        import pkg_resources
        streamlit_version = pkg_resources.get_distribution("streamlit").version
        st.caption(f"Streamlit v{streamlit_version}")
    except Exception:
        st.caption("Streamlit version unavailable")