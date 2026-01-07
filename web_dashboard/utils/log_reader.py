"""
Log Reader Utility
==================

Utility functions for reading and analyzing application logs.
Can be used by AI assistants to automatically check for errors.
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re


def get_log_file_path() -> Path:
    """Get the path to the main application log file."""
    # Get web_dashboard directory
    current_file = Path(__file__).resolve()
    web_dashboard_dir = current_file.parent.parent
    log_file = web_dashboard_dir / 'logs' / 'app.log'
    return log_file


def read_recent_errors(
    hours: int = 24,
    max_lines: int = 100,
    include_warnings: bool = True
) -> List[Dict[str, str]]:
    """Read recent error and warning logs.
    
    Args:
        hours: Number of hours to look back
        max_lines: Maximum number of error lines to return
        include_warnings: Include WARNING level logs
        
    Returns:
        List of error log entries with keys: timestamp, level, module, message, formatted
    """
    log_file = get_log_file_path()
    
    if not log_file.exists():
        return []
    
    errors = []
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    try:
        # Read file from end (more efficient for large files)
        file_size = log_file.stat().st_size
        # Read last 5MB or entire file, whichever is smaller
        read_size = min(5 * 1024 * 1024, file_size)
        
        with open(log_file, 'rb') as f:
            f.seek(max(0, file_size - read_size))
            buffer = f.read().decode('utf-8', errors='ignore')
        
        lines = buffer.split('\n')
        # Skip first line if we didn't start at beginning (might be partial)
        if file_size > read_size:
            lines = lines[1:]
        
        # Parse lines in reverse (most recent first)
        for line in reversed(lines):
            if len(errors) >= max_lines:
                break
            
            line = line.strip()
            if not line:
                continue
            
            # Parse log format: YYYY-MM-DD HH:MM:SS | LEVEL | module | message
            try:
                parts = line.split(' | ', 3)
                if len(parts) == 4:
                    timestamp_str, level_str, module, message = parts
                    
                    # Parse timestamp
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue
                    
                    # Check if within time range
                    if timestamp < cutoff_time:
                        continue
                    
                    # Filter by level
                    level = level_str.strip()
                    if level == 'ERROR' or (include_warnings and level == 'WARNING'):
                        errors.append({
                            'timestamp': timestamp_str,
                            'level': level,
                            'module': module.strip(),
                            'message': message.strip(),
                            'formatted': line
                        })
            except Exception:
                continue
        
        # Return in chronological order (oldest first)
        return list(reversed(errors))
        
    except Exception as e:
        return [{
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'level': 'ERROR',
            'module': 'log_reader',
            'message': f'Failed to read log file: {e}',
            'formatted': f'ERROR reading logs: {e}'
        }]


def search_logs(
    search_term: str,
    hours: int = 24,
    max_lines: int = 50,
    case_sensitive: bool = False
) -> List[Dict[str, str]]:
    """Search logs for a specific term.
    
    Args:
        search_term: Text to search for
        hours: Number of hours to look back
        max_lines: Maximum number of matching lines to return
        case_sensitive: Whether search should be case sensitive
        
    Returns:
        List of matching log entries
    """
    log_file = get_log_file_path()
    
    if not log_file.exists():
        return []
    
    matches = []
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    if not case_sensitive:
        search_term = search_term.lower()
    
    try:
        file_size = log_file.stat().st_size
        read_size = min(5 * 1024 * 1024, file_size)
        
        with open(log_file, 'rb') as f:
            f.seek(max(0, file_size - read_size))
            buffer = f.read().decode('utf-8', errors='ignore')
        
        lines = buffer.split('\n')
        if file_size > read_size:
            lines = lines[1:]
        
        for line in reversed(lines):
            if len(matches) >= max_lines:
                break
            
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains search term
            line_lower = line if case_sensitive else line.lower()
            if search_term not in line_lower:
                continue
            
            # Parse log format
            try:
                parts = line.split(' | ', 3)
                if len(parts) == 4:
                    timestamp_str, level_str, module, message = parts
                    
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    except:
                        continue
                    
                    if timestamp < cutoff_time:
                        continue
                    
                    matches.append({
                        'timestamp': timestamp_str,
                        'level': level_str.strip(),
                        'module': module.strip(),
                        'message': message.strip(),
                        'formatted': line
                    })
            except Exception:
                # Include unparsed lines that match
                matches.append({
                    'timestamp': 'N/A',
                    'level': 'UNKNOWN',
                    'module': '',
                    'message': line,
                    'formatted': line
                })
        
        return list(reversed(matches))
        
    except Exception as e:
        return []


def get_recent_job_errors(job_name: Optional[str] = None, hours: int = 24) -> List[Dict[str, str]]:
    """Get recent errors related to scheduled jobs.
    
    Args:
        job_name: Specific job name to filter by (e.g., 'update_portfolio_prices')
        hours: Number of hours to look back
        
    Returns:
        List of error log entries
    """
    if job_name:
        # Search for specific job
        search_terms = [
            job_name,
            job_name.replace('_', ' '),
            f"job.*{job_name}",
            f"scheduler.*{job_name}"
        ]
        all_errors = []
        for term in search_terms:
            errors = search_logs(term, hours=hours, max_lines=20)
            all_errors.extend(errors)
        # Deduplicate
        seen = set()
        unique_errors = []
        for error in all_errors:
            key = error['formatted']
            if key not in seen:
                seen.add(key)
                unique_errors.append(error)
        return unique_errors
    else:
        # Get all job-related errors
        return search_logs('scheduler|job|update_portfolio|performance_metrics', hours=hours, max_lines=50)


def format_errors_for_display(errors: List[Dict[str, str]]) -> str:
    """Format error list for easy reading.
    
    Args:
        errors: List of error dictionaries
        
    Returns:
        Formatted string
    """
    if not errors:
        return "No errors found."
    
    lines = [f"Found {len(errors)} error(s):\n"]
    
    for i, error in enumerate(errors, 1):
        lines.append(f"{i}. [{error['timestamp']}] [{error['level']}] {error['module']}")
        lines.append(f"   {error['message']}")
        lines.append("")
    
    return "\n".join(lines)


# Convenience function for AI to use
def check_recent_errors(hours: int = 24) -> str:
    """Check for recent errors - convenience function for AI assistants.
    
    Args:
        hours: Number of hours to look back
        
    Returns:
        Formatted string of recent errors
    """
    errors = read_recent_errors(hours=hours, max_lines=50, include_warnings=True)
    return format_errors_for_display(errors)

