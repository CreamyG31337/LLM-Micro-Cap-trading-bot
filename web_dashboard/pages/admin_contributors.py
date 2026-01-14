#!/usr/bin/env python3
"""
Contributor Management
======================

Admin page for managing contributors (investors), including:
- Viewing contributors and their fund contributions
- Splitting contributors into separate accounts
- Merging contributors
- Editing contributor details
"""

import streamlit as st
import sys
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, has_admin_access, can_modify_data, get_user_email, redirect_to_login
from streamlit_utils import get_supabase_client, display_dataframe_with_copy
from navigation import render_navigation

# Import shared utilities
from admin_utils import perf_timer, get_cached_contributors, get_cached_fund_names

# Page configuration
st.set_page_config(page_title="Contributor Management", page_icon="👤", layout="wide")

# Check authentication
if not is_authenticated():
    redirect_to_login("pages/admin_contributors.py")

# Refresh token if needed
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    from auth_utils import logout_user
    logout_user(return_to="pages/admin_contributors.py")
    st.stop()

# Check admin access
if not has_admin_access():
    st.error("❌ Access Denied: Admin privileges required")
    st.stop()

# Navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Header
st.markdown("# 👤 Contributor Management")
st.caption(f"Manage contributors (investors) and their fund contributions")

client = get_supabase_client()
if not client:
    st.error("Failed to connect to database")
    st.stop()

# Get contributors
with st.spinner("Loading contributors..."):
    try:
        contributors_list = get_cached_contributors()
        if not contributors_list:
            st.info("No contributors found")
            st.stop()
    except Exception as e:
        st.error(f"Error loading contributors: {e}")
        st.stop()

# Create tabs
tab_view, tab_split, tab_merge, tab_edit = st.tabs([
    "📋 View Contributors",
    "✂️ Split Contributor",
    "🔗 Merge Contributors",
    "✏️ Edit Contributor"
])

# Tab 1: View Contributors
with tab_view:
    st.header("📋 All Contributors")
    
    # Filter options
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        search_name = st.text_input("Search by name", key="contrib_search_name")
    with col_filter2:
        search_email = st.text_input("Search by email", key="contrib_search_email")
    
    # Filter contributors
    filtered_contributors = contributors_list
    if search_name:
        filtered_contributors = [c for c in filtered_contributors if search_name.lower() in c.get('name', '').lower()]
    if search_email:
        filtered_contributors = [c for c in filtered_contributors if search_email.lower() in (c.get('email') or '').lower()]
    
    st.caption(f"Showing {len(filtered_contributors)} of {len(contributors_list)} contributors")
    
    # Display contributors
    for contrib in filtered_contributors:
        contrib_id = contrib.get('id')
        contrib_name = contrib.get('name')
        contrib_email = contrib.get('email')
        
        with st.expander(f"👤 {contrib_name} ({contrib_email or 'No email'})", expanded=False):
            # Get fund contributions for this contributor
            try:
                # Try by contributor_id first
                contribs_result = client.supabase.table("fund_contributions")\
                    .select("*")\
                    .eq("contributor_id", contrib_id)\
                    .execute()
                
                # Also get by name (legacy)
                contribs_by_name = client.supabase.table("fund_contributions")\
                    .select("*")\
                    .eq("contributor", contrib_name)\
                    .execute()
                
                # Combine and deduplicate
                all_contribs = contribs_result.data or []
                contrib_ids = {c.get('id') for c in all_contribs}
                for c in (contribs_by_name.data or []):
                    if c.get('id') not in contrib_ids:
                        all_contribs.append(c)
                
                if all_contribs:
                    # Group by fund
                    by_fund = {}
                    for c in all_contribs:
                        fund = c.get('fund')
                        if fund not in by_fund:
                            by_fund[fund] = []
                        by_fund[fund].append(c)
                    
                    st.markdown(f"**Contributor ID:** `{contrib_id}`")
                    if contrib_email:
                        st.markdown(f"**Email:** {contrib_email}")
                    
                    st.markdown("**Fund Contributions:**")
                    for fund, contribs in by_fund.items():
                        net_amount = Decimal('0')
                        for c in contribs:
                            amount = Decimal(str(c.get('amount', 0)))
                            if c.get('contribution_type') == 'CONTRIBUTION':
                                net_amount += amount
                            else:
                                net_amount -= amount
                        
                        st.markdown(f"- **{fund}**: {len(contribs)} transactions, Net: ${net_amount:,.2f}")
                    
                    # Show transaction details
                    if st.checkbox(f"Show transaction details", key=f"show_details_{contrib_id}"):
                        contribs_df = pd.DataFrame(all_contribs)
                        if not contribs_df.empty:
                            # Select relevant columns
                            display_cols = ['fund', 'amount', 'contribution_type', 'timestamp', 'notes']
                            available_cols = [c for c in display_cols if c in contribs_df.columns]
                            contribs_df = contribs_df[available_cols]
                            contribs_df = contribs_df.sort_values('timestamp', ascending=False)
                            display_dataframe_with_copy(contribs_df, label=f"Contributions for {contrib_name}", key_suffix=f"contrib_{contrib_id}")
                else:
                    st.info("No fund contributions found for this contributor")
                    
            except Exception as e:
                st.error(f"Error loading contributions: {e}")

