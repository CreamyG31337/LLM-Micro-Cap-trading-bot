#!/usr/bin/env python3
"""
Paywall Detection System
========================

Centralized paywall detection using regex patterns for known financial news sites.
Supports extensible pattern matching for paywall detection.

Documentation:
- Each site's paywall patterns are documented with examples
- Patterns are regex-based for flexibility
- Sites may have multiple patterns (different paywall messages)
- Some sites have metered paywalls (limited free articles) vs hard paywalls (all articles)
"""

import re
import logging
from typing import Optional, Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Load obfuscated domain names
def _load_obfuscated_domains() -> Dict[str, str]:
    """Load obfuscated domain names from keys file."""
    try:
        # Try importing from web_dashboard package
        try:
            from web_dashboard.test_url_loader import get_domain
        except ImportError:
            # Fallback for direct script execution
            from test_url_loader import get_domain
        
        return {
            'site_a': get_domain('DOMAIN_SITE_A'),
            'site_b': get_domain('DOMAIN_SITE_B'),
        }
    except (ImportError, FileNotFoundError, KeyError) as e:
        # Fallback if keys file not available - use placeholder that won't match
        logger.warning(f"Could not load obfuscated domains from keys file: {e}")
        logger.warning("Paywall detection for obfuscated sites will not work without keys file")
        # Use placeholder domains that won't match real URLs
        return {
            'site_a': 'placeholder-site-a.invalid',
            'site_b': 'placeholder-site-b.invalid',
        }

_OBFUSCATED_DOMAINS = _load_obfuscated_domains()

# Paywall patterns organized by domain
# Format: domain (lowercase) -> list of regex patterns
# Patterns should match paywall messages in article content
PAYWALL_PATTERNS: Dict[str, List[str]] = {
    # Site A - Hard paywall (obfuscated domain name)
    # Example: "The article requires paid subscription."
    _OBFUSCATED_DOMAINS['site_a']: [
        r'The article requires paid subscription\.',
    ],
    
    # Financial Times (FT.com) - Metered/Hard paywall
    # Example: "Subscribe to unlock this article", "Try unlimited access"
    'ft.com': [
        r'Subscribe to unlock this article',
        r'Subscribe to read',
        r'Subscribe to continue reading',
        r'Try unlimited access',
        r'Only.*for.*weeks',
        r'Complete digital access to quality FT journalism',
    ],
    
    # Wall Street Journal (WSJ) - Hard paywall
    # One of the strictest paywalls; most articles require subscription
    # Patterns TBD - need to research actual paywall messages
    'wsj.com': [
        r'Subscribe to continue reading',
        r'Already a subscriber\?',
        r'Sign in to continue reading',
    ],
    
    # Bloomberg - Paywall for premium content (~$35/month)
    # Core wire service news is often free, but deeper analysis is gated
    # Patterns TBD - need to research actual paywall messages
    'bloomberg.com': [
        r'Subscribe to read',
        r'Subscribe to continue',
        r'Already a subscriber\?',
    ],
    
    # Barron's - Investment-focused (owned by WSJ parent)
    # Paywall for stock picks, market commentary, and analysis
    # Patterns TBD - need to research actual paywall messages
    'barrons.com': [
        r'Subscribe to continue reading',
        r'Already a subscriber\?',
        r'Sign in to continue',
    ],
    
    # MarketWatch - Metered paywall (Dow Jones-owned)
    # Popular for stock quotes, news, and personal finance
    # Articles often limited after a few views
    # Patterns TBD - need to research actual paywall messages
    'marketwatch.com': [
        r'Subscribe to continue reading',
        r'Already a subscriber\?',
        r'You\'ve reached your article limit',
    ],
    
    # Reuters - Paywall for premium content (~$35/month)
    # Core wire service news is often free, but deeper business/stock reports are gated
    # Patterns TBD - need to research actual paywall messages
    'reuters.com': [
        r'Subscribe to read',
        r'Subscribe to continue',
        r'Already a subscriber\?',
    ],
    
    # CNBC - Partial paywall for in-depth reports and premium features
    # Basic news is free, but advanced stock tools/analysis require subscription
    # Patterns TBD - need to research actual paywall messages
    'cnbc.com': [
        r'Subscribe to Pro',
        r'Already a Pro subscriber\?',
        r'Upgrade to Pro',
    ],
    
    # The Economist - Metered/Hard paywall
    # Weekly global business and finance insights
    # Patterns TBD - need to research actual paywall messages
    'economist.com': [
        r'Subscribe to continue reading',
        r'Already a subscriber\?',
        r'Sign in to continue',
    ],
    
    # Site B - Metered/Hard paywall (obfuscated domain name)
    # Major US newspaper with subscription model
    _OBFUSCATED_DOMAINS['site_b']: [
        r'Subscribe for full access',
        r'Log in',
        r'Create an account',
        r'Subscribe to The Times',
    ],
}

# Generic paywall patterns that might appear on any site
GENERIC_PATTERNS = [
    r'subscribe to (read|continue|unlock)',
    r'paid subscription',
    r'premium content',
    r'requires subscription',
    r'sign in to continue',
    r'log in to continue',
]


def extract_domain(url: str) -> str:
    """Extract domain from URL for pattern matching.
    
    Args:
        url: Article URL
        
    Returns:
        Domain name (lowercase, without www)
    """
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
        
        return domain
    except Exception as e:
        logger.warning(f"Error extracting domain from URL {url}: {e}")
        return ""


def detect_paywall(content: str, source: str) -> Optional[str]:
    """Detect if content contains a paywall message.
    
    Args:
        content: Article content to check
        source: Source domain or URL
        
    Returns:
        Paywall type/domain if detected, None otherwise
    """
    if not content or not source:
        return None
    
    # Extract domain if source is a URL
    domain = extract_domain(source) if '://' in source else source.lower()
    
    # Check domain-specific patterns first
    for pattern_domain, patterns in PAYWALL_PATTERNS.items():
        if pattern_domain in domain:
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    logger.debug(f"Paywall detected: {pattern_domain} (pattern: {pattern})")
                    return pattern_domain
    
    # Check generic patterns as fallback
    for pattern in GENERIC_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            logger.debug(f"Generic paywall pattern detected: {pattern}")
            return "generic"
    
    return None


def is_paywalled_article(content: str, url: str) -> bool:
    """Main detection function - check if article is paywalled.
    
    Args:
        content: Article content to check
        url: Article URL (for domain extraction)
        
    Returns:
        True if paywall detected, False otherwise
    """
    if not content or not url:
        return False
    
    paywall_type = detect_paywall(content, url)
    return paywall_type is not None


def get_paywall_patterns() -> Dict[str, List[str]]:
    """Get all documented paywall patterns.
    
    Returns:
        Dictionary mapping domains to their paywall patterns
    """
    return PAYWALL_PATTERNS.copy()


def add_paywall_pattern(domain: str, pattern: str) -> None:
    """Add a new paywall pattern for a domain.
    
    Useful for extending the detection system as new patterns are discovered.
    
    Args:
        domain: Domain name (e.g., 'example.com')
        pattern: Regex pattern to match paywall message
    """
    domain = domain.lower()
    if domain not in PAYWALL_PATTERNS:
        PAYWALL_PATTERNS[domain] = []
    
    if pattern not in PAYWALL_PATTERNS[domain]:
        PAYWALL_PATTERNS[domain].append(pattern)
        logger.info(f"Added new paywall pattern for {domain}: {pattern}")

