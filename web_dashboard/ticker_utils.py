#!/usr/bin/env python3
"""
Ticker Utilities
================

Utility functions for fetching ticker information from all databases
and generating clickable links to ticker details pages.
"""

import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


def get_ticker_info(
    ticker: str,
    supabase_client=None,
    postgres_client=None
) -> Dict[str, Any]:
    """Get comprehensive ticker information from all databases.
    
    Aggregates ticker data from multiple sources (Supabase and Postgres) including
    basic security info, portfolio data, research articles, social sentiment,
    congress trades, and watchlist status.
    
    Args:
        ticker: Ticker symbol (e.g., "AAPL", "XMA.TO")
        supabase_client: Optional SupabaseClient instance for accessing securities,
            positions, trades, congress data, and watchlist
        postgres_client: Optional PostgresClient instance for accessing research
            articles and social sentiment metrics
        
    Returns:
        Dictionary with the following structure:
        {
            'ticker': str,  # Uppercase ticker symbol
            'found': bool,  # True if any data found for this ticker
            'basic_info': dict | None,  # From securities table
                {
                    'ticker': str,
                    'company_name': str,
                    'sector': str,
                    'industry': str,
                    'currency': str,  # 'USD', 'CAD', etc.
                    'exchange': str   # 'NASDAQ', 'NYSE', 'TSX', etc.
                }
            'portfolio_data': dict | None,
                {
                    'positions': list[dict],  # Latest 100 positions
                    'trades': list[dict],     # Latest 100 trades
                    'has_positions': bool,
                    'has_trades': bool
                }
            'research_articles': list[dict],  # Last 30 days, limit 50
                [
                    {
                        'id': int,
                        'title': str,
                        'url': str,
                        'summary': str,
                        'source': str,
                        'published_at': datetime,
                        'fetched_at': datetime,
                        'relevance_score': float,
                        'sentiment': str,  # 'positive', 'negative', 'neutral'
                        'sentiment_score': float,
                        'article_type': str
                    }
                ]
            'social_sentiment': dict | None,
                {
                    'latest_metrics': list[dict],  # Latest per platform
                    'alerts': list[dict]           # Extreme alerts (24h)
                }
            'congress_trades': list[dict],  # Last 30 days, limit 50
                [
                    {
                        'ticker': str,
                        'politician': str,
                        'chamber': str,  # 'House' or 'Senate'
                        'party': str,
                        'type': str,     # 'Purchase' or 'Sale'
                        'amount': str,
                        'transaction_date': date
                    }
                ]
            'watchlist_status': dict | None,
                {
                    'ticker': str,
                    'priority_tier': str,  # 'A', 'B', or 'C'
                    'source': str,
                    'is_active': bool
                }
        }
    
    Example:
        >>> from supabase_client import SupabaseClient
        >>> from postgres_client import PostgresClient
        >>> 
        >>> sb_client = SupabaseClient()
        >>> pg_client = PostgresClient()
        >>> 
        >>> # Get info for Apple
        >>> info = get_ticker_info("AAPL", sb_client, pg_client)
        >>> print(info['basic_info']['company_name'])
        'Apple Inc.'
        >>> print(f"Found {len(info['research_articles'])} articles")
        Found 15 articles
        >>> 
        >>> # Canadian ticker
        >>> info = get_ticker_info("XMA.TO", sb_client, pg_client)
        >>> print(info['basic_info']['exchange'])
        'TSX'
    
    Note:
        - Function makes 6 separate database queries (can be slow for large datasets)
        - Returns empty lists/None for missing data rather than raising exceptions
        - All timestamps should be timezone-aware (UTC)
        - Warnings logged for individual query failures (doesn't fail entire function)
    """
    ticker_upper = ticker.upper().strip()
    result = {
        'ticker': ticker_upper,
        'basic_info': None,
        'portfolio_data': None,
        'research_articles': [],
        'social_sentiment': None,
        'congress_trades': [],
        'watchlist_status': None,
        'found': False
    }
    
    # 1. Get basic info from securities table
    if supabase_client:
        try:
            sec_result = supabase_client.supabase.table("securities")\
                .select("*")\
                .eq("ticker", ticker_upper)\
                .execute()
            
            if sec_result.data and len(sec_result.data) > 0:
                result['basic_info'] = sec_result.data[0]
                result['found'] = True
        except Exception as e:
            logger.warning(f"Error fetching basic info for {ticker_upper}: {e}")
    
    # 2. Get portfolio data (positions and trades)
    if supabase_client:
        try:
            # Get current positions
            pos_result = supabase_client.supabase.table("portfolio_positions")\
                .select("*")\
                .eq("ticker", ticker_upper)\
                .order("date", desc=True)\
                .limit(100)\
                .execute()
            
            # Get trade history
            trade_result = supabase_client.supabase.table("trade_log")\
                .select("*")\
                .eq("ticker", ticker_upper)\
                .order("date", desc=True)\
                .limit(100)\
                .execute()
            
            if pos_result.data or trade_result.data:
                result['portfolio_data'] = {
                    'positions': pos_result.data if pos_result.data else [],
                    'trades': trade_result.data if trade_result.data else [],
                    'has_positions': len(pos_result.data) > 0 if pos_result.data else False,
                    'has_trades': len(trade_result.data) > 0 if trade_result.data else False
                }
                result['found'] = True
        except Exception as e:
            logger.warning(f"Error fetching portfolio data for {ticker_upper}: {e}")
    
    # 3. Get research articles (last 30 days)
    if postgres_client:
        try:
            thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
            query = """
                SELECT id, title, url, summary, source, published_at, fetched_at,
                       relevance_score, sentiment, sentiment_score, article_type
                FROM research_articles
                WHERE tickers @> ARRAY[%s]::text[]
                   OR ticker = %s
                AND fetched_at >= %s
                ORDER BY fetched_at DESC
                LIMIT 50
            """
            articles = postgres_client.execute_query(
                query, 
                (ticker_upper, ticker_upper, thirty_days_ago.isoformat())
            )
            
            if articles:
                result['research_articles'] = articles
                result['found'] = True
        except Exception as e:
            logger.warning(f"Error fetching research articles for {ticker_upper}: {e}")
    
    # 4. Get social sentiment (latest metrics)
    if postgres_client:
        try:
            query = """
                SELECT DISTINCT ON (platform)
                    ticker, platform, volume, sentiment_label, sentiment_score,
                    bull_bear_ratio, created_at
                FROM social_metrics
                WHERE ticker = %s
                ORDER BY platform, created_at DESC
                LIMIT 10
            """
            sentiment_data = postgres_client.execute_query(query, (ticker_upper,))
            
            # Get extreme alerts (last 24 hours)
            query_alerts = """
                SELECT ticker, platform, sentiment_label, sentiment_score, created_at
                FROM social_metrics
                WHERE ticker = %s
                  AND sentiment_label IN ('EUPHORIC', 'FEARFUL', 'BULLISH')
                  AND created_at > NOW() - INTERVAL '24 hours'
                ORDER BY created_at DESC
                LIMIT 10
            """
            alerts = postgres_client.execute_query(query_alerts, (ticker_upper,))
            
            if sentiment_data or alerts:
                result['social_sentiment'] = {
                    'latest_metrics': sentiment_data if sentiment_data else [],
                    'alerts': alerts if alerts else []
                }
                result['found'] = True
        except Exception as e:
            logger.warning(f"Error fetching social sentiment for {ticker_upper}: {e}")
    
    # 5. Get congress trades (last 30 days)
    if supabase_client:
        try:
            thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).date()
            congress_result = supabase_client.supabase.table("congress_trades_enriched")\
                .select("*")\
                .eq("ticker", ticker_upper)\
                .gte("transaction_date", thirty_days_ago.isoformat())\
                .order("transaction_date", desc=True)\
                .limit(50)\
                .execute()
            
            if congress_result.data:
                result['congress_trades'] = congress_result.data
                result['found'] = True
        except Exception as e:
            logger.warning(f"Error fetching congress trades for {ticker_upper}: {e}")
    
    # 6. Get watchlist status
    if supabase_client:
        try:
            watchlist_result = supabase_client.supabase.table("watched_tickers")\
                .select("*")\
                .eq("ticker", ticker_upper)\
                .execute()
            
            if watchlist_result.data and len(watchlist_result.data) > 0:
                result['watchlist_status'] = watchlist_result.data[0]
                result['found'] = True
        except Exception as e:
            logger.warning(f"Error fetching watchlist status for {ticker_upper}: {e}")
    
    return result


