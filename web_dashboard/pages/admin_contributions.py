#!/usr/bin/env python3
"""
Contributions Management
=======================

Admin page for managing investor contributions and withdrawals.
"""

import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, has_admin_access, can_modify_data, get_user_email
from streamlit_utils import get_supabase_client, display_dataframe_with_copy, render_sidebar_fund_selector
from navigation import render_navigation

# Import shared utilities
from admin_utils import perf_timer, get_cached_fund_names, get_cached_contributors

# Import log_handler to register PERF logging level
try:
    import log_handler  # noqa: F401 - Import to register PERF level
except ImportError:
    pass

# Performance logging setup
import logging
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Contributions", page_icon="💰", layout="wide")

# Check authentication - redirect to main page if not logged in
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Refresh token if needed (auto-refresh before expiry)
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    from auth_utils import logout_user
    logout_user()
    st.error("Your session has expired. Please log in again.")
    st.switch_page("streamlit_app.py")
    st.stop()

# Check admin access (allows both admin and readonly_admin)
if not has_admin_access():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Standardized sidebar fund selector
with st.sidebar:
    st.markdown("---")
    st.header("📊 Fund Selection")
    global_selected_fund = render_sidebar_fund_selector()

# Header
st.markdown("# 💰 Contribution Management")
st.caption(f"Logged in as: {get_user_email()}")

client = get_supabase_client()
if not client:
    st.error("Failed to connect to database")
else:
    try:
        fund_names = get_cached_fund_names()
        
        if not fund_names:
            st.warning("No funds available. Create a fund first in Fund Management.")
        else:
            # Add Contribution/Withdrawal
            st.subheader("Add Contribution or Withdrawal")
            
            col1, col2 = st.columns(2)
            
            with col1:
                contrib_fund = st.selectbox("Fund", options=fund_names, key="contrib_fund")
                contrib_name = st.text_input("Contributor Name", key="contrib_name")
                contrib_email = st.text_input("Contributor Email (optional)", key="contrib_email")
            
            with col2:
                contrib_amount = st.number_input("Amount", min_value=0.01, value=1000.0, step=100.0, format="%.2f", key="contrib_amount")
                contrib_type = st.selectbox("Type", options=["CONTRIBUTION", "WITHDRAWAL"], key="contrib_type")
                contrib_date = st.date_input("Date", value=datetime.now(), key="contrib_date")
            
            contrib_notes = st.text_area("Notes (optional)", key="contrib_notes", height=100)
            
            if st.button("💾 Add Contribution/Withdrawal", type="primary", disabled=not can_modify_data()):
                if not can_modify_data():
                    st.error("❌ Read-only admin cannot add contributions")
                    st.stop()
                if not contrib_name:
                    st.error("Please enter a contributor name")
                elif contrib_amount <= 0:
                    st.error("Amount must be greater than 0")
                else:
                    try:
                        # Combine date with current time
                        contrib_timestamp = datetime.combine(contrib_date, datetime.now().time())
                        
                        contribution_data = {
                            "fund": contrib_fund,
                            "contributor": contrib_name,
                            "email": contrib_email if contrib_email else None,
                            "amount": float(contrib_amount),
                            "contribution_type": contrib_type,
                            "timestamp": contrib_timestamp.isoformat(),
                            "notes": contrib_notes if contrib_notes else None
                        }
                        
                        client.supabase.table("fund_contributions").insert(contribution_data).execute()
                        
                        st.cache_data.clear()
                        st.success(f"✅ {contrib_type} of ${contrib_amount:,.2f} recorded for {contrib_name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding contribution: {e}")
            
            st.divider()
            
            # View Contributions
            st.subheader("All Contributions")
            
            # Filter options
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                filter_fund = st.selectbox("Filter by Fund", options=["All"] + fund_names, key="filter_fund")
            with col_filter2:
                filter_type = st.selectbox("Filter by Type", options=["All", "CONTRIBUTION", "WITHDRAWAL"], key="filter_type")
            with col_filter3:
                filter_contributor = st.text_input("Filter by Contributor", key="filter_contributor", placeholder="Search contributor name...")
            
            # Build query
            query = client.supabase.table("fund_contributions").select("*").order("timestamp", desc=True)
            
            if filter_fund != "All":
                query = query.eq("fund", filter_fund)
            if filter_type != "All":
                query = query.eq("contribution_type", filter_type)
            if filter_contributor:
                query = query.ilike("contributor", f"%{filter_contributor}%")
            
            contributions = query.execute()
            
            if contributions.data:
                contrib_df = pd.DataFrame(contributions.data)
                
                # Format timestamp for display
                if 'timestamp' in contrib_df.columns:
                    contrib_df['timestamp'] = pd.to_datetime(contrib_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
                
                # Format amount with currency symbol
                if 'amount' in contrib_df.columns:
                    contrib_df['amount'] = contrib_df['amount'].apply(lambda x: f"${float(x):,.2f}" if pd.notna(x) else "$0.00")
                
                display_dataframe_with_copy(contrib_df, label="Contributions", key_suffix="contributions", use_container_width=True)
            else:
                st.info("No contributions found matching the filters")
            
            st.divider()
            
            # Contributor Summary
            st.subheader("Contributor Summary")
            
            try:
                # Get summary by contributor
                summary_query = client.supabase.table("fund_contributions").select("contributor, fund, contribution_type, amount").execute()
                
                if summary_query.data:
                    summary_df = pd.DataFrame(summary_query.data)
                    
                    # Calculate totals by contributor and fund
                    summary = summary_df.groupby(['contributor', 'fund', 'contribution_type'])['amount'].sum().reset_index()
                    
                    # Pivot to show contributions and withdrawals
                    pivot_summary = summary.pivot_table(
                        index=['contributor', 'fund'],
                        columns='contribution_type',
                        values='amount',
                        fill_value=0
                    ).reset_index()
                    
                    # Calculate net contribution
                    if 'CONTRIBUTION' in pivot_summary.columns and 'WITHDRAWAL' in pivot_summary.columns:
                        pivot_summary['Net Contribution'] = pivot_summary['CONTRIBUTION'] - pivot_summary['WITHDRAWAL']
                    elif 'CONTRIBUTION' in pivot_summary.columns:
                        pivot_summary['Net Contribution'] = pivot_summary['CONTRIBUTION']
                    elif 'WITHDRAWAL' in pivot_summary.columns:
                        pivot_summary['Net Contribution'] = -pivot_summary['WITHDRAWAL']
                    
                    # Format currency columns
                    for col in ['CONTRIBUTION', 'WITHDRAWAL', 'Net Contribution']:
                        if col in pivot_summary.columns:
                            pivot_summary[col] = pivot_summary[col].apply(lambda x: f"${float(x):,.2f}" if pd.notna(x) else "$0.00")
                    
                    display_dataframe_with_copy(pivot_summary, label="Contributor Summary", key_suffix="contributor_summary", use_container_width=True)
                else:
                    st.info("No contributions found for summary")
            except Exception as e:
                st.warning(f"Could not generate contributor summary: {e}")
                
    except Exception as e:
        st.error(f"Error loading contributions: {e}")

