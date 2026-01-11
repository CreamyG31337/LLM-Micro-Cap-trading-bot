from flask import Blueprint, render_template, request, g
import logging
from datetime import datetime, timedelta, date, timezone
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path to allow importing from root
# This ensures we can import modules like 'auth', 'supabase_client', etc.
sys.path.append(str(Path(__file__).parent.parent))

from auth import require_auth
from research_repository import ResearchRepository
from user_preferences import get_user_preference
from flask_auth_utils import get_user_email_flask
from flask_cache_utils import cache_resource, cache_data
# Note: get_navigation_context imported inside function to avoid circular import

logger = logging.getLogger('research')

research_bp = Blueprint('research', __name__)

# Log blueprint registration
logger.debug("[RESEARCH] Research blueprint loaded")

# Cached repository instance (resource caching)
@cache_resource
def get_research_repository():
    """Get research repository instance, cached for application lifetime"""
    return ResearchRepository()

# Cached helper functions for data fetching
@cache_data(ttl=300)
def get_cached_unique_tickers(repo: ResearchRepository):
    """Get unique tickers with caching (5min TTL)"""
    try:
        return repo.get_unique_tickers()
    except Exception as e:
        logger.error(f"Error fetching unique tickers: {e}", exc_info=True)
        return []

@cache_data(ttl=30)
def get_cached_articles(
    repo: ResearchRepository,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    article_type_filter: Optional[str],
    search_filter: Optional[str],
    ticker_filter: Optional[str],
    per_page: int,
    offset: int
):
    """Get articles with caching (30s TTL for fresher data during active use)"""
    try:
        tickers_filter = [ticker_filter] if ticker_filter else None
        
        if start_date and end_date:
            articles = repo.get_articles_by_date_range(
                start_date=start_date,
                end_date=end_date,
                article_type=article_type_filter,
                search_text=search_filter,
                tickers_filter=tickers_filter,
                limit=per_page,
                offset=offset
            )
        else:
            articles = repo.get_all_articles(
                article_type=article_type_filter,
                search_text=search_filter,
                tickers_filter=tickers_filter,
                limit=per_page,
                offset=offset
            )
        
        # Ensure articles is a list (not None)
        if articles is None:
            return []
        
        # Filter out any None articles and ensure valid structure
        articles = [a for a in articles if a is not None]
        
        # Ensure each article has tickers field
        for article in articles:
            if 'tickers' not in article or article['tickers'] is None:
                article['tickers'] = []
        
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        return []

@research_bp.route('/research')
@require_auth
def research_dashboard():
    """Research Repository Dashboard"""
    logger.debug("[RESEARCH] Route /v2/research accessed")
    try:
        # Get cached repository instance
        logger.debug("[RESEARCH] Getting ResearchRepository (cached)")
        repo = get_research_repository()
        logger.debug("[RESEARCH] ResearchRepository retrieved successfully")
        
        # Parse query parameters for filters
        # Date Range
        date_range_option = request.args.get('date_range', 'Last 30 days')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Calculate dates
        start_date = None
        end_date = None
        
        if date_range_option == "All time":
            start_date = None
            end_date = None
        elif date_range_option == "Custom" and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1)
            except ValueError:
                date_range_option = 'Last 30 days' # Fallback
                
        if not start_date and date_range_option != "All time":
            # Default or standard ranges
            days_map = {
                "Last 7 days": 7,
                "Last 30 days": 30,
                "Last 90 days": 90
            }
            days = days_map.get(date_range_option, 30)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
        # Other filters
        article_type = request.args.get('article_type', 'All')
        article_type_filter = None if article_type == 'All' else article_type
        
        ticker = request.args.get('ticker', 'All')
        ticker_filter = None if ticker == 'All' else ticker
        
        search_text = request.args.get('search', '').strip()
        search_filter = search_text if search_text else None
        
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        offset = (page - 1) * per_page
        
        # Owned tickers filter (simplified for V1: passing boolean if checked)
        only_owned = request.args.get('only_owned') == 'true'
        
        # Fetch tickers for dropdown (cached)
        unique_tickers = get_cached_unique_tickers(repo)
            
        # Fetch Articles (cached)
        articles = get_cached_articles(
            repo=repo,
            start_date=start_date,
            end_date=end_date,
            article_type_filter=article_type_filter,
            search_filter=search_filter,
            ticker_filter=ticker_filter,
            per_page=per_page,
            offset=offset
        )
        
        logger.info(f"Research dashboard: Fetched {len(articles)} valid articles")
            
        # Get common context
        from app import get_navigation_context  # Import here to avoid circular import
        user_email = get_user_email_flask()
        user_theme = get_user_preference('theme', default='system')
        nav_context = get_navigation_context(current_page='research')

        logger.debug(f"[RESEARCH] Rendering template with {len(articles)} articles, {len(unique_tickers)} tickers")
        
        return render_template(
            'research.html',
            articles=articles,
            unique_tickers=unique_tickers,
            filters={
                'date_range': date_range_option,
                'start_date': start_date_str,
                'end_date': end_date_str,
                'article_type': article_type,
                'ticker': ticker,
                'search': search_text,
                'only_owned': only_owned,
                'page': page
            },
            user_email=user_email,
            user_theme=user_theme,
            **nav_context
        )
        
    except Exception as e:
        logger.error(f"Error in research dashboard: {e}", exc_info=True)
        # Return error page with details
        from app import get_navigation_context  # Import here to avoid circular import
        user_email = get_user_email_flask()
        user_theme = get_user_preference('theme', default='system')
        nav_context = get_navigation_context(current_page='research')
        
        return render_template(
            'error.html' if Path('templates/error.html').exists() else 'base.html', 
            error_title="Research Repository Error",
            error_message=str(e),
            error_details="Please check the logs for more information.",
            user_email=user_email,
            user_theme=user_theme,
            **nav_context
        ), 500