def get_ticker_external_links(ticker: str, exchange: Optional[str] = None) -> Dict[str, str]:
    """Generate external links to financial websites for a ticker.
    
    Creates links to major financial data sources including Yahoo Finance,
    TradingView, Finviz, Seeking Alpha, MarketWatch, StockTwits, Reddit, and
    Google Finance. Handles both US and Canadian tickers appropriately.
    
    Args:
        ticker: Ticker symbol (e.g., "AAPL", "XMA.TO", "SHOP.V")
        exchange: Optional exchange code for more specific routing.
            Supported: 'NASDAQ', 'NYSE', 'TSX', 'TSXV', 'AMEX'
        
    Returns:
        Dictionary mapping site names to full URLs:
        {
            'Yahoo Finance': str,
            'TradingView': str,
            'Finviz': str,
            'Seeking Alpha': str,
            'MarketWatch': str,
            'StockTwits': str,
            'Reddit (WSB)': str,
            'Google Finance': str
        }
    
    Example:
        >>> links = get_ticker_external_links("AAPL", "NASDAQ")
        >>> print(links['Yahoo Finance'])
        'https://finance.yahoo.com/quote/AAPL'
        >>> print(links['TradingView'])
        'https://www.tradingview.com/symbols/NASDAQ-AAPL/'
        >>> 
        >>> # Canadian ticker
        >>> links = get_ticker_external_links("XMA.TO", "TSX")
        >>> print(links['TradingView'])
        'https://www.tradingview.com/symbols/TSX-XMA/'
    
    Note:
        - Canadian ticker suffixes (.TO, .V) are automatically detected
        - Base ticker extracted for sites that don't support suffixes
        - All URLs are properly formatted and URL-safe
    """
    ticker_upper = ticker.upper().strip()
    
    # Handle Canadian tickers
    base_ticker = ticker_upper
    is_canadian = False
    if '.TO' in ticker_upper:
        base_ticker = ticker_upper.replace('.TO', '')
        is_canadian = True
        exchange = exchange or 'TSX'
    elif '.V' in ticker_upper:
        base_ticker = ticker_upper.replace('.V', '')
        is_canadian = True
        exchange = exchange or 'TSXV'
    
    links = {}
    
    # Yahoo Finance
    links['Yahoo Finance'] = f"https://finance.yahoo.com/quote/{ticker_upper}"
    
    # TradingView
    if exchange:
        # Try to map exchange to TradingView format
        exchange_map = {
            'NASDAQ': 'NASDAQ',
            'NYSE': 'NYSE',
            'TSX': 'TSX',
            'TSXV': 'TSXV',
            'AMEX': 'AMEX'
        }
        tv_exchange = exchange_map.get(exchange, exchange)
        links['TradingView'] = f"https://www.tradingview.com/symbols/{tv_exchange}-{base_ticker}/"
    else:
        links['TradingView'] = f"https://www.tradingview.com/symbols/{base_ticker}/"
    
    # Finviz
    links['Finviz'] = f"https://finviz.com/quote.ashx?t={base_ticker}"
    
    # Seeking Alpha
    links['Seeking Alpha'] = f"https://seekingalpha.com/symbol/{base_ticker}"
    
    # MarketWatch
    links['MarketWatch'] = f"https://www.marketwatch.com/investing/stock/{base_ticker}"
    
    # StockTwits
    links['StockTwits'] = f"https://stocktwits.com/symbol/{base_ticker}"
    
    # Reddit (wallstreetbets search)
    links['Reddit (WSB)'] = f"https://www.reddit.com/r/wallstreetbets/search/?q={base_ticker}&restrict_sr=1"
    
    # Google Finance
    links['Google Finance'] = f"https://www.google.com/finance/quote/{ticker_upper}"
    
    return links


