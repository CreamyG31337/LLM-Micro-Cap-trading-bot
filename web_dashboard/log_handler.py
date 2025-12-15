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
    """Setup logging with in-memory handler.
    
    Args:
        level: Log level (default: INFO)
    """
    handler = get_log_handler()
    handler.setLevel(level)
    
    # Get root logger
    root_logger = logging.getLogger()
    
    # Remove existing handlers to avoid duplicates
    for existing_handler in root_logger.handlers[:]:
        if isinstance(existing_handler, InMemoryLogHandler):
            root_logger.removeHandler(existing_handler)
    
    # Add our handler
    root_logger.addHandler(handler)
    root_logger.setLevel(level)
