"""
Shared Utilities for Scheduled Jobs
====================================

Common functions and utilities used across multiple job modules.
"""

from typing import List, Optional


def calculate_relevance_score(
    tickers: List[str], 
    sector: Optional[str],
    owned_tickers: Optional[List[str]] = None
) -> float:
    """Calculate relevance score based on tickers and ownership.
    
    Args:
        tickers: List of ticker symbols extracted from article
        sector: Sector name if available
        owned_tickers: Optional list of tickers we own (for performance)
        
    Returns:
        Relevance score: 0.8 (owned tickers), 0.7 (opportunities), 0.5 (general)
    """
    if not tickers:
        return 0.5  # General market news
    
    # Check if any tickers are owned
    if owned_tickers:
        has_owned = any(ticker in owned_tickers for ticker in tickers)
        if has_owned:
            return 0.8  # Ticker-specific, owned
    
    # Has tickers but none owned = opportunity discovery
    return 0.7

