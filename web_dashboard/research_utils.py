#!/usr/bin/env python3
"""
Research Utilities
==================

Helper functions for extracting and processing research articles.
"""

import logging
import re
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse

try:
    import trafilatura
except ImportError:
    trafilatura = None
    logging.warning("trafilatura not installed - article extraction will fail")

logger = logging.getLogger(__name__)


def is_domain_blacklisted(url: str, blacklist: list[str]) -> tuple[bool, str]:
    """Check if URL's domain is in the blacklist.
    
    Args:
        url: URL to check
        blacklist: List of blacklisted domains (e.g., ['msn.com', 'reuters.com'])
        
    Returns:
        Tuple of (is_blacklisted, domain)
    """
    domain = extract_source_from_url(url)
    
    # Check if domain matches any blacklisted domain
    for blocked_domain in blacklist:
        # Case-insensitive match
        if domain.lower() == blocked_domain.lower():
            return (True, domain)
    
    return (False, domain)


def extract_article_content(url: str) -> Dict[str, Any]:

    """Extract article content from URL using Trafilatura.
    
    Args:
        url: Article URL to extract content from
        
    Returns:
        Dictionary with keys:
        - title: Article title
        - content: Full article text
        - published_at: Published date (datetime or None)
        - source: Source name extracted from URL
        - success: Boolean indicating success
        - error: Error type if failed ('download_failed', 'extraction_empty', 'extraction_error')
    """
    if not trafilatura:
        logger.error("trafilatura not installed - cannot extract article content")
        return {
            'title': '',
            'content': '',
            'published_at': None,
            'source': extract_source_from_url(url),
            'success': False,
            'error': 'extraction_error'
        }
    
    try:
        # Download and extract content
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            logger.warning(f"Failed to download content from {url}")
            return {
                'title': '',
                'content': '',
                'published_at': None,
                'source': extract_source_from_url(url),
                'success': False,
                'error': 'download_failed'
            }
        
        # Extract article data
        extracted = trafilatura.extract(
            downloaded,
            include_comments=False,
            include_links=False,
            include_images=False,
            include_tables=False
        )
        
        if not extracted:
            logger.warning(f"Failed to extract content from {url}")
            return {
                'title': '',
                'content': '',
                'published_at': None,
                'source': extract_source_from_url(url),
                'success': False,
                'error': 'extraction_empty'
            }
        
        # Extract metadata
        metadata = trafilatura.extract_metadata(downloaded)
        
        # Get title
        title = metadata.title if metadata and metadata.title else ''
        
        # Get published date
        published_at = None
        if metadata and metadata.date:
            try:
                # Try to parse the date
                published_at = datetime.fromisoformat(metadata.date.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                try:
                    # Try alternative parsing (dateutil is optional)
                    try:
                        from dateutil import parser
                        published_at = parser.parse(metadata.date)
                    except ImportError:
                        # dateutil not available, skip date parsing
                        logger.debug("dateutil not available, skipping date parsing")
                except Exception:
                    logger.debug(f"Could not parse date: {metadata.date}")
        
        return {
            'title': title,
            'content': extracted,
            'published_at': published_at,
            'source': extract_source_from_url(url),
            'success': True,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return {
            'title': '',
            'content': '',
            'published_at': None,
            'source': extract_source_from_url(url),
            'success': False,
            'error': 'extraction_error'
        }


def extract_source_from_url(url: str) -> str:
    """Extract source name from URL.
    
    Args:
        url: Article URL
        
    Returns:
        Clean source name (e.g., "yahoo.com" from "https://finance.yahoo.com/...")
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.netloc or parsed.path
        
        # Remove www. prefix
        if hostname.startswith('www.'):
            hostname = hostname[4:]
        
        # Remove port if present
        if ':' in hostname:
            hostname = hostname.split(':')[0]
        
        return hostname
        
    except Exception as e:
        logger.warning(f"Error extracting source from URL {url}: {e}")
        return "unknown"


def validate_ticker_format(ticker: Optional[str], max_length: int = 20) -> bool:
    """Validate ticker symbol format.
    
    Args:
        ticker: Ticker symbol to validate
        max_length: Maximum allowed length (default 20, database limit)
        
    Returns:
        True if valid format, False otherwise
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    ticker = ticker.strip().upper()
    if not ticker:
        return False
    
    # Check length
    if len(ticker) > max_length:
        return False
    
    # Valid tickers: start with a letter; allow letters/digits/dot/dash afterwards
    # No spaces allowed
    pattern = r"^[A-Z][A-Z0-9\.-]*$"
    if not re.fullmatch(pattern, ticker):
        return False
    
    # Additional checks: reject if looks like a company name
    # - Contains multiple words (spaces would be caught by pattern, but check for common words)
    # - Too long (already checked)
    # - Contains common company name words
    company_name_indicators = ['LIMITED', 'INC', 'CORP', 'CORPORATION', 'LLC', 'LTD', 'HOLDINGS', 'GROUP', 'COMPANY']
    ticker_upper = ticker.upper()
    if any(indicator in ticker_upper for indicator in company_name_indicators):
        return False
    
    return True


def validate_ticker_in_content(ticker: Optional[str], content: str) -> bool:
    """Validate that ticker appears in article content.
    
    Args:
        ticker: Ticker symbol to validate
        content: Full article content to search
        
    Returns:
        True if ticker appears in content (case-insensitive), False otherwise
    """
    if not ticker or not content:
        return False
    
    # Case-insensitive search for ticker in content
    return ticker.upper() in content.upper()


def normalize_relationship(source: str, target: str, rel_type: str) -> Tuple[str, str, str]:
    """Normalize relationship direction using Option A (Industry Standard).
    
    Option A: Supplier → Buyer direction
    - SUPPLIER: [Supplier] -> SUPPLIER -> [Buyer] (e.g., TSM -> SUPPLIER -> AAPL)
    - CUSTOMER relationships are converted to SUPPLIER with supplier as source, buyer as target
    
    Args:
        source: Source ticker or company name
        target: Target ticker or company name
        rel_type: Relationship type (SUPPLIER, CUSTOMER, COMPETITOR, PARTNER, PARENT, SUBSIDIARY, LITIGATION)
        
    Returns:
        Tuple of (normalized_source, normalized_target, normalized_type)
        
    Examples:
        >>> normalize_relationship("TSM", "AAPL", "SUPPLIER")
        ("TSM", "AAPL", "SUPPLIER")
        >>> normalize_relationship("AAPL", "TSM", "CUSTOMER")
        ("TSM", "AAPL", "SUPPLIER")
        >>> normalize_relationship("AAPL", "MSFT", "COMPETITOR")
        ("AAPL", "MSFT", "COMPETITOR")
    """
    rel_type_upper = rel_type.upper().strip()
    source_upper = source.upper().strip()
    target_upper = target.upper().strip()
    
    # Handle CUSTOMER relationships: flip to SUPPLIER with supplier as source
    if rel_type_upper == "CUSTOMER":
        # "Apple is a customer of TSMC" → TSM -> SUPPLIER -> AAPL
        return (target_upper, source_upper, "SUPPLIER")
    
    # SUPPLIER relationships: already in correct direction (Supplier -> Buyer)
    # Other types (COMPETITOR, PARTNER, LITIGATION, PARENT, SUBSIDIARY): keep as-is
    return (source_upper, target_upper, rel_type_upper)
