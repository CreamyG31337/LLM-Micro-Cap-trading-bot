#!/usr/bin/env python3
"""
Test URL Loader Utility
=======================

Utility to load obfuscated test URLs from test_urls.keys.json.
This keeps sensitive test URLs out of the codebase.
"""

import json
import base64
from pathlib import Path
from typing import Optional, Dict

_KEYS_FILE = Path(__file__).parent / "test_urls.keys.json"
_url_cache: Optional[Dict[str, str]] = None


def _load_urls() -> Dict[str, str]:
    """Load and decode URLs from keys file."""
    global _url_cache
    
    if _url_cache is not None:
        return _url_cache
    
    _url_cache = {}
    
    if not _KEYS_FILE.exists():
        raise FileNotFoundError(
            f"Test URLs keys file not found: {_KEYS_FILE}\n"
            "Create test_urls.keys.json with obfuscated URLs."
        )
    
    with open(_KEYS_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Decode all non-comment keys
    for key, value in data.items():
        if not key.startswith('_') and isinstance(value, str):
            try:
                decoded = base64.b64decode(value).decode('utf-8')
                _url_cache[key] = decoded
            except Exception as e:
                # If decoding fails, assume it's already decoded (for backwards compatibility)
                _url_cache[key] = value
    
    return _url_cache


def get_test_url(key: str) -> str:
    """
    Get a test URL by key.
    
    Args:
        key: Key name from test_urls.keys.json (e.g., 'FT_ARTICLE_1')
        
    Returns:
        Decoded URL string
        
    Raises:
        KeyError: If key not found
        FileNotFoundError: If keys file doesn't exist
    """
    urls = _load_urls()
    
    if key not in urls:
        available = ', '.join(sorted(urls.keys()))
        raise KeyError(
            f"Test URL key '{key}' not found.\n"
            f"Available keys: {available}"
        )
    
    return urls[key]


def list_test_urls() -> Dict[str, str]:
    """
    List all available test URLs.
    
    Returns:
        Dictionary mapping key names to decoded URLs
    """
    return _load_urls().copy()


def get_domain(key: str) -> str:
    """
    Get a domain name by key (for obfuscated domain references).
    
    Args:
        key: Key name from test_urls.keys.json (e.g., 'DOMAIN_SITE_A')
        
    Returns:
        Decoded domain string
        
    Raises:
        KeyError: If key not found
        FileNotFoundError: If keys file doesn't exist
    """
    return get_test_url(key)  # Reuse same decoding logic