# Tab 2: Split Contributor
with tab_split:
    st.header("✂️ Split Contributor")
    st.caption("Split a contributor into two separate accounts by reassigning specific fund contributions")
    
    if not can_modify_data():
        st.warning("⚠️ Read-only admin cannot split contributors")
        st.stop()
    
    # Select contributor to split
    contributor_options = {f"{c['name']} ({c.get('email') or 'No email'})": c['id'] for c in contributors_list}
    selected_contributor_display = st.selectbox(
        "Select Contributor to Split",
        options=[""] + list(contributor_options.keys()),
        key="split_contributor_select"
    )
    
    if selected_contributor_display:
        selected_contributor_id = contributor_options[selected_contributor_display]
        selected_contributor = next((c for c in contributors_list if c['id'] == selected_contributor_id), None)
        
        if selected_contributor:
            st.divider()
            st.markdown(f"**Splitting:** {selected_contributor['name']}")
            
            # Get all contributions for this contributor
            try:
                contribs_result = client.supabase.table("fund_contributions")\
                    .select("*")\
                    .eq("contributor_id", selected_contributor_id)\
                    .execute()
                
                contribs_by_name = client.supabase.table("fund_contributions")\
                    .select("*")\
                    .eq("contributor", selected_contributor['name'])\
                    .execute()
                
                all_contribs = contribs_result.data or []
                contrib_ids = {c.get('id') for c in all_contribs}
                for c in (contribs_by_name.data or []):
                    if c.get('id') not in contrib_ids:
                        all_contribs.append(c)
                
                if not all_contribs:
                    st.warning("No contributions found for this contributor")
                else:
                    st.markdown(f"**Found {len(all_contribs)} contribution(s)**")
                    
                    # New contributor details
                    st.subheader("New Contributor Details")
                    new_contributor_name = st.text_input("New Contributor Name", key="new_contrib_name")
                    new_contributor_email = st.text_input("New Contributor Email (optional)", key="new_contrib_email")
                    
                    # Select contributions to move
                    st.subheader("Select Contributions to Move")
                    contribs_df = pd.DataFrame(all_contribs)
                    contribs_df['display'] = contribs_df.apply(
                        lambda row: f"{row.get('fund')} - ${row.get('amount', 0):,.2f} ({row.get('contribution_type')}) - {row.get('timestamp', '')[:10]}",
                        axis=1
                    )
                    
                    selected_contrib_ids = st.multiselect(
                        "Select contributions to move to new contributor",
                        options=contribs_df['id'].tolist(),
                        format_func=lambda x: contribs_df[contribs_df['id'] == x]['display'].iloc[0] if not contribs_df[contribs_df['id'] == x].empty else str(x),
                        key="split_contrib_select"
                    )
                    
                    if st.button("✂️ Split Contributor", type="primary", disabled=not new_contributor_name or not selected_contrib_ids):
                        if not new_contributor_name:
                            st.error("Please enter a name for the new contributor")
                        elif not selected_contrib_ids:
                            st.error("Please select at least one contribution to move")
                        else:
                            try:
                                with st.spinner("Splitting contributor..."):
                                    # Create new contributor
                                    new_contrib_data = {
                                        "name": new_contributor_name,
                                        "email": new_contributor_email if new_contributor_email else None
                                    }
                                    new_contrib_result = client.supabase.table("contributors").insert(new_contrib_data).execute()
                                    
                                    if not new_contrib_result.data:
                                        st.error("Failed to create new contributor")
                                    else:
                                        new_contrib_id = new_contrib_result.data[0]['id']
                                        
                                        # Update selected contributions
                                        updated_count = 0
                                        for contrib_id in selected_contrib_ids:
                                            # Update both contributor_id and contributor name
                                            update_data = {
                                                "contributor_id": new_contrib_id,
                                                "contributor": new_contributor_name
                                            }
                                            if new_contributor_email:
                                                update_data["email"] = new_contributor_email
                                            
                                            result = client.supabase.table("fund_contributions")\
                                                .update(update_data)\
                                                .eq("id", contrib_id)\
                                                .execute()
                                            
                                            if result.data:
                                                updated_count += 1
                                        
                                        # Clear cache
                                        st.cache_data.clear()
                                        st.success(f"✅ Split complete! Created new contributor '{new_contributor_name}' and moved {updated_count} contribution(s)")
                                        st.rerun()
                                        
                            except Exception as e:
                                st.error(f"Error splitting contributor: {e}")
                                import traceback
                                st.code(traceback.format_exc())
            except Exception as e:
                st.error(f"Error loading contributions: {e}")

