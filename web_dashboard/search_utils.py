#!/usr/bin/env python3
"""
Search Utilities
================

Utility functions for formatting and processing SearXNG search results
for use in AI context and display.
"""

from typing import List, Dict, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
def get_company_name_from_db(ticker: str) -> Optional[str]:
    """Get company name from database for a ticker symbol.
    
    Args:
        ticker: Ticker symbol (e.g., "XMA.TO", "AAPL")
        
    Returns:
        Company name if found in database, None otherwise
    """
    try:
        # Import here to avoid circular dependency
        from streamlit_utils import get_supabase_client
        
        client = get_supabase_client()
        if not client:
            logger.debug(f"Supabase client not available for company name lookup: {ticker}")
            return None
        
        # Query securities table for company name
        result = client.supabase.table("securities").select("company_name").eq("ticker", ticker.upper().strip()).execute()
        
        if result.data and len(result.data) > 0:
            company_name = result.data[0].get('company_name')
            if company_name and company_name.strip() and company_name != 'Unknown':
                logger.debug(f"Found company name for {ticker}: {company_name}")
                return company_name.strip()
        
        logger.debug(f"Company name not found in database for {ticker}")
        return None
        
    except Exception as e:
        logger.warning(f"Error fetching company name from database for {ticker}: {e}")
        return None


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
    max_results_per_ticker: int = 5
) -> Dict[str, Any]:
    """Search for news about specific portfolio tickers.
    
    Args:
        searxng_client: SearXNGClient instance
        tickers: List of ticker symbols to search for
        search_type: Type of search ('news' or 'web')
        time_range: Time range filter ('day', 'week', 'month', 'year')
        max_results_per_ticker: Maximum results per ticker
        
    Returns:
        Dictionary mapping ticker to search results
    """
    if not searxng_client or not searxng_client.enabled:
        logger.warning("SearXNG client not available for ticker search")
        return {}
    
    ticker_results = {}
    
    for ticker in tickers:
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
            
            ticker_results[ticker] = search_data
            logger.info(f"Search completed for {ticker}: {len(search_data.get('results', []))} results")
            
        except Exception as e:
            logger.error(f"Error searching for {ticker}: {e}")
            ticker_results[ticker] = {
                'results': [],
                'query': f"{ticker} stock news",
                'error': str(e)
            }
    
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


def build_search_query(
    user_query: str, 
    tickers: Optional[List[str]] = None,
    company_name: Optional[str] = None,
    preserve_keywords: bool = True
) -> str:
    """Construct optimized search query from user input.
    
    Args:
        user_query: User's natural language query
        tickers: Optional list of ticker symbols to include
        company_name: Optional company name to include in search
        preserve_keywords: Whether to preserve important keywords from query
        
    Returns:
        Optimized search query string
    """
    query = user_query.strip()
    query_lower = query.lower()
    
    # Extract and preserve important financial keywords
    important_keywords = []
    if preserve_keywords:
        financial_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'dividend', 'ipo',
            'merger', 'acquisition', 'financial', 'report', 'quarterly',
            'annual', 'guidance', 'forecast', 'analyst', 'rating', 'upgrade',
            'downgrade', 'price target', 'valuation', 'results', 'announcement'
        ]
        
        for keyword in financial_keywords:
            if keyword in query_lower:
                important_keywords.append(keyword)
    
    # Build query components
    query_parts = []
    
    # Add tickers first if provided
    if tickers:
        ticker_str = " ".join(tickers)
        query_parts.append(ticker_str)
    
    # Add company name if provided
    if company_name and company_name.strip():
        query_parts.append(company_name.strip())
    
    # Add preserved important keywords
    if important_keywords:
        query_parts.extend(important_keywords)
    
    # If we have tickers/company name and keywords, build focused query
    if query_parts:
        # Check if original query already contains these elements
        query_contains_tickers = tickers and any(ticker.lower() in query_lower for ticker in tickers)
        query_contains_company = company_name and company_name.lower() in query_lower
        
        # If original query doesn't have tickers/company, use our built query
        if not query_contains_tickers or (company_name and not query_contains_company):
            built_query = " ".join(query_parts)
            # Add "news" if not already present
            if 'news' not in built_query.lower() and 'news' not in query_lower:
                built_query += " news"
            return built_query
    
    # Fallback: enhance original query
    query = user_query.strip()
    
    # If tickers are provided, enhance the query
    if tickers:
        ticker_str = " ".join(tickers)
        # Add tickers to query if not already present
        if not any(ticker.lower() in query.lower() for ticker in tickers):
            query = f"{query} {ticker_str}"
    
    # Add company name if provided and not already in query
    if company_name and company_name.strip():
        if company_name.lower() not in query.lower():
            query = f"{query} {company_name.strip()}"
    
    # Add stock/market context if not present
    market_keywords = ['stock', 'market', 'trading', 'earnings', 'news', 'financial']
    if not any(keyword in query.lower() for keyword in market_keywords):
        query = f"{query} stock"
    
    return query


