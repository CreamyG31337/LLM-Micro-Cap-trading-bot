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
    
    def format_size(size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
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
        
        # Calculate total size for progress
        total_size = sum(f.stat().st_size for f in pdf_files)
        logger.info(f"Total size: {format_size(total_size)}")
        logger.info("")
        
        success_count = 0
        failed_files = []
        
        for idx, pdf_file in enumerate(pdf_files, 1):
            # Get relative path to preserve folder structure
            rel_path = pdf_file.relative_to(local_dir)
            # Convert Windows path separators to forward slashes for remote path (Unix server)
            rel_path_str = str(rel_path).replace('\\', '/')
            remote_path = f"{server_path}/{rel_path_str}"
            # Remote directory path must also use forward slashes (Unix server)
            remote_dir = remote_path.rsplit('/', 1)[0] if '/' in remote_path else server_path
            
            # Get file size
            file_size = pdf_file.stat().st_size
            file_size_str = format_size(file_size)
            
            # Build scp command
            cmd = ["scp"]
            
            if key_path_str:
                cmd.extend(["-i", key_path_str])
            
            # Add compression for large files
            if file_size > 1024 * 1024:  # > 1MB
                cmd.append("-C")  # Enable compression
            
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
            
            logger.info(f"[{idx}/{len(pdf_files)}] 📤 Uploading {pdf_file.name} ({file_size_str})...")
            logger.info(f"    → {remote_path}")
            
            # Retry logic
            max_retries = 3
            upload_success = False
            
            for attempt in range(1, max_retries + 1):
                try:
                    # Create directory first (only on first attempt)
                    if attempt == 1:
                        logger.debug(f"  Creating remote directory: {remote_dir_clean}")
                        mkdir_result = subprocess.run(ssh_cmd, check=True, capture_output=True, text=True, timeout=30)
                        if mkdir_result.stderr and mkdir_result.stderr.strip():
                            logger.debug(f"  mkdir stderr: {mkdir_result.stderr}")
                    
                    # Upload file with progress indication
                    # Timeout: 30 minutes for large files (1800 seconds)
                    # Calculate timeout based on file size: 1 minute per MB, minimum 5 minutes, maximum 30 minutes
                    timeout_seconds = max(300, min(1800, int(file_size / (1024 * 1024) * 60)))
                    
                    if attempt > 1:
                        logger.info(f"    🔄 Retry {attempt}/{max_retries}...")
                    else:
                        logger.info(f"    ⏳ Transferring (timeout: {timeout_seconds // 60} min)...")
                    
                    scp_result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout_seconds)
                    logger.info(f"    ✅ Upload complete")
                    upload_success = True
                    success_count += 1
                    break
                    
                except subprocess.TimeoutExpired:
                    if attempt < max_retries:
                        logger.warning(f"    ⚠️  Timeout (attempt {attempt}/{max_retries}), retrying...")
                        continue
                    else:
                        logger.error(f"  ❌ Timeout uploading {pdf_file.name} (exceeded {timeout_seconds // 60} minutes after {max_retries} attempts)")
                        failed_files.append((pdf_file.name, "Timeout"))
                except subprocess.CalledProcessError as e:
                    # Extract meaningful error information
                    error_detail = ""
                    if e.stderr:
                        error_detail = e.stderr.strip()
                    elif e.stdout:
                        error_detail = e.stdout.strip()
                    else:
                        error_detail = f"Exit code {e.returncode}"
                    
                    if attempt < max_retries:
                        logger.warning(f"    ⚠️  Upload failed (attempt {attempt}/{max_retries}): {error_detail[:100]}")
                        logger.info(f"    🔄 Retrying...")
                        continue
                    else:
                        logger.error(f"  ❌ Failed to upload {pdf_file.name} after {max_retries} attempts")
                        logger.error(f"     Remote path: {remote_path}")
                        if "ssh" in str(e.cmd[0] if e.cmd else ""):
                            logger.error(f"     Failed at: Creating remote directory")
                            logger.error(f"     Directory: {remote_dir_clean}")
                        else:
                            logger.error(f"     Failed at: File upload")
                        logger.error(f"     Error: {error_detail[:300]}")  # Limit error message length
                        failed_files.append((pdf_file.name, error_detail[:100]))
            
            if not upload_success:
                logger.info("")  # Blank line after failed file
        
        # Summary
        logger.info("")
        logger.info("=" * 70)
        if success_count == len(pdf_files):
            logger.info(f"✅ All {success_count} file(s) uploaded successfully")
            return True
        else:
            logger.info(f"⚠️  Upload summary: {success_count}/{len(pdf_files)} file(s) succeeded")
            if failed_files:
                logger.info(f"   Failed files:")
                for filename, error in failed_files:
                    logger.info(f"     - {filename}: {error}")
            return False
        
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

