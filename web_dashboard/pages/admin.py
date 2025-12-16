#!/usr/bin/env python3
"""
Admin Page for Web Dashboard
Centralized admin functionality for managing users, funds, scheduled tasks, and system status
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, is_admin, get_user_email
from streamlit_utils import get_supabase_client

# Page configuration
st.set_page_config(
    page_title="Admin Dashboard",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check authentication
if not is_authenticated():
    st.error("Please log in to access the admin page.")
    st.stop()

# Check admin status
if not is_admin():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Header
st.markdown("# ⚙️ Admin Dashboard")
st.caption(f"Logged in as: {get_user_email()}")

# Display build timestamp (from Woodpecker CI environment variable)
import os
build_timestamp = os.getenv("BUILD_TIMESTAMP")
if build_timestamp:
    st.caption(f"🏷️ Build: {build_timestamp}")
else:
    # Development mode - show current time
    try:
        from zoneinfo import ZoneInfo
        pacific = ZoneInfo("America/Vancouver")
        now = datetime.now(pacific)
        dev_timestamp = now.strftime("%Y-%m-%d %H:%M %Z")
        st.caption(f"🏷️ Build: Development ({dev_timestamp})")
    except (ImportError, Exception):
        st.caption(f"🏷️ Build: Development ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

# Custom page navigation in sidebar
with st.sidebar:
    st.title("Navigation")
    st.markdown("### Pages")
    st.page_link("streamlit_app.py", label="📈 Dashboard", icon="📈")
    st.page_link("pages/admin.py", label="⚙️ Admin", icon="⚙️")
    st.markdown("---")

# Create tabs for different admin sections
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "⏰ Scheduled Tasks",
    "👥 User Management", 
    "🔐 Contributor Access",
    "🏦 Fund Management",
    "📊 System Status",
    "📈 Trade Entry",
    "💰 Contributions",
    "📋 Logs"
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
        # Get all users with their fund assignments
        try:
            # Call the list_users_with_funds SQL function
            result = client.supabase.rpc('list_users_with_funds').execute()
            
            if result.data:
                users_df = pd.DataFrame(result.data)
                
                # Display users table
                st.subheader("All Users")
                st.dataframe(
                    users_df,
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
                                    st.success(f"✅ {result_data.get('message')}")
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
                
                # Get available funds from funds table
                funds_result = client.supabase.table("funds").select("name").order("name").execute()
                available_funds = [row['name'] for row in funds_result.data] if funds_result.data else []
                
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
                                    st.success(f"✅ {result_data.get('message', f'Successfully assigned {fund_name} to {user_email}')}")
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
                                    st.success(f"✅ Successfully removed {remove_fund} from {remove_email}")
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
                # Get all contributors
                all_contributors = client.supabase.table("contributors").select("id, name, email").order("name").execute()
                contributors_list = all_contributors.data if all_contributors.data else []
                
                # Get all users - query user_profiles directly instead of RPC to avoid permission issues
                try:
                    users_result = client.supabase.rpc('list_users_with_funds').execute()
                    users_list = users_result.data if users_result.data else []
                    using_fallback = False
                except Exception as rpc_error:
                    # Fallback: Query user_profiles directly and get funds separately
                    using_fallback = True
                    rpc_error_msg = str(rpc_error)
                    
                    try:
                        # Get user profiles
                        profiles_result = client.supabase.table("user_profiles").select("user_id, email, full_name").execute()
                        profiles = profiles_result.data if profiles_result.data else []
                        
                        # Get user funds for each user
                        users_list = []
                        for profile in profiles:
                            funds_result = client.supabase.table("user_funds").select("fund_name").eq("user_id", profile['user_id']).execute()
                            funds = [f['fund_name'] for f in funds_result.data] if funds_result.data else []
                            users_list.append({
                                'user_id': profile['user_id'],
                                'email': profile['email'],
                                'full_name': profile['full_name'],
                                'funds': funds
                            })
                    except Exception as direct_error:
                        st.error(f"❌ Could not load users via fallback: {direct_error}")
                        st.error(f"Original RPC error: {rpc_error_msg}")
                        users_list = []
                
                # Show fallback warning after loading if we used fallback
                if using_fallback and users_list:
                    st.warning(f"⚠️ Using fallback query (RPC error: {rpc_error_msg[:100]}...). This is expected if the RPC function has permission issues.")
                
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
                                        st.success(f"✅ {result_data.get('message')}")
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
                            st.dataframe(access_df, use_container_width=True)
                            
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
                                                st.success(f"✅ {result_data.get('message')}")
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
        # Load all funds from the funds table
        try:
            funds_result = client.supabase.table("funds").select("*").order("name").execute()
            fund_names = [row['name'] for row in funds_result.data] if funds_result.data else []
            
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
                    fund_info = next((f for f in funds_result.data if f['name'] == fund_name), {})
                    
                    fund_stats.append({
                        "Fund Name": fund_name,
                        "Type": fund_info.get('fund_type', 'N/A'),
                        "Currency": fund_info.get('currency', 'N/A'),
                        "Positions": position_count,
                        "Trades": trade_count_val
                    })
                
                funds_df = pd.DataFrame(fund_stats)
                st.subheader("All Funds")
                st.dataframe(funds_df, use_container_width=True)
            else:
                st.info("No funds found in database")
            
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
                            
                            st.success(f"✅ Fund '{new_fund_name}' created successfully!")
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
                            st.success(f"✅ Fund renamed from '{rename_fund}' to '{new_name}'")
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
                            # Clear portfolio_positions
                            client.supabase.table("portfolio_positions").delete().eq("fund", wipe_fund).execute()
                            # Clear trade_log
                            client.supabase.table("trade_log").delete().eq("fund", wipe_fund).execute()
                            # Clear performance_metrics
                            client.supabase.table("performance_metrics").delete().eq("fund", wipe_fund).execute()
                            # Reset cash_balances to 0
                            client.supabase.table("cash_balances").update({"amount": 0}).eq("fund", wipe_fund).execute()
                            
                            st.success(f"✅ All data for '{wipe_fund}' has been wiped. Fund and contributions preserved.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error wiping fund data: {e}")
            
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
                            
                            st.success(f"✅ Fund '{delete_fund}' and all its data has been permanently deleted.")
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
                            pnl = 0  # P&L is calculated differently for sells
                            
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
                    st.dataframe(trades_df[available_cols], use_container_width=True)
                else:
                    st.info("No recent trades")
                    
        except Exception as e:
            st.error(f"Error loading trade entry: {e}")

# Tab 7: Contributions
with tab7:
    st.header("💰 Contribution Management")
    st.caption("Add and manage investor contributions")
    
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
                # Add Contribution Section
                st.subheader("➕ Add Contribution/Withdrawal")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    contrib_fund = st.selectbox("Fund", options=fund_names, key="contrib_fund")
                    contrib_type = st.selectbox("Type", options=["CONTRIBUTION", "WITHDRAWAL"], key="contrib_type")
                    contrib_amount = st.number_input("Amount ($)", min_value=0.01, value=1000.0, step=100.0, format="%.2f", key="contrib_amount")
                
                with col2:
                    # Get existing contributors for autocomplete
                    existing_contributors = client.supabase.table("fund_contributions").select("contributor, email").eq("fund", contrib_fund).execute()
                    contributor_names = sorted(list(set([r['contributor'] for r in existing_contributors.data if r.get('contributor')]))) if existing_contributors.data else []
                    
                    contrib_new_or_existing = st.radio("Contributor", ["Existing", "New"], horizontal=True, key="contrib_new_existing")
                    
                    if contrib_new_or_existing == "Existing" and contributor_names:
                        contrib_name = st.selectbox("Select Contributor", options=contributor_names, key="contrib_name_existing")
                        # Get email for selected contributor
                        existing_email = next((r['email'] for r in existing_contributors.data if r['contributor'] == contrib_name and r.get('email')), "")
                        contrib_email = st.text_input("Email", value=existing_email, key="contrib_email_existing")
                    else:
                        contrib_name = st.text_input("Contributor Name", placeholder="e.g., John Smith", key="contrib_name_new")
                        contrib_email = st.text_input("Email", placeholder="email@example.com", key="contrib_email_new")
                
                # Optional fields
                with st.expander("Additional Options", expanded=False):
                    contrib_notes = st.text_area("Notes", placeholder="Optional notes", key="contrib_notes")
                    contrib_date = st.date_input("Date", value=datetime.now(), key="contrib_date")
                
                if st.button("💰 Record Contribution", type="primary"):
                    if not contrib_name:
                        st.error("Please enter a contributor name")
                    elif contrib_amount <= 0:
                        st.error("Amount must be greater than 0")
                    else:
                        try:
                            # Get or create contributor (if email provided)
                            contributor_id = None
                            if contrib_email:
                                try:
                                    contrib_result = client.supabase.table("contributors").select("id").eq("email", contrib_email).maybe_single().execute()
                                    if contrib_result.data:
                                        contributor_id = contrib_result.data['id']
                                    else:
                                        # Create new contributor
                                        new_contrib = client.supabase.table("contributors").insert({
                                            "name": contrib_name,
                                            "email": contrib_email
                                        }).execute()
                                        if new_contrib.data:
                                            contributor_id = new_contrib.data['id']
                                except:
                                    pass  # Contributors table might not exist yet
                            
                            # Get fund_id
                            fund_id = None
                            try:
                                fund_result = client.supabase.table("funds").select("id").eq("name", contrib_fund).maybe_single().execute()
                                if fund_result.data:
                                    fund_id = fund_result.data['id']
                            except:
                                pass  # Funds table might not exist yet
                            
                            contrib_data = {
                                "fund": contrib_fund,  # Keep for backward compatibility
                                "contributor": contrib_name,  # Keep for backward compatibility
                                "email": contrib_email if contrib_email else None,
                                "amount": float(contrib_amount),
                                "contribution_type": contrib_type,
                                "timestamp": datetime.combine(contrib_date, datetime.min.time()).isoformat(),
                                "notes": contrib_notes if contrib_notes else None
                            }
                            
                            # Add new FK columns if available
                            if fund_id:
                                contrib_data["fund_id"] = fund_id
                            if contributor_id:
                                contrib_data["contributor_id"] = contributor_id
                            
                            client.supabase.table("fund_contributions").insert(contrib_data).execute()
                            
                            action_word = "Contribution" if contrib_type == "CONTRIBUTION" else "Withdrawal"
                            st.success(f"✅ {action_word} recorded: ${contrib_amount:,.2f} for {contrib_name}")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error recording contribution: {e}")
                
                st.divider()
                
                # Edit Contributor Section
                st.subheader("✏️ Edit Contributor Info")
                st.caption("Update name or email for an existing contributor across all their records")
                
                if contributor_names:
                    col3, col4 = st.columns(2)
                    
                    with col3:
                        edit_contributor = st.selectbox("Select Contributor to Edit", options=[""] + contributor_names, key="edit_contributor")
                    
                    if edit_contributor:
                        # Get current email
                        current_email = next((r['email'] for r in existing_contributors.data if r['contributor'] == edit_contributor and r.get('email')), "")
                        
                        with col4:
                            new_name = st.text_input("New Name", value=edit_contributor, key="edit_new_name")
                            new_email = st.text_input("New Email", value=current_email or "", key="edit_new_email")
                        
                        if st.button("✏️ Update Contributor", type="secondary"):
                            if not new_name:
                                st.error("Name cannot be empty")
                            else:
                                try:
                                    # Update all records for this contributor across all funds
                                    update_data = {"contributor": new_name}
                                    if new_email:
                                        update_data["email"] = new_email
                                    
                                    client.supabase.table("fund_contributions").update(update_data).eq("contributor", edit_contributor).execute()
                                    
                                    st.success(f"✅ Updated contributor '{edit_contributor}' to '{new_name}'")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating contributor: {e}")
                else:
                    st.info("No contributors found for this fund")
                
                st.divider()
                
                # View Contributors
                st.subheader("👥 Fund Contributors")
                view_fund = st.selectbox("View Fund", options=fund_names, key="view_contrib_fund")
                
                contributors_result = client.supabase.table("contributor_ownership").select("*").eq("fund", view_fund).execute()
                if contributors_result.data:
                    contrib_df = pd.DataFrame(contributors_result.data)
                    st.dataframe(contrib_df, use_container_width=True)
                else:
                    st.info(f"No contributors found for {view_fund}")
                    
        except Exception as e:
            st.error(f"Error loading contributions: {e}")

# Tab 8: Logs
with tab8:
    st.header("📋 Application Logs")
    st.caption("View recent application logs with filtering")
    
    try:
        from log_handler import read_logs_from_file, log_message
        import os
        
        # Controls row
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 2, 1])
        
        with col1:
            auto_refresh = st.checkbox("🔄 Auto-refresh", value=False, help="Refresh logs every 5 seconds")
        
        with col2:
            level_filter = st.selectbox(
                "Level",
                options=["All", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                index=2  # Default to "INFO"
            )
        
        with col3:
            num_logs = st.selectbox(
                "Show",
                options=[50, 100, 200, 500],
                index=1  # Default to 100
            )
        
        with col4:
            search_text = st.text_input("🔍 Search", placeholder="Filter by text...", label_visibility="collapsed")
        
        with col5:
            if st.button("🗑️ Clear Logs"):
                # Clear log file content
                try:
                    log_file = os.path.join(os.path.dirname(__file__), '..', 'logs', 'app.log')
                    if os.path.exists(log_file):
                        with open(log_file, 'w', encoding='utf-8') as f:
                            f.write("")
                    st.success("Logs cleared")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear logs: {e}")
        
        # Get logs with filters
        level = None if level_filter == "All" else level_filter
        
        # Use file-based reader
        logs = read_logs_from_file(
            n=num_logs,
            level=level,
            search=search_text if search_text else None
        )
        
        # Display logs in a code block for better formatting
        if logs:
            st.caption(f"Showing last {len(logs)} log entries")
            
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