def filter_relevant_results(
    results: List[Dict[str, Any]], 
    ticker: str,
    company_name: Optional[str] = None,
    min_relevance_score: float = 0.3
) -> List[Dict[str, Any]]:
    """Filter search results to only include those relevant to the ticker.
    
    Args:
        results: List of search result dictionaries
        ticker: Ticker symbol to match against (e.g., "XMA.TO" or "AAPL")
        company_name: Optional company name to check for
        min_relevance_score: Minimum relevance score (0-1) to include result
        
    Returns:
        Filtered list of relevant results, sorted by relevance score
    """
    if not results:
        return []
    
    base_ticker = ticker.split('.')[0].upper()
    ticker_upper = ticker.upper()
    
    # Prepare company name for matching
    company_keywords = []
    if company_name:
        company_name_upper = company_name.upper()
        # Use full company name
        company_keywords.append(company_name_upper)
        # Also split into significant words if it's long
        words = [w for w in company_name_upper.split() if len(w) > 3 and w not in ['CORP', 'CORPORATION', 'INC', 'LTD', 'LIMITED', 'GROUP', 'HOLDINGS']]
        if words:
            company_keywords.extend(words)
            
    relevant_results = []
    
    for result in results:
        title = result.get('title', '').upper()
        content = result.get('content', '').upper()
        url = result.get('url', '').upper()
        
        # Combine all text to check
        text_to_check = f"{title} {content} {url}"
        
        relevance_score = 0.0
        
        # Exact ticker match (with or without suffix) - highest priority
        if ticker_upper in text_to_check:
            relevance_score = 1.0
        # Base ticker match in title (high weight)
        elif base_ticker in title:
            relevance_score = 0.8
        # Company name match in title (high weight)
        elif company_name and any(kw in title for kw in company_keywords):
            relevance_score = 0.8
        # Base ticker match in content (medium weight)
        elif base_ticker in content:
            relevance_score = 0.6
        # Company name match in content (medium weight)
        elif company_name and any(kw in content for kw in company_keywords):
            relevance_score = 0.6
        # Base ticker match in URL (lower weight)
        elif base_ticker in url:
            relevance_score = 0.4
        
        # Only include if meets minimum relevance threshold
        if relevance_score >= min_relevance_score:
            result['relevance_score'] = relevance_score
            relevant_results.append(result)
    
    # Sort by relevance score descending
    relevant_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    return relevant_results


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


def extract_tickers_from_query(query: str) -> List[str]:
    """Extract ticker symbols from a query string, including exchange suffixes.
    
    Looks for ticker symbols with patterns like:
    - XMA.TO, AAPL, TSLA (with or without exchange suffixes)
    - $XMA.TO, $AAPL (with $ prefix)
    - XMA.TO stock, AAPL earnings (in context)
    
    Args:
        query: User query string
        
    Returns:
        List of potential ticker symbols found (with suffixes preserved)
    """
    # Pattern for ticker symbols with optional exchange suffixes
    # Matches: 1-5 uppercase letters, optionally followed by .TO, .V, .CN, .NE, .TSX
    # Also handles $ prefix
    ticker_pattern = r'\$?([A-Z]{1,5}(?:\.(?:TO|V|CN|NE|TSX))?)\b'
    
    # Find all potential matches
    matches = re.findall(ticker_pattern, query)
    
    # Filter out common false positives (common words that look like tickers)
    false_positives = {
        'I', 'A', 'AN', 'THE', 'IS', 'IT', 'TO', 'BE', 'OR', 'OF', 'IN',
        'ON', 'AT', 'BY', 'FOR', 'AS', 'WE', 'HE', 'MY', 'ME', 'US', 'SO',
        'DO', 'GO', 'NO', 'UP', 'IF', 'AM', 'PM', 'OK', 'TV', 'PC', 'AI',
        'API', 'URL', 'HTTP', 'HTTPS', 'PDF', 'CSV', 'JSON', 'XML', 'HTML'
    }
    
    # Extract unique tickers, filtering false positives
    tickers = []
    for match in matches:
        # Extract base ticker (before .) for false positive check
        base_ticker = match.split('.')[0]
        if base_ticker not in false_positives and match not in tickers:
            tickers.append(match)
    
    return tickers


