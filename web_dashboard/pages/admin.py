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

# Create tabs for different admin sections
tab1, tab2, tab3, tab4 = st.tabs([
    "⏰ Scheduled Tasks",
    "👥 User Management", 
    "🏦 Fund Management",
    "📊 System Status"
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
                    user_email = st.text_input("User Email", placeholder="user@example.com")
                
                # Get available funds from distinct fund names in portfolio_positions
                funds_result = client.supabase.table("portfolio_positions").select("fund").execute()
                available_funds = sorted(list(set([row['fund'] for row in funds_result.data if row.get('fund')]))) if funds_result.data else []
                
                with col2:
                    fund_name = st.selectbox("Fund Name", options=[""] + available_funds)
                
                if st.button("Assign Fund", type="primary"):
                    if user_email and fund_name:
                        try:
                            assign_result = client.supabase.rpc(
                                'assign_fund_to_user',
                                {'user_email': user_email, 'fund_name': fund_name}
                            ).execute()
                            
                            if assign_result.data:
                                st.success(f"✅ Successfully assigned {fund_name} to {user_email}")
                                st.rerun()
                            else:
                                st.error("Failed to assign fund")
                        except Exception as e:
                            st.error(f"Error assigning fund: {e}")
                    else:
                        st.warning("Please enter both email and fund name")
                
                # Remove fund assignment
                st.subheader("Remove Fund Assignment")
                col3, col4 = st.columns(2)
                
                with col3:
                    remove_email = st.text_input("User Email", key="remove_email", placeholder="user@example.com")
                
                with col4:
                    # Get funds again for remove dropdown
                    remove_funds_result = client.supabase.table("portfolio_positions").select("fund").execute()
                    remove_available_funds = sorted(list(set([row['fund'] for row in remove_funds_result.data if row.get('fund')]))) if remove_funds_result.data else []
                    remove_fund = st.selectbox("Fund Name", options=[""] + remove_available_funds, key="remove_fund")
                
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
                        
                        with col_info:
                            funds_str = ", ".join(row['funds']) if row['funds'] else "None"
                            st.markdown(f"**{row['contributor']}** ({row['email']})")
                            st.caption(f"Funds: {funds_str} | Contribution: ${row['total_contribution']:,.2f}")
                        
                        with col_action:
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
                        
                        st.divider()
            else:
                st.success("✅ All contributors have registered accounts!")
        except Exception as e:
            st.warning(f"Could not load unregistered contributors: {e}")
            st.info("You may need to run the `list_unregistered_contributors` SQL function in Supabase.")

# Tab 3: Fund Management
with tab3:
    st.header("🏦 Fund Management")
    st.caption("Manage funds in the system")
    
    client = get_supabase_client()
    if not client:
        st.error("Failed to connect to database")
    else:
        # List all funds (from distinct fund names in portfolio_positions)
        try:
            # Use raw SQL to get distinct funds efficiently (avoids 1000-row limit issue)
            # First try to get from funds table, fallback to portfolio_positions
            funds_result = client.supabase.table("funds").select("name").execute()
            
            if funds_result.data:
                fund_names = sorted([row['name'] for row in funds_result.data if row.get('name')])
            else:
                # Fallback: get distinct funds from portfolio_positions using RPC or pagination
                # Query with explicit high limit to ensure we get all funds
                all_funds = set()
                offset = 0
                batch_size = 1000
                
                while True:
                    batch = client.supabase.table("portfolio_positions").select("fund").range(offset, offset + batch_size - 1).execute()
                    if not batch.data:
                        break
                    for row in batch.data:
                        if row.get('fund'):
                            all_funds.add(row['fund'])
                    if len(batch.data) < batch_size:
                        break
                    offset += batch_size
                    if offset > 50000:  # Safety limit
                        break
                
                fund_names = sorted(list(all_funds))
            
            # Get statistics for each fund
            if fund_names:
                fund_stats = []
                for fund_name in fund_names:
                    # Get position count
                    pos_count = client.supabase.table("portfolio_positions").select("id", count="exact").eq("fund", fund_name).execute()
                    position_count = pos_count.count if hasattr(pos_count, 'count') else len(pos_count.data) if pos_count.data else 0
                    
                    # Get latest date
                    latest_date_result = client.supabase.table("portfolio_positions").select("date").eq("fund", fund_name).order("date", desc=True).limit(1).execute()
                    latest_date = latest_date_result.data[0]['date'] if latest_date_result.data else "N/A"
                    
                    fund_stats.append({
                        "Fund Name": fund_name,
                        "Positions": position_count,
                        "Latest Data": latest_date
                    })
                
                funds_df = pd.DataFrame(fund_stats)
                st.subheader("All Funds")
                st.dataframe(funds_df, use_container_width=True)
            else:
                st.info("No funds found")
            
            # Note: Funds are created automatically when portfolio data is added
            # There's no separate funds table - funds are identified by name in portfolio_positions
            st.info("💡 Funds are created automatically when portfolio data is added. No manual creation needed.")
        except Exception as e:
            st.error(f"Error loading funds: {e}")

# Tab 4: System Status
with tab4:
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

