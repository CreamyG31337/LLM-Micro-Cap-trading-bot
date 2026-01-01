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
            
            # Create mapping
            name_to_id = {c.name: c.id for c in containers}
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                selected_container_name = st.selectbox("Select Container", container_names, index=0 if container_names else None)
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
    else:
        # Get list of log files (recursive to find server/ollama.log)
        log_files = list(LOGS_DIR.rglob("*.log"))
        log_files.extend(list(LOGS_DIR.rglob("*.txt")))

        if not log_files:
            st.warning("No log files found in logs directory.")
        else:
            # Sort by modification time (newest first)
            log_files.sort(key=os.path.getmtime, reverse=True)
            
            # Create filenames list for dropdown (relative to logs dir)
            filenames = [str(f.relative_to(LOGS_DIR)) for f in log_files]
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                selected_filename = st.selectbox("Select Log File", filenames)
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
                        log_content = "".join(lines[-2000:])
                    
                    st.text_area("File Content", log_content, height=600)
                except Exception as e:
                    st.error(f"Error reading file: {e}")
