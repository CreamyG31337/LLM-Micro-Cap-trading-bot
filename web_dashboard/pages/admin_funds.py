#!/usr/bin/env python3
"""
Fund Management
==============

Admin page for managing funds, including creation, editing, deletion, and portfolio operations.
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

from auth_utils import is_authenticated, has_admin_access, can_modify_data, get_user_email
from streamlit_utils import get_supabase_client, display_dataframe_with_copy
from supabase_client import SupabaseClient
from navigation import render_navigation

# Import shared utilities
from admin_utils import perf_timer, get_cached_funds, get_cached_fund_names, get_fund_statistics_batched

# Import log_handler to register PERF logging level
try:
    import log_handler  # noqa: F401 - Import to register PERF level
except ImportError:
    pass

# Performance logging setup
import logging
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(page_title="Fund Management", page_icon="🏦", layout="wide")

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

# Check admin access (allows both admin and readonly_admin)
if not has_admin_access():
    st.error("❌ Access Denied: Admin privileges required")
    st.info("Only administrators can access this page.")
    st.stop()

# Navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Header
st.markdown("# 🏦 Fund Management")
st.caption(f"Logged in as: {get_user_email()}")

client = get_supabase_client()
if not client:
    st.error("Failed to connect to database")
else:
    # Load all funds from cache with spinner
    with st.spinner("Loading funds..."):
        try:
            with perf_timer("Fund Management Load"):
                funds_data = get_cached_funds()
                fund_names = [f['name'] for f in funds_data]
                
                # Get statistics for all funds in batched queries
                if fund_names:
                    # Get batched statistics (replaces N+1 queries with 2 batched queries)
                    fund_statistics = get_fund_statistics_batched(fund_names)
                    
                    fund_stats = []
                    for fund_name in fund_names:
                        # Get fund details
                        fund_info = next((f for f in funds_data if f['name'] == fund_name), {})
                        
                        # Get statistics from batched result
                        stats = fund_statistics.get(fund_name, {"positions": 0, "trades": 0})
                        
                        fund_stats.append({
                            "Fund Name": fund_name,
                            "Type": fund_info.get('fund_type', 'N/A'),
                            "Currency": fund_info.get('currency', 'N/A'),
                            "Production": "✅" if fund_info.get('is_production') else "❌",
                            "Positions": stats["positions"],
                            "Trades": stats["trades"]
                        })
                    
                    funds_df = pd.DataFrame(fund_stats)
                    st.subheader("All Funds")
                    display_dataframe_with_copy(funds_df, label="All Funds", key_suffix="funds", use_container_width=True)
                else:
                    st.info("No funds found in database")
        except Exception as e:
            st.error(f"Error loading funds: {e}")
    
    st.divider()
    
    # ===== REFRESH TICKER METADATA =====
    st.subheader("🔄 Refresh Ticker Metadata")
    st.caption("Update company name, sector, and industry for any ticker from yfinance")
    
    col_ticker, col_currency, col_button = st.columns([2, 1, 1])
    with col_ticker:
        refresh_ticker = st.text_input("Ticker Symbol", placeholder="e.g., PRE", key="refresh_ticker_input", label_visibility="collapsed")
    with col_currency:
        refresh_currency = st.selectbox("Currency", options=["CAD", "USD"], index=0, key="refresh_currency_select", label_visibility="collapsed")
    with col_button:
        st.write("")  # Spacer
        if st.button("🔄 Refresh Metadata", key="refresh_metadata_button", use_container_width=True):
            if not refresh_ticker:
                st.error("Please enter a ticker symbol")
            else:
                try:
                    with st.spinner(f"Refreshing metadata for {refresh_ticker}..."):
                        admin_client = SupabaseClient(use_service_role=True)
                        success = admin_client.ensure_ticker_in_securities(refresh_ticker.upper().strip(), refresh_currency)
                        
                        if success:
                            # Get updated data to show
                            updated = admin_client.supabase.table("securities")\
                                .select("ticker, company_name, sector, industry, currency")\
                                .eq("ticker", refresh_ticker.upper().strip())\
                                .execute()
                            
                            if updated.data:
                                data = updated.data[0]
                                st.success(f"✅ **{data.get('company_name', refresh_ticker)}**")
                                st.info(f"**Sector:** {data.get('sector', 'N/A')} | **Industry:** {data.get('industry', 'N/A')} | **Currency:** {data.get('currency', 'N/A')}")
                                st.cache_data.clear()
                            else:
                                st.warning(f"Ticker {refresh_ticker} not found after refresh")
                        else:
                            st.error(f"Failed to refresh metadata for {refresh_ticker}")
                except Exception as e:
                    st.error(f"Error refreshing metadata: {e}")
    
    st.divider()
    
    # ===== TOGGLE PRODUCTION FLAG =====
    st.subheader("🏭 Toggle Production Status")
    st.caption("Mark funds as production (included in automated backfill) or test/dev (excluded)")
    with st.expander("Manage production flags", expanded=True):
        if fund_names:
            for fund_name in fund_names:
                fund_info = next((f for f in funds_data if f['name'] == fund_name), {})
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
                    
                    # Update if changed (only if can modify)
                    if new_status != is_prod and can_modify_data():
                        try:
                            client.supabase.table("funds")\
                                .update({"is_production": new_status})\
                                .eq("name", fund_name)\
                                .execute()
                            st.cache_data.clear()  # Clear cache after update
                            st.toast(f"✅ {fund_name} marked as {'production' if new_status else 'test/dev'}", icon="✅")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating {fund_name}: {e}")
        else:
            st.info("No funds found")
    
    # Get fund_names again for the rest of the operations
    fund_names = get_cached_fund_names()
    
    st.divider()
    
    # ===== EDIT FUND DETAILS =====
    st.subheader("✏️ Edit Fund Details")
    st.caption("Update fund type, description, or currency")
    with st.expander("Edit fund details", expanded=False):
        col_edit1, col_edit2 = st.columns(2)
        with col_edit1:
            edit_fund = st.selectbox("Select Fund to Edit", options=[""] + fund_names, key="edit_fund_select")
        
        # Fetch current details if fund selected
        current_desc = ""
        current_type = "investment"
        current_curr = "CAD"
        
        if edit_fund:
            fund_info = next((f for f in funds_data if f['name'] == edit_fund), {})
            current_desc = fund_info.get('description', '')
            current_type = fund_info.get('fund_type', 'investment')
            current_curr = fund_info.get('currency', 'CAD')
        
        with col_edit1:
            new_desc = st.text_input("Description", value=current_desc, key="edit_fund_desc")
            new_curr = st.selectbox("Currency", options=["CAD", "USD"], index=0 if current_curr == "CAD" else 1, key="edit_fund_curr")
        
        with col_edit2:
            # Add 'rrsp' to options explicitly
            type_options = sorted(list(set(["investment", "retirement", "tfsa", "test", "rrsp", "margin", "personal"])))
            # Ensure current type is in options
            if current_type not in type_options:
                type_options.append(current_type)
            
            type_index = type_options.index(current_type) if current_type in type_options else 0
            new_type = st.selectbox("Fund Type (Set to 'rrsp' for tax exemption)", options=type_options, index=type_index, key="edit_fund_type")
        
        if st.button("💾 Save Changes", type="primary", disabled=(not edit_fund or not can_modify_data())):
            if not can_modify_data():
                st.error("❌ Read-only admin cannot modify fund details")
                st.stop()
            try:
                client.supabase.table("funds").update({
                    "description": new_desc,
                    "fund_type": new_type,
                    "currency": new_curr
                }).eq("name", edit_fund).execute()
                
                st.cache_data.clear()
                st.toast(f"✅ Updated details for '{edit_fund}'", icon="✅")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating fund: {e}")
    
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
        
        if st.button("➕ Create Fund", type="primary", disabled=not can_modify_data()):
            if not can_modify_data():
                st.error("❌ Read-only admin cannot create funds")
                st.stop()
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
                    
                    st.cache_data.clear()  # Clear cache after adding fund
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
        
        if st.button("✏️ Rename Fund", type="primary", disabled=not can_modify_data()):
            if not can_modify_data():
                st.error("❌ Read-only admin cannot rename funds")
                st.stop()
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
                    st.cache_data.clear()  # Clear cache after renaming
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
        
        if st.button("🧹 Wipe Fund Data", type="secondary", disabled=not can_modify_data()):
                if not can_modify_data():
                    st.error("❌ Read-only admin cannot wipe fund data")
                    st.stop()
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
            
            if st.button("🔄 Wipe Portfolio Positions Only", type="primary", disabled=not can_modify_data()):
                if not can_modify_data():
                    st.error("❌ Read-only admin cannot wipe portfolio positions")
                    st.stop()
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
            
            if st.button("🔧 Rebuild Portfolio", type="primary", disabled=not can_modify_data()):
                if not can_modify_data():
                    st.error("❌ Read-only admin cannot rebuild portfolios")
                    st.stop()
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
                            # admin_funds.py is in web_dashboard/pages/, so go up 2 levels to get project root
                            admin_file = Path(__file__).resolve()
                            # admin_funds.py is in web_dashboard/pages/, so:
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
            
            if st.button("🗑️ Delete Fund Permanently", type="secondary", disabled=not can_modify_data()):
                if not can_modify_data():
                    st.error("❌ Read-only admin cannot delete funds")
                    st.stop()
                if not delete_fund:
                    st.error("Please select a fund")
                elif confirm_delete_name != delete_fund:
                    st.error("Fund name doesn't match. Please type the fund name exactly to confirm.")
                else:
                    try:
                        # First clear all dependent data (FK constraints use ON DELETE RESTRICT)
                        client.supabase.table("portfolio_positions").delete().eq("fund", delete_fund).execute()
                        client.supabase.table("trade_log").delete().eq("fund", delete_fund).execute()
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