def render_ticker_link(
    ticker: str,
    display_text: Optional[str] = None,
    use_page_link: bool = True
) -> str:
    """Generate a clickable ticker link for Streamlit markdown rendering.
    
    Creates markdown-formatted links that navigate to the ticker details page.
    Note: Only works in markdown contexts (st.markdown, st.write with markdown),
    NOT in st.dataframe() or AgGrid.
    
    Args:
        ticker: Ticker symbol (e.g., "AAPL", "TSLA")
        display_text: Optional text to display for the link.
            If None, displays the ticker symbol itself.
        use_page_link: If True, uses Streamlit's page navigation format.
            If False, uses query parameter format (legacy).
        
    Returns:
        Markdown link string in format: "[display](url)"
    
    Example:
        >>> link = render_ticker_link("AAPL")
        >>> print(link)
        '[AAPL](ticker_details?ticker=AAPL)'
        >>> 
        >>> # Custom display text
        >>> link = render_ticker_link("AAPL", "Apple Inc.")
        >>> print(link)
        '[Apple Inc.](ticker_details?ticker=AAPL)'
        >>> 
        >>> # Use in Streamlit markdown
        >>> import streamlit as st
        >>> st.markdown(f"View details for {render_ticker_link('AAPL')}")
    
    Warning:
        This does NOT work in st.dataframe() or AgGrid - the markdown
        will display as plain text. For tables, consider:
        - st.data_editor() with LinkColumn (Streamlit 1.29+)
        - Separate "View Details" button column
        - Custom HTML table with unsafe_allow_html=True
    """
    ticker_upper = ticker.upper().strip()
    display = display_text if display_text else ticker_upper
    
    if use_page_link:
        # Use Streamlit page_link format
        # Format: ticker_details?ticker=AAPL
        return f"[{display}](ticker_details?ticker={ticker_upper})"
    else:
        # Fallback to query parameter format
        return f"[{display}](?ticker={ticker_upper})"