# Tab 3: Merge Contributors
with tab_merge:
    st.header("🔗 Merge Contributors")
    st.caption("Merge two contributors into one (moves all contributions to the target contributor)")
    
    if not can_modify_data():
        st.warning("⚠️ Read-only admin cannot merge contributors")
        st.stop()
    
    st.info("💡 Select the source contributor to merge FROM, and the target contributor to merge INTO. All contributions from the source will be moved to the target.")
    
    contributor_options = {f"{c['name']} ({c.get('email') or 'No email'})": c['id'] for c in contributors_list}
    
    col_merge1, col_merge2 = st.columns(2)
    with col_merge1:
        source_contributor = st.selectbox(
            "Source Contributor (merge FROM)",
            options=[""] + list(contributor_options.keys()),
            key="merge_source"
        )
    with col_merge2:
        target_contributor = st.selectbox(
            "Target Contributor (merge INTO)",
            options=[""] + list(contributor_options.keys()),
            key="merge_target"
        )
    
    if source_contributor and target_contributor:
        source_id = contributor_options[source_contributor]
        target_id = contributor_options[target_contributor]
        
        if source_id == target_id:
            st.error("Source and target cannot be the same")
        else:
            source_contrib = next((c for c in contributors_list if c['id'] == source_id), None)
            target_contrib = next((c for c in contributors_list if c['id'] == target_id), None)
            
            if source_contrib and target_contrib:
                st.divider()
                st.markdown(f"**Merging:** {source_contrib['name']} → {target_contrib['name']}")
                
                # Get contributions count
                try:
                    source_contribs = client.supabase.table("fund_contributions")\
                        .select("id")\
                        .or_(f"contributor_id.eq.{source_id},contributor.eq.{source_contrib['name']}")\
                        .execute()
                    
                    contrib_count = len(source_contribs.data) if source_contribs.data else 0
                    st.markdown(f"**Will move {contrib_count} contribution(s)**")
                    
                    if st.button("🔗 Merge Contributors", type="primary"):
                        try:
                            with st.spinner("Merging contributors..."):
                                # Update all contributions
                                update_data = {
                                    "contributor_id": target_id,
                                    "contributor": target_contrib['name']
                                }
                                if target_contrib.get('email'):
                                    update_data["email"] = target_contrib['email']
                                
                                # Update by contributor_id
                                result1 = client.supabase.table("fund_contributions")\
                                    .update(update_data)\
                                    .eq("contributor_id", source_id)\
                                    .execute()
                                
                                # Update by contributor name (legacy)
                                result2 = client.supabase.table("fund_contributions")\
                                    .update(update_data)\
                                    .eq("contributor", source_contrib['name'])\
                                    .execute()
                                
                                # Delete source contributor
                                delete_result = client.supabase.table("contributors")\
                                    .delete()\
                                    .eq("id", source_id)\
                                    .execute()
                                
                                # Clear cache
                                st.cache_data.clear()
                                st.success(f"✅ Merged {source_contrib['name']} into {target_contrib['name']}")
                                st.rerun()
                                
                        except Exception as e:
                            st.error(f"Error merging contributors: {e}")
                            import traceback
                            st.code(traceback.format_exc())
                except Exception as e:
                    st.error(f"Error loading contributions: {e}")

