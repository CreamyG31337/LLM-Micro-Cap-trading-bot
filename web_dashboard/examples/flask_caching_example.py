"""
Example: Adding Flask Caching to Research Routes
================================================

This example shows how to migrate cached functions from Streamlit to Flask
using the flask_cache_utils module.
"""

from flask_cache_utils import cache_data, cache_resource
from research_repository import ResearchRepository
from cache_version import get_cache_version
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Cache Repository Instance (Resource)
# ============================================================================

@cache_resource
def get_research_repository():
    """
    Cache the repository instance (like @st.cache_resource).
    This ensures we only create one instance per application lifetime.
    """
    return ResearchRepository()


# ============================================================================
# Example 2: Cache Statistics (Data with TTL)
# ============================================================================

@cache_data(ttl=60)  # Cache for 60 seconds (matches Streamlit)
def get_cached_statistics(repo: ResearchRepository, refresh_key: int):
    """
    Get article statistics with caching.
    
    Args:
        repo: ResearchRepository instance
        refresh_key: Integer that changes when user clicks refresh (for cache invalidation)
    
    Returns:
        Dictionary with statistics
    """
    return repo.get_article_statistics(days=90)


# ============================================================================
# Example 3: Cache Articles List (Data with TTL)
# ============================================================================

@cache_data(ttl=30)  # Cache for 30 seconds (matches Streamlit)
def get_cached_articles(
    repo: ResearchRepository,
    refresh_key: int,
    use_date_filter: bool,
    start_datetime_str: str,
    end_datetime_str: str,
    article_type_filter: str,
    source_filter: str,
    search_filter: str,
    embedding_filter: bool,
    tickers_filter_json: str,
    results_per_page: int,
    offset: int
):
    """
    Get articles with caching (30s TTL for fresher data during active use).
    
    Args:
        tickers_filter_json: JSON-encoded list of tickers to filter by, or empty string for no filter
    """
    # Parse tickers filter from JSON
    tickers_filter = None
    if tickers_filter_json:
        try:
            tickers_filter = json.loads(tickers_filter_json)
        except (json.JSONDecodeError, TypeError):
            tickers_filter = None
    
    try:
        if use_date_filter and start_datetime_str and end_datetime_str:
            start_dt = datetime.fromisoformat(start_datetime_str)
            end_dt = datetime.fromisoformat(end_datetime_str)
            articles = repo.get_articles_by_date_range(
                start_date=start_dt,
                end_date=end_dt,
                article_type=article_type_filter if article_type_filter else None,
                source=source_filter if source_filter else None,
                search_text=search_filter if search_filter else None,
                embedding_filter=embedding_filter,
                tickers_filter=tickers_filter,
                limit=results_per_page,
                offset=offset
            )
        else:
            articles = repo.get_all_articles(
                article_type=article_type_filter if article_type_filter else None,
                source=source_filter if source_filter else None,
                search_text=search_filter if search_filter else None,
                embedding_filter=embedding_filter,
                tickers_filter=tickers_filter,
                limit=results_per_page,
                offset=offset
            )
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        return []


# ============================================================================
# Example 4: Cache with Version Support (for automatic invalidation)
# ============================================================================

@cache_data(ttl=300)  # Cache for 5 minutes
def get_cached_owned_tickers(refresh_key: int, _cache_version: Optional[str] = None):
    """
    Get owned tickers from all production funds with caching.
    Includes cache_version for automatic invalidation when portfolio updates.
    
    Returns normalized tickers (uppercase, trimmed) for consistent comparison.
    """
    if _cache_version is None:
        _cache_version = get_cache_version()
    
    try:
        from supabase_client import SupabaseClient
        from research_utils import normalize_ticker
        
        # Use role-based access for security
        from flask_auth_utils import is_admin_flask, get_user_token_flask
        
        if is_admin_flask():
            client = SupabaseClient(use_service_role=True)
        else:
            user_token = get_user_token_flask()
            if user_token:
                client = SupabaseClient(user_token=user_token)
            else:
                logger.warning("No user token available, cannot fetch owned tickers")
                return set()
        
        if not client:
            return set()
        
        # Get production funds
        funds_result = client.supabase.table("funds")\
            .select("name")\
            .eq("is_production", True)\
            .execute()
        
        if not funds_result.data:
            return set()
        
        prod_funds = [f['name'] for f in funds_result.data]
        
        positions_result = client.supabase.table("latest_positions")\
            .select("ticker, fund")\
            .in_("fund", prod_funds)\
            .execute()
        
        if positions_result.data:
            owned_tickers = set()
            for pos in positions_result.data:
                ticker = pos.get('ticker')
                if ticker:
                    normalized = normalize_ticker(ticker)
                    if normalized:
                        owned_tickers.add(normalized)
            
            return owned_tickers
        
        return set()
    except Exception as e:
        logger.warning(f"Could not fetch owned tickers: {e}")
        return set()


# ============================================================================
# Example 5: Using Cached Functions in Flask Routes
# ============================================================================

def example_research_route():
    """
    Example Flask route showing how to use cached functions.
    This would be in routes/research_routes.py
    """
    from flask import request
    
    # Get cached repository (resource)
    repo = get_research_repository()
    
    # Get refresh key from query params (for manual cache invalidation)
    refresh_key = int(request.args.get('refresh_key', 0))
    
    # Get cached statistics
    stats = get_cached_statistics(repo, refresh_key)
    
    # Get cached articles with filters
    page = int(request.args.get('page', 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    start_dt_str = request.args.get('start_date', '')
    end_dt_str = request.args.get('end_date', '')
    
    articles = get_cached_articles(
        repo=repo,
        refresh_key=refresh_key,
        use_date_filter=bool(start_dt_str and end_dt_str),
        start_datetime_str=start_dt_str,
        end_datetime_str=end_dt_str,
        article_type_filter=request.args.get('article_type', ''),
        source_filter=request.args.get('source', ''),
        search_filter=request.args.get('search', ''),
        embedding_filter=request.args.get('embedding_only') == 'true',
        tickers_filter_json=request.args.get('tickers_json', ''),
        results_per_page=per_page,
        offset=offset
    )
    
    return {
        'stats': stats,
        'articles': articles,
        'page': page
    }


# ============================================================================
# Example 6: Manual Cache Invalidation
# ============================================================================

def clear_research_cache():
    """Clear all research-related caches manually."""
    # Clear specific function cache
    get_cached_statistics.clear_all_cache()
    get_cached_articles.clear_all_cache()
    
    # Or clear everything
    from flask_cache_utils import clear_all_caches
    clear_all_caches()


# ============================================================================
# Example 7: Cache Statistics
# ============================================================================

def get_cache_info():
    """Get information about current cache state."""
    from flask_cache_utils import get_cache_stats
    
    stats = get_cache_stats()
    return {
        'total_keys': stats['total_keys'],
        'backend': stats['backend'],
        'sample_keys': stats['keys'][:5]  # First 5 keys
    }
