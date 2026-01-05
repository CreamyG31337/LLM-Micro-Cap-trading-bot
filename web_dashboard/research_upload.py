#!/usr/bin/env python3
"""
Research Report File Upload Utility
===================================

Handles uploading PDF files to server when running locally.
"""

import logging
import os
import platform
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
    # Ensure logger has a console handler if running from console app
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    
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
        # On Windows, rsync is typically not installed by default
        # scp works fine and is included with OpenSSH on Windows
        if platform.system() == "Windows":
            logger.info("ℹ️  rsync not available (using scp instead)")
        else:
            logger.info("ℹ️  rsync not available, using scp instead")
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
    import os
    
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
        
        # Handle SSH key path - normalize Windows paths
        if ssh_key_path:
            # Convert to Path object to normalize and check existence
            key_path = PathLib(ssh_key_path).expanduser().resolve()
            if key_path.exists():
                # Convert Windows path to forward slashes for SSH command
                # On Windows, SSH/rsync can handle forward slashes even for local paths
                key_path_str = str(key_path).replace('\\', '/')
                cmd.insert(1, "-e")
                cmd.insert(2, f"ssh -i {key_path_str}")
                logger.info(f"Using SSH key: {key_path_str}")
            else:
                logger.warning(f"SSH key not found at: {key_path}, will use default SSH keys or prompt for password")
        
        logger.info(f"Uploading files with rsync to {server_user}@{server_host}:{server_path}...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.debug(f"rsync output: {result.stdout}")
        logger.info("✅ Files uploaded successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else (e.stdout if e.stdout else 'Unknown error')
        logger.error(f"rsync failed: {error_msg}")
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
    
    # Ensure logger has a console handler if running from console app
    if not logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)
    
    try:
        pdf_files = list(local_dir.rglob("*.pdf"))
        
        # Handle SSH key path - normalize Windows paths
        key_path_str = None
        if ssh_key_path:
            key_path = PathLib(ssh_key_path).expanduser().resolve()
            if key_path.exists():
                # Convert Windows path to forward slashes for SSH (works on both Windows and Unix)
                key_path_str = str(key_path).replace('\\', '/')
                logger.info(f"Using SSH key: {key_path_str}")
            else:
                logger.warning(f"SSH key not found at: {key_path}, will use default SSH keys or prompt for password")
        
        logger.info(f"Found {len(pdf_files)} PDF file(s) to upload via scp")
        logger.info(f"Destination: {server_user}@{server_host}:{server_path}")
        logger.info("")
        
        for idx, pdf_file in enumerate(pdf_files, 1):
            # Get relative path to preserve folder structure
            rel_path = pdf_file.relative_to(local_dir)
            # Convert Windows path separators to forward slashes for remote path (Unix server)
            rel_path_str = str(rel_path).replace('\\', '/')
            remote_path = f"{server_path}/{rel_path_str}"
            # Remote directory path must also use forward slashes (Unix server)
            remote_dir = remote_path.rsplit('/', 1)[0] if '/' in remote_path else server_path
            
            # Build scp command
            cmd = ["scp"]
            
            if key_path_str:
                cmd.extend(["-i", key_path_str])
            
            cmd.extend([
                str(pdf_file),
                f"{server_user}@{server_host}:{remote_path}"
            ])
            
            # Create remote directory first (remote_dir already uses forward slashes)
            # Ensure remote_dir uses forward slashes (Unix server path)
            remote_dir_clean = remote_dir.replace('\\', '/')
            
            ssh_cmd = ["ssh"]
            if key_path_str:
                ssh_cmd.extend(["-i", key_path_str])
            ssh_cmd.extend([
                f"{server_user}@{server_host}",
                f"mkdir -p '{remote_dir_clean}'"  # Quote to handle any special characters
            ])
            
            logger.info(f"[{idx}/{len(pdf_files)}] 📤 Uploading {pdf_file.name}...")
            logger.info(f"    → {remote_path}")
            try:
                # Create directory first
                logger.debug(f"  Creating remote directory: {remote_dir_clean}")
                mkdir_result = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True, timeout=30)
                if mkdir_result.stderr and mkdir_result.stderr.strip():
                    logger.debug(f"  mkdir stderr: {mkdir_result.stderr}")
                
                # Upload file with progress indication
                logger.info(f"    ⏳ Transferring...")
                scp_result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=300)
                logger.info(f"    ✅ Upload complete")
            except subprocess.TimeoutExpired:
                logger.error(f"  ❌ Timeout uploading {pdf_file.name} (exceeded 5 minutes)")
                return False
            except subprocess.CalledProcessError as e:
                # Extract meaningful error information
                error_detail = ""
                if e.stderr:
                    error_detail = e.stderr.strip()
                elif e.stdout:
                    error_detail = e.stdout.strip()
                else:
                    error_detail = f"Exit code {e.returncode}"
                
                logger.error(f"  ❌ Failed to upload {pdf_file.name}")
                logger.error(f"     Remote path: {remote_path}")
                if "ssh" in str(e.cmd[0] if e.cmd else ""):
                    logger.error(f"     Failed at: Creating remote directory")
                    logger.error(f"     Directory: {remote_dir_clean}")
                else:
                    logger.error(f"     Failed at: File upload")
                logger.error(f"     Error: {error_detail[:300]}")  # Limit error message length
                return False
        
        logger.info(f"✅ All {len(pdf_files)} file(s) uploaded successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else (e.stdout if e.stdout else str(e))
        logger.error(f"scp failed: {error_msg}")
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
    # Default to ai-trading-www/research to match web server path
    path = os.environ.get("RESEARCH_SERVER_PATH", "/home/lance/ai-trading-www/research")
    key = os.environ.get("RESEARCH_SSH_KEY_PATH")
    
    if not host or not user:
        logger.debug("Server config not found: RESEARCH_SERVER_HOST or RESEARCH_SERVER_USER not set")
        return None
    
    # Normalize SSH key path if provided
    normalized_key = None
    if key:
        from pathlib import Path as PathLib
        try:
            # Expand user home directory (~) and resolve to absolute path
            # Handle Windows paths (backslashes) properly
            key_path = PathLib(key).expanduser().resolve()
            if key_path.exists():
                normalized_key = str(key_path)
                logger.info(f"✅ SSH key found: {normalized_key}")
            else:
                logger.warning(f"⚠️  SSH key path not found: {key_path}")
                logger.warning(f"   Original path from env: {key}")
                logger.warning(f"   Will try to use default SSH keys or password authentication")
        except Exception as e:
            logger.warning(f"⚠️  Error resolving SSH key path '{key}': {e}")
            logger.warning(f"   Will try to use default SSH keys or password authentication")
    else:
        logger.info("ℹ️  No SSH key specified (RESEARCH_SSH_KEY_PATH not set)")
        logger.info("   Will use default SSH keys or password authentication")
    
    return {
        "host": host,
        "user": user,
        "path": path,
        "ssh_key": normalized_key if normalized_key else key  # Return original if normalization failed
    }