def make_tickers_clickable(text: str) -> str:
    """Find ticker patterns in text and convert them to clickable links.
    
    Args:
        text: Text that may contain ticker symbols
        
    Returns:
        Text with tickers converted to markdown links
    """
    # Pattern for ticker symbols (1-5 uppercase letters, optionally with .TO, .V, etc.)
    ticker_pattern = r'\b([A-Z]{1,5}(?:\.(?:TO|V|CN|NE|TSX))?)\b'
    
    # False positives to exclude (common words, technical terms, financial/business acronyms)
    false_positives = {
        # Common words
        'I', 'A', 'AN', 'THE', 'IS', 'IT', 'TO', 'BE', 'OR', 'OF', 'IN',
        'ON', 'AT', 'BY', 'FOR', 'AS', 'WE', 'HE', 'MY', 'ME', 'US', 'SO',
        'DO', 'GO', 'NO', 'UP', 'IF', 'AM', 'PM', 'OK', 'TV', 'PC',
        # Technical terms
        'AI', 'API', 'URL', 'HTTP', 'HTTPS', 'PDF', 'CSV', 'JSON', 'XML', 'HTML',
        'SQL', 'REST', 'SOAP', 'SSH', 'FTP', 'VPN', 'DNS', 'IP',
        # Financial/Business acronyms
        'SEC', 'ETF', 'IPO', 'CEO', 'CFO', 'CTO', 'COO', 'CMO', 'CIO',
        'PE', 'PS', 'EPS', 'ROI', 'ROE', 'ROA', 'EBIT', 'FCF',
        'LLC', 'INC', 'LTD', 'CORP', 'PLC', 'GAAP', 'FDA', 'FTC',
        'IR', 'PR', 'HR', 'IT', 'RD', 'QA', 'VC', 'MA', 'USD', 'CAD',
        'YOY', 'MOM', 'QOQ', 'YTD', 'MTD', 'EOD', 'AUM', 'NAV'
    }
    
    def replace_ticker(match):
        ticker = match.group(1)
        base_ticker = ticker.split('.')[0]
        
        # Skip false positives
        if base_ticker in false_positives:
            return ticker
        
        # Convert to link
        return render_ticker_link(ticker, ticker, use_page_link=True)
    
    # Replace all ticker patterns
    result = re.sub(ticker_pattern, replace_ticker, text)
    
    return result

