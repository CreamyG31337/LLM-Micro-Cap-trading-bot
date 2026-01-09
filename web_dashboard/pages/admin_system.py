#!/usr/bin/env python3
"""
System Monitoring
================

Admin page for system status monitoring and log viewing.
Combines System Status and System Logs.
"""

import streamlit as st
import sys
import os
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, has_admin_access, get_user_email
from navigation import render_navigation

# Import shared utilities
from admin_utils import perf_timer, get_system_status_cached

# Page configuration
st.set_page_config(page_title="System Monitoring", page_icon="📊", layout="wide")

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
st.markdown("# 📊 System Monitoring")
st.caption(f"Logged in as: {get_user_email()}")

# Create tabs for System Status and System Logs
tab_status, tab_logs = st.tabs([
    "📊 System Status",
    "📜 System Logs"
])

# Tab 1: System Status
with tab_status:
    with perf_timer("System Status"):
        st.header("📊 System Status")
        st.caption("Monitor system health and status")
        
        # Get cached system status (replaces multiple separate queries)
        status = get_system_status_cached()
        
        # Database connection status
        st.subheader("Database Status")
        if status["supabase_connected"]:
            st.success("✅ Database: Connected")
        else:
            st.error("❌ Database: Connection Failed")
            if status["errors"]:
                for error in status["errors"]:
                    if "Supabase connection" in error:
                        st.error(f"❌ Database: Connection Error - {error}")
        
        # Exchange rates status
        st.subheader("Exchange Rates")
        if status["exchange_rates"]:
            st.info(f"Latest rate: {status['exchange_rates']}")
        else:
            st.warning("No exchange rates found")
            if status["errors"]:
                for error in status["errors"]:
                    if "Exchange rates" in error:
                        st.error(f"Error checking exchange rates: {error}")
        
        # Postgres (Research Repository) status
        st.subheader("Postgres (Research Repository)")
        if status["postgres_connected"]:
            st.success("✅ Postgres: Connected")
            if status["postgres_stats"]:
                st.info(f"Total research articles: {status['postgres_stats']['total']}")
                st.info(f"Articles (last 7 days): {status['postgres_stats']['recent_7d']}")
        else:
            st.error("❌ Postgres: Connection Failed")
            # Check if it's an import error
            try:
                from postgres_client import PostgresClient
            except ImportError:
                st.warning("⚠️ Postgres client not available (psycopg2 not installed)")
        
        # Job execution logs (from scheduler)
        st.subheader("Recent Job Executions")
        try:
            from scheduler.scheduler_core import get_job_logs
            all_jobs = ['exchange_rates']
            
            for job_id in all_jobs:
                logs = get_job_logs(job_id, limit=5)
                if logs:
                    st.write(f"**{job_id}**")
                    for log in logs:
                        log_status = "✅" if log['success'] else "❌"
                        time_str = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        st.text(f"{log_status} {time_str} - {log['message'][:50]}")
        except ImportError:
            st.info("Scheduler module not available")
        except Exception as e:
            st.warning(f"Could not load job logs: {e}")

