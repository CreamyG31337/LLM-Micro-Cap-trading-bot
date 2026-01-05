#!/usr/bin/env python3
"""
Research Report File Upload Utility
===================================

Handles uploading PDF files to server when running locally.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_running_locally() -> bool:
    """
    Detect if code is running locally vs on server.
    
    Returns:
        True if running locally, False if on server
    """
    # Check for server environment indicators
    server_indicators = [
        os.environ.get('DOCKER_CONTAINER') is not None,
        os.environ.get('CI') is not None,
        os.environ.get('VERCEL') is not None,
        os.environ.get('HEROKU') is not None,
        os.environ.get('AWS_LAMBDA_FUNCTION_NAME') is not None,
    ]
    
    if any(server_indicators):
        return False
    
    # Check if we're on Windows (likely local dev)
    import platform
    if platform.system() == 'Windows':
        return True
    
    # Check hostname (simple heuristic - adjust as needed)
    import socket
    hostname = socket.gethostname().lower()
    if 'localhost' in hostname or 'local' in hostname:
        return True
    
    # Default: assume local if no server indicators
    return True


def upload_research_files_to_server(
    local_research_dir,
    server_host: str,
    server_user: str,
    server_path: str,
    ssh_key_path: Optional[str] = None
) -> bool:
    """
    Upload Research PDF files to server using rsync or scp.
    
    Args:
        local_research_dir: Local Research directory path (Path object or string)
        server_host: Server hostname or IP
        server_user: SSH username
        server_path: Remote path (e.g., /home/user/ai-trading/Research)
        ssh_key_path: Optional path to SSH private key
        
    Returns:
        True if successful, False otherwise
    """
    # Convert to Path if needed (avoid scoping issues)
    from pathlib import Path as PathLib
    if not isinstance(local_research_dir, PathLib):
        local_research_dir = PathLib(local_research_dir)
    
    if not local_research_dir.exists():
        logger.error(f"Local Research directory not found: {local_research_dir}")
        return False
    
    # Find all PDF files
    pdf_files = list(local_research_dir.rglob("*.pdf"))
    if not pdf_files:
        logger.info("No PDF files found to upload")
        return True  # Not an error, just nothing to upload
    
    logger.info(f"Found {len(pdf_files)} PDF file(s) to upload")
    
    # Try rsync first (more efficient), fallback to scp
    rsync_available = _check_command_available("rsync")
    
    if rsync_available:
        return _upload_with_rsync(local_research_dir, server_host, server_user, server_path, ssh_key_path)
    else:
        logger.warning("rsync not available, falling back to scp")
        return _upload_with_scp(local_research_dir, server_host, server_user, server_path, ssh_key_path)


def _check_command_available(command: str) -> bool:
    """Check if a command is available in PATH."""
    try:
        subprocess.run([command, "--version"], capture_output=True, check=True, timeout=5)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _upload_with_rsync(
    local_dir,
    server_host: str,
    server_user: str,
    server_path: str,
    ssh_key_path: Optional[str]
) -> bool:
    """Upload using rsync."""
    # Import Path locally to avoid scoping issues
    from pathlib import Path as PathLib
    
    try:
        # Build rsync command
        cmd = [
            "rsync",
            "-avz",  # archive, verbose, compress
            "--progress",
            "--include=*/",
            "--include=*.pdf",
            "--exclude=*",
            f"{local_dir}/",
            f"{server_user}@{server_host}:{server_path}/"
        ]
        
        if ssh_key_path and PathLib(ssh_key_path).exists():
            cmd.insert(1, "-e")
            cmd.insert(2, f"ssh -i {ssh_key_path}")
        
        logger.info(f"Uploading files with rsync to {server_user}@{server_host}:{server_path}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.debug(f"rsync output: {result.stdout}")
        logger.info("✅ Files uploaded successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"rsync failed: {e.stderr if e.stderr else 'Unknown error'}")
        return False
    except Exception as e:
        logger.error(f"Error during rsync upload: {e}")
        return False


def _upload_with_scp(
    local_dir,
    server_host: str,
    server_user: str,
    server_path: str,
    ssh_key_path: Optional[str]
) -> bool:
    """Upload using scp (fallback)."""
    # Import Path locally to avoid scoping issues
    from pathlib import Path as PathLib
    
    try:
        pdf_files = list(local_dir.rglob("*.pdf"))
        
        for pdf_file in pdf_files:
            # Get relative path to preserve folder structure
            rel_path = pdf_file.relative_to(local_dir)
            remote_path = f"{server_path}/{rel_path}"
            remote_dir = str(PathLib(remote_path).parent)
            
            # Build scp command
            cmd = ["scp"]
            
            if ssh_key_path and PathLib(ssh_key_path).exists():
                cmd.extend(["-i", ssh_key_path])
            
            cmd.extend([
                str(pdf_file),
                f"{server_user}@{server_host}:{remote_path}"
            ])
            
            # Create remote directory first
            ssh_cmd = ["ssh"]
            if ssh_key_path and PathLib(ssh_key_path).exists():
                ssh_cmd.extend(["-i", ssh_key_path])
            ssh_cmd.extend([
                f"{server_user}@{server_host}",
                f"mkdir -p {remote_dir}"
            ])
            
            logger.info(f"Uploading {pdf_file.name}...")
            subprocess.run(ssh_cmd, check=True, capture_output=True)
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"✅ Uploaded: {pdf_file.name}")
        
        logger.info("✅ All files uploaded successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"scp failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Error during scp upload: {e}")
        return False


def get_server_config() -> Optional[dict]:
    """
    Get server configuration from environment variables.
    
    Returns:
        Dictionary with server config or None if not configured
    """
    host = os.environ.get("RESEARCH_SERVER_HOST")
    user = os.environ.get("RESEARCH_SERVER_USER")
    path = os.environ.get("RESEARCH_SERVER_PATH", "/home/lance/ai-trading/Research")
    key = os.environ.get("RESEARCH_SSH_KEY_PATH")
    
    if not host or not user:
        return None
    
    return {
        "host": host,
        "user": user,
        "path": path,
        "ssh_key": key
    }

