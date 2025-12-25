#!/usr/bin/env python3
"""
Research Utilities
==================

Helper functions for extracting and processing research articles.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

try:
    import trafilatura
except ImportError:
    trafilatura = None
    logging.warning("trafilatura not installed - article extraction will fail")

logger = logging.getLogger(__name__)


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
    """
    if not trafilatura:
        logger.error("trafilatura not installed - cannot extract article content")
        return {
            'title': '',
            'content': '',
            'published_at': None,
            'source': extract_source_from_url(url)
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
                'source': extract_source_from_url(url)
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
                'source': extract_source_from_url(url)
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
            'source': extract_source_from_url(url)
        }
        
    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        return {
            'title': '',
            'content': '',
            'published_at': None,
            'source': extract_source_from_url(url)
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

