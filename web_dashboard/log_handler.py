#!/usr/bin/env python3
"""
In-memory log handler for capturing application logs.
Provides a thread-safe circular buffer for recent log messages.
"""

import logging
from collections import deque
import threading
from datetime import datetime
from typing import List, Dict


class PacificTimeFormatter(logging.Formatter):
    """Custom formatter that displays timestamps in Pacific Time."""
    
    def formatTime(self, record, datefmt=None):
        """Override formatTime to use Pacific Time."""
        try:
            from zoneinfo import ZoneInfo
            pacific = ZoneInfo("America/Vancouver")
            dt = datetime.fromtimestamp(record.created, tz=pacific)
        except (ImportError, Exception):
            # Fallback if zoneinfo not available
            from datetime import timezone, timedelta
            # Pacific is UTC-8 (PST) or UTC-7 (PDT)
            # This is a simple approximation - doesn't handle DST perfectly
            pacific_offset = timedelta(hours=-8)
            dt = datetime.fromtimestamp(record.created, tz=timezone(pacific_offset))
        
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')


class InMemoryLogHandler(logging.Handler):
    """Custom logging handler that stores recent log messages in memory.
    
    Thread-safe circular buffer with configurable size. Useful for
    displaying logs in web UI without file system access.
    """
    
    def __init__(self, maxlen=500):
        super().__init__()
        self.log_records = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        
        # Set a formatter with Pacific Time
        formatter = PacificTimeFormatter(
            '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.setFormatter(formatter)
    
    def emit(self, record):
        """Store formatted log record in buffer."""
        try:
            msg = self.format(record)
            with self.lock:
                self.log_records.append({
                    'timestamp': datetime.fromtimestamp(record.created),
                    'level': record.levelname,
                    'module': record.name,
                    'message': record.getMessage(),
                    'formatted': msg
                })
        except Exception:
            self.handleError(record)
    
    def get_logs(self, n=None, level=None, module=None, search=None) -> List[Dict]:
        """Get recent log records with optional filtering.
        
        Args:
            n: Number of recent logs to return (None = all)
            level: Filter by log level (e.g., 'INFO', 'ERROR')
            module: Filter by module name (partial match)
            search: Filter by message text (case-insensitive)
            
        Returns:
            List of log record dictionaries
        """
        with self.lock:
            logs = list(self.log_records)
        
        # Apply filters
        if level:
            logs = [log for log in logs if log['level'] == level]
        
        if module:
            logs = [log for log in logs if module.lower() in log['module'].lower()]
        
        if search:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log['message'].lower()]
        
        # Return last n logs
        if n:
            logs = logs[-n:]
        
        return logs
    
    def get_formatted_logs(self, n=None, level=None, module=None, search=None) -> List[str]:
        """Get formatted log strings (for download/display).
        
        Args:
            Same as get_logs()
            
        Returns:
            List of formatted log strings
        """
        logs = self.get_logs(n=n, level=level, module=module, search=search)
        return [log['formatted'] for log in logs]
    
    def clear(self):
        """Clear all log records."""
        with self.lock:
            self.log_records.clear()


# Global handler instance
_log_handler = None


def get_log_handler() -> InMemoryLogHandler:
    """Get the global in-memory log handler instance.
    
    Returns:
        InMemoryLogHandler instance
    """
    global _log_handler
    if _log_handler is None:
        _log_handler = InMemoryLogHandler(maxlen=500)
    return _log_handler


def setup_logging(level=logging.INFO):
    """Setup logging with file handler for app modules.
    
    Uses FileHandler to write to logs/app.log to avoid deadlocks.
    Attached only to app-specific loggers, not root logger.
    
    Args:
        level: Log level (default: INFO)
    """
    import os
    
    # Ensure logs directory exists
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'app.log')
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(PacificTimeFormatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    file_handler.setLevel(level)
    
    # List of our application module names to capture logs from
    app_modules = [
        'app',  # For log_message() calls from streamlit_app.py
        'streamlit_utils',
        'chart_utils', 
        'auth_utils',
        'supabase_client',
        'exchange_rates_utils',
        'scheduler',
        'scheduler.scheduler_core',
        'scheduler.jobs',
        'log_handler',
        '__main__',
        'web_dashboard',
    ]
    
    # Attach handler to each app module logger
    for module_name in app_modules:
        logger = logging.getLogger(module_name)
        
        # Remove existing handlers to avoid duplicates
        # We also remove StreamHandlers if any, to avoid console noise/lag
        for h in logger.handlers[:]:
            logger.removeHandler(h)
        
        # Add our file handler
        logger.addHandler(file_handler)
        logger.setLevel(level)
        
        # Disable propagation to prevent Streamlit interference
        logger.propagate = False
        
    # Also initialize the global InMemoryLogHandler for backward compatibility
    # (some code might still use log_handler.log_records directly)
    # But it won't receive new logs unless we also attach it.
    # For now, let's just stick to FileHandler as the source of truth.


def read_logs_from_file(n=100, level=None, search=None) -> List[Dict]:
    """Read recent logs from the log file.
    
    Args:
        n: Number of recent logs to return
        level: Filter by log level
        search: Filter by message text
        
    Returns:
        List of dicts with timestamp, level, module, message keys
    """
    import os
    
    log_file = os.path.join(os.path.dirname(__file__), 'logs', 'app.log')
    if not os.path.exists(log_file):
        return []
        
    logs = []
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            # Read all lines (for simple implementation)
            # For massive logs, we'd use seek() from end, but rotation checks are better
            lines = f.readlines()
            
        # Parse lines
        for line in lines:
            try:
                # Expected format: YYYY-MM-DD HH:MM:SS | LEVEL    | module | message
                parts = line.split(' | ', 3)
                if len(parts) == 4:
                    timestamp_str, level_str, module, message = parts
                    
                    # Store
                    logs.append({
                        'timestamp': datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S'),
                        'level': level_str.strip(),
                        'module': module.strip(),
                        'message': message.strip(),
                        'formatted': line.strip()
                    })
            except Exception:
                continue # Skip malformed lines
                
        # Apply filters
        if level:
            logs = [log for log in logs if log['level'] == level]
        
        if search:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log['message'].lower()]
            
        # Return last n
        if n:
            logs = logs[-n:]
            
        return logs
        
    except Exception as e:
        print(f"Error reading log file: {e}")
        return []

def log_message(message: str, level: str = 'INFO', module: str = 'app'):
    """Convenience function to log a message."""
    logger = logging.getLogger(module)
    if hasattr(logging, level.upper()):
        log_level = getattr(logging, level.upper())
    else:
        log_level = logging.INFO
    logger.log(log_level, message)


def log_execution_time(module_name=None):
    """Decorator to log execution time of functions.
    
    Args:
        module_name: Optional module name for log record. 
                    If None, uses function's module.
    """
    import time
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                # Determine module name
                mod = module_name or func.__module__
                
                # Use INFO for slow ops (>1s), DEBUG for fast ones
                level = 'INFO' if duration > 1.0 else 'DEBUG'
                msg = f"PERF: {func.__name__} took {duration:.3f}s"
                
                log_message(msg, level=level, module=mod)
        return wrapper
    return decorator