# Tab 4: Edit Contributor
with tab_edit:
    st.header("✏️ Edit Contributor")
    
    if not can_modify_data():
        st.warning("⚠️ Read-only admin cannot edit contributors")
        st.stop()
    
    contributor_options = {f"{c['name']} ({c.get('email') or 'No email'})": c['id'] for c in contributors_list}
    selected_contributor_display = st.selectbox(
        "Select Contributor to Edit",
        options=[""] + list(contributor_options.keys()),
        key="edit_contributor_select"
    )
    
    if selected_contributor_display:
        selected_contributor_id = contributor_options[selected_contributor_display]
        selected_contributor = next((c for c in contributors_list if c['id'] == selected_contributor_id), None)
        
        if selected_contributor:
            st.divider()
            
            new_name = st.text_input("Name", value=selected_contributor.get('name', ''), key="edit_name")
            new_email = st.text_input("Email", value=selected_contributor.get('email') or '', key="edit_email")
            
            if st.button("💾 Save Changes", type="primary"):
                try:
                    update_data = {"name": new_name}
                    if new_email:
                        update_data["email"] = new_email
                    else:
                        update_data["email"] = None
                    
                    result = client.supabase.table("contributors")\
                        .update(update_data)\
                        .eq("id", selected_contributor_id)\
                        .execute()
                    
                    if result.data:
                        # Also update fund_contributions if name changed
                        if new_name != selected_contributor.get('name'):
                            client.supabase.table("fund_contributions")\
                                .update({"contributor": new_name})\
                                .eq("contributor_id", selected_contributor_id)\
                                .execute()
                            
                            # Also update by old name (legacy)
                            client.supabase.table("fund_contributions")\
                                .update({"contributor": new_name})\
                                .eq("contributor", selected_contributor.get('name'))\
                                .execute()
                        
                        # Update email in fund_contributions if changed
                        if new_email != selected_contributor.get('email'):
                            if new_email:
                                client.supabase.table("fund_contributions")\
                                    .update({"email": new_email})\
                                    .eq("contributor_id", selected_contributor_id)\
                                    .execute()
                        
                        st.cache_data.clear()
                        st.success("✅ Contributor updated successfully")
                        st.rerun()
                    else:
                        st.error("Failed to update contributor")
                        
                except Exception as e:
                    st.error(f"Error updating contributor: {e}")
                    import traceback
                    st.code(traceback.format_exc())
