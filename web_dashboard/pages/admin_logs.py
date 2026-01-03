#!/usr/bin/env python3
import streamlit as st
import os
import glob
from pathlib import Path
import time

st.set_page_config(layout="wide", page_title="Admin: Log Viewer", page_icon="📜")

# Add parent directory to path to allow imports
import sys
sys.path.append(str(Path(__file__).parent.parent))

from navigation import render_navigation
render_navigation()

st.title("📜 System Logs Viewer")

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
