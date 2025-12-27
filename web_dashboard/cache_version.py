"""
Cache Version Management
========================

Provides a mechanism for background jobs to invalidate Streamlit's cache
by updating a shared version file. When jobs update portfolio data, they
bump the cache version, causing cached functions to re-fetch fresh data.

Usage in background jobs:
    from cache_version import bump_cache_version
    
    # After updating portfolio data
    bump_cache_version()

Usage in cached functions:
    from cache_version import get_cache_version
    
    @st.cache_data(ttl=300)
    def get_portfolio_data(_cache_version=None):
        if _cache_version is None:
            _cache_version = get_cache_version()
        # ... fetch data ...
"""

import os
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Cache version file location (in web_dashboard directory)
VERSION_FILE = Path(__file__).parent / ".cache_version"


def get_cache_version() -> str:
    """Get current cache version from file.
    
    Returns:
        Cache version string (timestamp or BUILD_TIMESTAMP)
    """
    try:
        if VERSION_FILE.exists():
            version = VERSION_FILE.read_text().strip()
            if version:
                return version
    except Exception as e:
        logger.debug(f"Could not read cache version file: {e}")
    
    # Fallback to BUILD_TIMESTAMP (deployment time) or current time
    return os.getenv("BUILD_TIMESTAMP", datetime.now().strftime("%Y%m%d_%H%M%S"))


def bump_cache_version() -> None:
    """Update cache version to current timestamp.
    
    Call this after updating portfolio data to invalidate Streamlit's cache.
    Safe to call even if it fails - will just log a warning.
    """
    try:
        new_version = datetime.now().isoformat()
        VERSION_FILE.write_text(new_version)
        logger.info(f"Cache version bumped to: {new_version}")
    except Exception as e:
        logger.warning(f"Failed to bump cache version: {e}")
        # Don't raise - cache bumping failure shouldn't break the job
