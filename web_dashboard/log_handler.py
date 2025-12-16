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


class InMemoryLogHandler(logging.Handler):
    """Custom logging handler that stores recent log messages in memory.
    
    Thread-safe circular buffer with configurable size. Useful for
    displaying logs in web UI without file system access.
    """
    
    def __init__(self, maxlen=500):
        super().__init__()
        self.log_records = deque(maxlen=maxlen)
        self.lock = threading.Lock()
        
        # Set a formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
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
    """Setup logging with in-memory handler for app modules only.
    
    IMPORTANT: We do NOT attach to the root logger to avoid interfering
    with Streamlit's internal logging, which can cause deadlocks.
    Instead, we only capture logs from our own application modules.
    
    Args:
        level: Log level (default: INFO)
    """
    handler = get_log_handler()
    handler.setLevel(level)
    
    # List of our application module names to capture logs from
    # These are the logger names used by logging.getLogger(__name__) in our code
    app_modules = [
        'streamlit_utils',
        'chart_utils', 
        'auth_utils',
        'supabase_client',
        'exchange_rates_utils',
        'scheduler',
        'scheduler.scheduler_core',
        'log_handler',
        '__main__',
        'web_dashboard',
    ]
    
    # Attach handler to each app module logger (NOT the root logger)
    for module_name in app_modules:
        logger = logging.getLogger(module_name)
        
        # Remove existing InMemoryLogHandler to avoid duplicates
        for existing_handler in logger.handlers[:]:
            if isinstance(existing_handler, InMemoryLogHandler):
                logger.removeHandler(existing_handler)
        
        # Add our handler
        logger.addHandler(handler)
        logger.setLevel(level)
        
        # Disable propagation to root logger to prevent Streamlit interference
        logger.propagate = False


def log_message(message: str, level: str = 'INFO', module: str = 'app'):
    """Convenience function to log a message directly to the in-memory handler.
    
    Use this when you want to ensure a message appears in the admin logs
    without relying on the logging module hierarchy.
    
    Args:
        message: The message to log
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        module: Module name to associate with log
    """
    handler = get_log_handler()
    
    # Create a log record manually
    record = logging.LogRecord(
        name=module,
        level=getattr(logging, level.upper(), logging.INFO),
        pathname='',
        lineno=0,
        msg=message,
        args=(),
        exc_info=None
    )
    
    handler.emit(record)

