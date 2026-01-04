#!/usr/bin/env python3
"""
Archive Service Utility
=======================

Integration with archive.is, archive.ph, and archive.md for bypassing paywalls.
These are mirrors of the same service (archive.today) that capture web page snapshots.

Features:
- Check if a URL is already archived
- Submit URLs for archiving
- Extract content from archived pages
- Handle rate limiting and retries
"""

import logging
import time
from typing import Optional
from urllib.parse import quote, urlparse

# Use curl_cffi to bypass TLS fingerprinting (JA3)
from curl_cffi import requests

logger = logging.getLogger(__name__)

# Create a session to maintain cookies and connection pooling
_session = None

def _get_session() -> requests.Session:
    """Get or create a curl_cffi session with browser impersonation."""
    global _session
    if _session is None:
        # Use 'edge' impersonation which was verified to work against archive.is rate limiting
        _session = requests.Session(impersonate="edge")
        # Set default headers for all requests in this session
        _session.headers.update(_get_browser_headers())
    return _session

# Archive service domains (mirrors of the same service)
# Try archive.ph first as it's often more lenient with rate limiting
ARCHIVE_DOMAINS = [
    'archive.ph',  # Try this first
    'archive.is',
    'archive.md',
]

# Rate limiting: max 1 submission per second
_last_submission_time = 0
_submission_rate_limit = 1.0  # seconds


def _rate_limit_submission() -> None:
    """Enforce rate limiting for archive submissions."""
    global _last_submission_time
    current_time = time.time()
    time_since_last = current_time - _last_submission_time
    
    if time_since_last < _submission_rate_limit:
        sleep_time = _submission_rate_limit - time_since_last
        logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
        time.sleep(sleep_time)
    
    _last_submission_time = time.time()


def check_archived(url: str, timeout: int = 10) -> Optional[str]:
    """Get archive URL using /newest/ endpoint.
    
    The /newest/ endpoint automatically serves archived content if available,
    or archives it on-the-fly. We use this URL directly without checking first.
    
    Args:
        url: Original article URL
        timeout: Request timeout in seconds (not used for URL construction)
        
    Returns:
        Archive URL using /newest/ endpoint, or None if URL is invalid
    """
    if not url:
        return None
    
    # Use /newest/ endpoint which works directly - no need to check first
    # Try archive.ph first as it's often most reliable
    for domain in ARCHIVE_DOMAINS:
        # Construct the /newest/ URL - this will work if archived or archive on-the-fly
        archive_url = f"https://{domain}/newest/{url}"
        logger.debug(f"Using archive URL: {archive_url}")
        return archive_url
    
    return None


def submit_for_archiving(url: str, timeout: int = 30) -> bool:
    """Submit a URL to archive service using /newest/ endpoint.
    
    The /newest/ endpoint automatically archives the URL if not already archived.
    Since we now use /newest/ directly in check_archived, this function
    is mainly for explicit submission tracking. The actual archiving happens
    when we access the /newest/ URL.
    
    Args:
        url: URL to archive
        timeout: Request timeout in seconds
        
    Returns:
        True (always succeeds since /newest/ handles it automatically)
    """
    if not url:
        return False
    
    # The /newest/ endpoint handles archiving automatically, so we just
    # need to construct the URL. The actual archiving happens when accessed.
    logger.info(f"URL will be archived via /newest/ endpoint when accessed: {url}")
    return True


def _get_browser_headers() -> dict:
    """Get browser-like headers to avoid rate limiting."""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
    }


def get_archived_content(archived_url: str, timeout: int = 30) -> Optional[str]:
    """Extract content from an archived page.
    
    This fetches the raw HTML from the archive URL. The /newest/ endpoint
    will either serve existing archived content or archive it on-the-fly.
    Uses browser-like headers and session to avoid rate limiting.
    
    Args:
        archived_url: URL of archived page (should be /newest/ format)
        timeout: Request timeout in seconds
        
    Returns:
        Raw HTML content, or None if failed
    """
    if not archived_url:
        return None
    
    try:
        logger.debug(f"Fetching archived content from {archived_url}")
        session = _get_session()
        
        # Add Referer header pointing to the original site
        # This makes the request look more legitimate
        headers = _get_browser_headers().copy()
        try:
            from urllib.parse import urlparse
            parsed = urlparse(archived_url)
            # Extract original URL from archive URL (format: /newest/{original_url})
            if '/newest/' in parsed.path:
                original_url = parsed.path.split('/newest/', 1)[1]
                if original_url.startswith('http'):
                    headers['Referer'] = original_url
        except Exception:
            pass  # If we can't parse, just continue without Referer
        
        # Use session to maintain cookies and connection
        response = session.get(
            archived_url,
            timeout=timeout,
            allow_redirects=True,  # Follow redirects automatically
            headers=headers
        )
        
        if response.status_code == 200:
            return response.text
        elif response.status_code == 429:
            # Log response body to see if there's more info
            try:
                error_msg = response.text[:200] if response.text else "No error message"
                logger.warning(f"Rate limited when fetching archived content (429): {error_msg}")
            except Exception:
                logger.warning(f"Rate limited when fetching archived content (429)")
            return None
        else:
            logger.warning(f"Failed to fetch archived content: status {response.status_code}")
            # Log response body for debugging
            try:
                if response.text:
                    logger.debug(f"Response body: {response.text[:500]}")
            except Exception:
                pass
            return None
            
    except (requests.errors.RequestsError, requests.errors.CurlError) as e:
        logger.warning(f"Error fetching archived content: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching archived content: {e}")
        return None

