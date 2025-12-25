#!/usr/bin/env python3
"""
Search Utilities
================

Utility functions for formatting and processing SearXNG search results
for use in AI context and display.
"""

from typing import List, Dict, Any, Optional
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def format_search_results(search_data: Dict[str, Any], max_results: int = 10) -> str:
    """Format SearXNG search results for AI context.
    
    Args:
        search_data: Dictionary from SearXNG search response
        max_results: Maximum number of results to format
        
    Returns:
        Formatted string with search results
    """
    if 'error' in search_data:
        return f"Search error: {search_data['error']}"
    
    results = search_data.get('results', [])[:max_results]
    
    if not results:
        return "No search results found."
    
    formatted_parts = []
    formatted_parts.append(f"Web Search Results for: {search_data.get('query', 'Unknown query')}")
    formatted_parts.append(f"Total results: {search_data.get('number_of_results', len(results))}")
    formatted_parts.append("")
    
    for i, result in enumerate(results, 1):
        title = result.get('title', 'No title')
        url = result.get('url', '')
        content = result.get('content', '')
        engine = result.get('engine', '')
        
        formatted_parts.append(f"{i}. {title}")
        if url:
            formatted_parts.append(f"   URL: {url}")
        if engine:
            formatted_parts.append(f"   Source: {engine}")
        if content:
            # Truncate long content
            max_content_length = 300
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            formatted_parts.append(f"   Summary: {content}")
        formatted_parts.append("")
    
    # Add answers if available
    answers = search_data.get('answers', [])
    if answers:
        formatted_parts.append("Quick Answers:")
        for answer in answers[:3]:  # Limit to 3 answers
            formatted_parts.append(f"  - {answer}")
        formatted_parts.append("")
    
    return "\n".join(formatted_parts)


def search_portfolio_tickers(
    searxng_client,
    tickers: List[str],
    search_type: str = "news",
    time_range: Optional[str] = "day",
    max_results_per_ticker: int = 5,
    max_workers: int = 10
) -> Dict[str, Any]:
    """Search for news about specific portfolio tickers in parallel.
    
    Args:
        searxng_client: SearXNGClient instance
        tickers: List of ticker symbols to search for
        search_type: Type of search ('news' or 'web')
        time_range: Time range filter ('day', 'week', 'month', 'year')
        max_results_per_ticker: Maximum results per ticker
        max_workers: Maximum number of parallel search threads (default: 10)
        
    Returns:
        Dictionary mapping ticker to search results
    """
    if not searxng_client or not searxng_client.enabled:
        logger.warning("SearXNG client not available for ticker search")
        return {}
    
    ticker_results = {}
    
    def search_single_ticker(ticker: str) -> tuple[str, Dict[str, Any]]:
        """Helper function to search a single ticker."""
        try:
            # Build search query for ticker
            query = f"{ticker} stock news"
            
            if search_type == "news":
                search_data = searxng_client.search_news(
                    query=query,
                    time_range=time_range,
                    max_results=max_results_per_ticker
                )
            else:
                search_data = searxng_client.search_web(
                    query=query,
                    time_range=time_range,
                    max_results=max_results_per_ticker
                )
            
            logger.info(f"Search completed for {ticker}: {len(search_data.get('results', []))} results")
            return ticker, search_data
            
        except Exception as e:
            logger.error(f"Error searching for {ticker}: {e}")
            return ticker, {
                'results': [],
                'query': f"{ticker} stock news",
                'error': str(e)
            }
    
    # Execute searches in parallel using ThreadPoolExecutor
    logger.info(f"Starting parallel search for {len(tickers)} tickers with {max_workers} workers")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all ticker searches
        future_to_ticker = {executor.submit(search_single_ticker, ticker): ticker for ticker in tickers}
        
        # Collect results as they complete
        for future in as_completed(future_to_ticker):
            ticker, search_data = future.result()
            ticker_results[ticker] = search_data
    
    logger.info(f"Completed parallel search for {len(ticker_results)} tickers")
    return ticker_results


def search_market_news(
    searxng_client,
    query: str = "stock market news today",
    time_range: Optional[str] = "day",
    max_results: int = 10
) -> Dict[str, Any]:
    """Search for general market news.
    
    Args:
        searxng_client: SearXNGClient instance
        query: Search query string
        time_range: Time range filter
        max_results: Maximum number of results
        
    Returns:
        Dictionary containing market news search results
    """
    if not searxng_client or not searxng_client.enabled:
        logger.warning("SearXNG client not available for market news search")
        return {
            'results': [],
            'query': query,
            'error': 'SearXNG not available'
        }
    
    try:
        return searxng_client.search_news(
            query=query,
            time_range=time_range,
            max_results=max_results
        )
    except Exception as e:
        logger.error(f"Error searching for market news: {e}")
        return {
            'results': [],
            'query': query,
            'error': str(e)
        }


def build_search_query(user_query: str, tickers: Optional[List[str]] = None) -> str:
    """Construct optimized search query from user input.
    
    Args:
        user_query: User's natural language query
        tickers: Optional list of ticker symbols to include
        
    Returns:
        Optimized search query string
    """
    query = user_query.strip()
    
    # If tickers are provided, enhance the query
    if tickers:
        ticker_str = " ".join(tickers)
        # Add tickers to query if not already present
        if not any(ticker.lower() in query.lower() for ticker in tickers):
            query = f"{query} {ticker_str}"
    
    # Add stock/market context if not present
    market_keywords = ['stock', 'market', 'trading', 'earnings', 'news', 'financial']
    if not any(keyword in query.lower() for keyword in market_keywords):
        query = f"{query} stock market"
    
    return query


def format_ticker_news_results(ticker_results: Dict[str, Dict[str, Any]]) -> str:
    """Format ticker-specific news search results.
    
    Args:
        ticker_results: Dictionary mapping ticker to search results
        
    Returns:
        Formatted string with ticker news
    """
    if not ticker_results:
        return "No ticker news available."
    
    formatted_parts = []
    formatted_parts.append("Recent News by Ticker:")
    formatted_parts.append("")
    
    for ticker, search_data in ticker_results.items():
        if 'error' in search_data:
            formatted_parts.append(f"{ticker}: Search error - {search_data['error']}")
            continue
        
        results = search_data.get('results', [])
        if not results:
            formatted_parts.append(f"{ticker}: No recent news found")
            continue
        
        formatted_parts.append(f"{ticker}:")
        for i, result in enumerate(results[:3], 1):  # Limit to 3 results per ticker
            title = result.get('title', 'No title')
            url = result.get('url', '')
            content = result.get('content', '')
            
            formatted_parts.append(f"  {i}. {title}")
            if url:
                formatted_parts.append(f"     {url}")
            if content:
                max_length = 200
                if len(content) > max_length:
                    content = content[:max_length] + "..."
                formatted_parts.append(f"     {content}")
        formatted_parts.append("")
    
    return "\n".join(formatted_parts)