# Tab 2: System Logs (Application + Docker)
with tab_logs:
    # Create sub-tabs for Application Logs and System Logs
    tab_app_logs, tab_sys_logs = st.tabs([
        "📋 Application Logs",
        "🐳 System Logs"
    ])
    
    # Application Logs
    with tab_app_logs:
        st.header("📋 Application Logs")
        st.caption("View recent application logs with filtering")
        
        try:
            from log_handler import read_logs_from_file
            
            # Controls row
            col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 1, 1, 1, 1.5, 1.5, 1])
            
            with col1:
                auto_refresh = st.checkbox("🔄 Auto-refresh", value=False, help="Refresh logs every 5 seconds")
            
            with col2:
                level_filter = st.selectbox(
                    "Level",
                    options=["All", "INFO + ERROR", "DEBUG", "PERF", "INFO", "WARNING", "ERROR"],
                    index=1  # Default to "INFO + ERROR"
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
                exclude_heartbeat = st.checkbox(
                    "💓 Hide Heartbeat", 
                    value=True, 
                    help="Exclude scheduler heartbeat logs (scheduler.scheduler_core.heartbeat)"
                )
            
            with col7:
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
            
            # Initialize pagination state
            if 'log_page' not in st.session_state:
                st.session_state.log_page = 1
            
            # Reset page to 1 if filters change
            filter_key = f"{level_filter}_{num_logs}_{sort_order}_{search_text}_{exclude_heartbeat}"
            if 'log_filter_key' not in st.session_state or st.session_state.log_filter_key != filter_key:
                st.session_state.log_page = 1
                st.session_state.log_filter_key = filter_key
            
            # Get logs with filters (with spinner for better UX)
            with st.spinner("Loading logs..."):
                # Handle special "INFO + ERROR" filter
                if level_filter == "All":
                    level = None
                elif level_filter == "INFO + ERROR":
                    level = ["INFO", "ERROR"]
                else:
                    level = level_filter
                
                # Build exclude_modules list
                exclude_modules = []
                if exclude_heartbeat:
                    exclude_modules.append('scheduler.scheduler_core.heartbeat')
                
                # Fetch all filtered logs for pagination
                all_logs = read_logs_from_file(
                    n=None,  # Get all logs (up to reasonable limit)
                    level=level,
                    search=search_text if search_text else None,
                    return_all=True,
                    exclude_modules=exclude_modules if exclude_modules else None
                )
                
                # Apply sort order (default from file is oldest first)
                if sort_order == "Newest First" and all_logs:
                    all_logs = list(reversed(all_logs))
            
            # Calculate pagination
            total_logs = len(all_logs)
            logs_per_page = num_logs
            total_pages = max(1, (total_logs + logs_per_page - 1) // logs_per_page) if total_logs > 0 else 1
            
            # Ensure page is within valid range
            if st.session_state.log_page > total_pages:
                st.session_state.log_page = total_pages
            if st.session_state.log_page < 1:
                st.session_state.log_page = 1
            
            # Get logs for current page
            start_idx = (st.session_state.log_page - 1) * logs_per_page
            end_idx = start_idx + logs_per_page
            logs = all_logs[start_idx:end_idx] if total_logs > 0 else []
            
            # Emoji mapping for log levels (used for display and download)
            emoji_map = {
                'DEBUG': '🔍',
                'PERF': '⚡',
                'INFO': 'ℹ️',
                'WARNING': '⚠️',
                'ERROR': '❌'
            }
            
            # Display logs in a code block for better formatting
            if logs:
                # Show pagination info
                page_info = f"Page {st.session_state.log_page} of {total_pages} | Showing {len(logs)} of {total_logs} log entries ({sort_order.lower()})"
                st.caption(page_info)
                
                # Create formatted log output
                log_lines = []
                for log in logs:
                    timestamp = log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    level_str = log['level'].ljust(8)
                    module = log['module'][:30].ljust(30)  # Limit module name width
                    message = log['message']
                    
                    # Add emoji indicators for levels
                    emoji = emoji_map.get(log['level'], '•')
                    
                    log_lines.append(f"{emoji} {timestamp} | {level_str} | {module} | {message}")
                
                # Display in code block
                log_text = "\n".join(log_lines)
                st.code(log_text, language=None)
                
                # Pagination controls
                if total_pages > 1:
                    col_prev, col_info, col_next, col_download = st.columns([1, 2, 1, 1])
                    
                    with col_prev:
                        if st.button("◀️ Previous", disabled=(st.session_state.log_page <= 1), use_container_width=True):
                            st.session_state.log_page -= 1
                            st.rerun()
                    
                    with col_info:
                        st.caption(f"Page {st.session_state.log_page} of {total_pages}")
                    
                    with col_next:
                        if st.button("Next ▶️", disabled=(st.session_state.log_page >= total_pages), use_container_width=True):
                            st.session_state.log_page += 1
                            st.rerun()
                    
                    with col_download:
                        # Download all filtered logs (not just current page)
                        all_log_text = "\n".join([
                            f"{emoji_map.get(log.get('level', ''), '•')} {log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')} | {log['level'].ljust(8)} | {log['module'][:30].ljust(30)} | {log['message']}"
                            for log in all_logs
                        ])
                        st.download_button(
                            label="⬇️ Download All",
                            data=all_log_text,
                            file_name=f"app_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )
                else:
                    # Download button (when no pagination needed)
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
                time.sleep(5)
                st.rerun()
                
        except ImportError:
            st.error("❌ Log handler not available")
            st.info("The logging module may not be initialized. Check streamlit_app.py configuration.")
        except Exception as e:
            st.error(f"Error loading logs: {e}")
    
    # System Logs (Docker/File System)
    with tab_sys_logs:
        st.header("🐳 System Logs")
        st.caption("View Docker container logs or file system logs")
        
        # --- MODE SELECTION ---
        # Check if Docker socket is available
        DOCKER_SOCKET_PATH = "/var/run/docker.sock"
        has_docker_socket = os.path.exists(DOCKER_SOCKET_PATH)

        mode = st.radio(
            "Source", 
            ["Docker Containers (Live)", "File System"], 
            index=0 if has_docker_socket else 1,
            horizontal=True
        )

        if mode == "Docker Containers (Live)":
            if not has_docker_socket:
                st.error("❌ Docker socket not found at `/var/run/docker.sock`")
                st.info("""
                **How to enable Docker monitoring:**
                1. Open Portainer
                2. Edit this `trading-dashboard` container
                3. Under **Volumes**, map `/var/run/docker.sock` (Host) to `/var/run/docker.sock` (Container)
                4. Redeploy
                """)
            else:
                try:
                    import docker
                    client = docker.DockerClient(base_url='unix://var/run/docker.sock')
                    
                    # List containers
                    containers = client.containers.list(all=True)
                    container_names = [c.name for c in containers]
                    container_names.sort()
                    
                    # Find Ollama containers and prioritize them
                    ollama_containers = [name for name in container_names if 'ollama' in name.lower()]
                    other_containers = [name for name in container_names if 'ollama' not in name.lower()]
                    sorted_containers = ollama_containers + other_containers
                    
                    # Create mapping
                    name_to_id = {c.name: c.id for c in containers}
                    
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        # Default to first Ollama container if available (they're listed first)
                        default_index = 0 if ollama_containers and sorted_containers else None
                        
                        selected_container_name = st.selectbox(
                            "Select Container", 
                            sorted_containers, 
                            index=default_index,
                            help="Ollama containers are listed first for easy access"
                        )
                        tail_lines = st.number_input("Lines to fetch", min_value=100, max_value=5000, value=500)
                        
                        if st.button("🔄 Refresh Logs"):
                            st.rerun()

                    if selected_container_name:
                        container_id = name_to_id[selected_container_name]
                        container = client.containers.get(container_id)
                        
                        # Show status
                        status_color = "green" if container.status == "running" else "red"
                        st.markdown(f"**Status:** :{status_color}[{container.status.upper()}] | **ID:** `{container_id[:12]}` | **Image:** `{container.image.tags[0] if container.image.tags else 'unknown'}`")
                        
                        try:
                            # Get logs
                            logs = container.logs(tail=tail_lines).decode('utf-8', errors='replace')
                            # Reverse to show newest first
                            log_lines = logs.split('\n')
                            logs = '\n'.join(reversed(log_lines))
                            
                            st.code(logs, language=None)
                            
                        except Exception as e:
                            st.error(f"Error fetching logs: {e}")
                            
                except ImportError:
                    st.error("`docker` python library not installed. Please add `docker>=7.0.0` to requirements.txt and rebuild.")
                except Exception as e:
                    st.error(f"Failed to connect to Docker: {e}")

        else:
            # --- FILE SYSTEM MODE ---
            LOGS_DIR = Path(__file__).parent.parent / "logs"

            # Ensure directory exists
            if not LOGS_DIR.exists():
                st.warning(f"Logs directory not found at {LOGS_DIR}")
                st.info("""
                **Ollama logs are typically available in Docker mode:**
                1. Switch to **"Docker Containers (Live)"** mode above
                2. Select the Ollama container from the dropdown
                3. Ollama containers are automatically listed first for easy access
                
                **If running in Docker with volume mapping:**
                - Ollama logs should appear at `server/server.log` in File System mode
                - Ensure the volume is mapped: Host `~/ollama-logs` → Container `/app/web_dashboard/logs/server`
                - See `LOGGING_SETUP.md` for detailed setup instructions
                """)
            else:
                # Get list of log files (recursive to find server/ollama.log)
                log_files = list(LOGS_DIR.rglob("*.log"))
                log_files.extend(list(LOGS_DIR.rglob("*.txt")))

                if not log_files:
                    st.warning("No log files found in logs directory.")
                    st.info("""
                    **To view Ollama logs:**
                    1. Switch to **"Docker Containers (Live)"** mode above (recommended)
                    2. Select the Ollama container from the dropdown
                    
                    **Expected Ollama log location:** `server/server.log` (when volume mapping is configured)
                    """)
                else:
                    # Prioritize Ollama logs (server/server.log)
                    ollama_log = LOGS_DIR / "server" / "server.log"
                    ollama_logs = [f for f in log_files if "server" in str(f) and "server.log" in str(f)]
                    other_logs = [f for f in log_files if f not in ollama_logs]
                    
                    # Sort: Ollama logs first, then by modification time
                    if ollama_logs:
                        log_files = ollama_logs + sorted(other_logs, key=os.path.getmtime, reverse=True)
                    else:
                        log_files.sort(key=os.path.getmtime, reverse=True)
                        # Warn if Ollama logs are missing
                        st.warning("⚠️ Ollama logs (`server/server.log`) not found. Showing other log files.")
                        st.info("""
                        **To view Ollama logs:**
                        1. Switch to **"Docker Containers (Live)"** mode above (recommended)
                        2. Or ensure volume mapping is configured: Host `/home/lance/ollama-logs` → Container `/app/web_dashboard/logs/server`
                        """)
                    
                    # Create filenames list for dropdown (relative to logs dir)
                    filenames = [str(f.relative_to(LOGS_DIR)) for f in log_files]
                    
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        # Default to Ollama log if available
                        default_index = 0
                        if ollama_logs and filenames:
                            # Find index of first Ollama log
                            for i, fname in enumerate(filenames):
                                if "server" in fname and "server.log" in fname:
                                    default_index = i
                                    break
                        
                        selected_filename = st.selectbox("Select Log File", filenames, index=default_index)
                        if st.button("🔄 Refresh File"):
                            st.rerun()
                            
                    if selected_filename:
                        selected_path = LOGS_DIR / selected_filename
                        
                        # File metadata
                        try:
                            stats = os.stat(selected_path)
                            size_mb = stats.st_size / (1024 * 1024)
                            st.caption(f"Size: {size_mb:.2f} MB")
                            
                            with open(selected_path, "r", encoding="utf-8", errors="replace") as f:
                                lines = f.readlines()
                                # Reverse to show newest first
                                log_content = "".join(reversed(lines[-2000:]))
                            
                            st.text_area("File Content", log_content, height=600)
                        except Exception as e:
                            st.error(f"Error reading file: {e}")