def detect_research_intent(query: str) -> Dict[str, Any]:
    """Detect research intent and classify the type of research needed.
    
    Args:
        query: User query string
        
    Returns:
        Dictionary with:
        - 'needs_search': bool - Whether search should be triggered
        - 'research_type': str - Type of research ('ticker', 'market', 'general', 'none')
        - 'tickers': List[str] - Extracted ticker symbols
        - 'keywords': List[str] - Relevant keywords found
    """
    query_lower = query.lower()
    
    # Extract tickers
    tickers = extract_tickers_from_query(query)
    
    # Research keywords that indicate need for web search
    research_keywords = [
        'research', 'news', 'latest', 'recent', 'today', 'analysis',
        'analyze', 'information', 'find', 'search', 'what', 'how',
        'why', 'when', 'where', 'update', 'current', 'happening'
    ]
    
    # Market-related keywords
    market_keywords = [
        'market', 'stocks', 'trading', 'earnings', 'ipo', 'dividend',
        'sector', 'industry', 'company', 'corporation', 'financial',
        'investor', 'investment', 'portfolio', 'equity', 'shares'
    ]
    
    # Time-sensitive keywords
    time_keywords = [
        'today', 'this week', 'this month', 'recent', 'latest',
        'current', 'now', 'yesterday', 'last week', 'last month'
    ]
    
    # Find matching keywords
    found_research_keywords = [kw for kw in research_keywords if kw in query_lower]
    found_market_keywords = [kw for kw in market_keywords if kw in query_lower]
    found_time_keywords = [kw for kw in time_keywords if kw in query_lower]
    
    # Determine if search is needed
    needs_search = False
    research_type = 'none'
    
    # Always search if explicit research keywords
    if found_research_keywords:
        needs_search = True
        if tickers:
            research_type = 'ticker'
        elif found_market_keywords:
            research_type = 'market'
        else:
            research_type = 'general'
    
    # Search if tickers mentioned (likely asking about specific stocks)
    elif tickers:
        needs_search = True
        research_type = 'ticker'
    
    # Search for market/time-sensitive queries
    elif found_market_keywords and found_time_keywords:
        needs_search = True
        research_type = 'market'
    
    # Search for general market queries
    elif found_market_keywords:
        needs_search = True
        research_type = 'market'
    
    return {
        'needs_search': needs_search,
        'research_type': research_type,
        'tickers': tickers,
        'keywords': {
            'research': found_research_keywords,
            'market': found_market_keywords,
            'time': found_time_keywords
        }
    }


def should_trigger_search(query: str, portfolio_tickers: Optional[List[str]] = None) -> bool:
    """Determine if a search should be triggered automatically based on query content.
    
    Args:
        query: User query string
        portfolio_tickers: Optional list of tickers in user's portfolio
        
    Returns:
        True if search should be triggered, False otherwise
    """
    intent = detect_research_intent(query)
    
    if not intent['needs_search']:
        return False
    
    # If tickers are mentioned, check if they're in portfolio
    if intent['tickers'] and portfolio_tickers:
        # If all mentioned tickers are in portfolio, might not need external search
        # But still search if research keywords are present
        all_in_portfolio = all(ticker in portfolio_tickers for ticker in intent['tickers'])
        if all_in_portfolio and not intent['keywords']['research']:
            # Only skip if no research keywords and all tickers in portfolio
            return False
    
    return True

