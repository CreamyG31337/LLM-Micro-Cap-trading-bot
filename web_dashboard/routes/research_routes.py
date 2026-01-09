from flask import Blueprint, render_template, request, g
import logging
from datetime import datetime, timedelta, date, timezone
import sys
from pathlib import Path

# Add parent directory to path to allow importing from root
# This ensures we can import modules like 'auth', 'supabase_client', etc.
sys.path.append(str(Path(__file__).parent.parent))

from auth import require_auth
from research_repository import ResearchRepository
from user_preferences import get_user_preference
from flask_auth_utils import get_user_email_flask
from app import get_navigation_context

logger = logging.getLogger(__name__)

research_bp = Blueprint('research', __name__)

@research_bp.route('/research')
@require_auth
def research_dashboard():
    """Research Repository Dashboard"""
    try:
        # Initialize repository
        repo = ResearchRepository()
        
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
        
        # Fetch tickers for dropdown
        try:
            unique_tickers = repo.get_unique_tickers()
        except:
            unique_tickers = []
            
        # Fetch Articles
        # Note: ResearchRepository.get_articles_by_date_range handles date filtering
        # get_all_articles handles no date filtering
        
        if start_date:
            articles = repo.get_articles_by_date_range(
                start_date=start_date,
                end_date=end_date,
                article_type=article_type_filter,
                search_text=search_filter,
                tickers_filter=[ticker_filter] if ticker_filter else None,
                limit=per_page,
                offset=offset
            )
        else:
            articles = repo.get_all_articles(
                article_type=article_type_filter,
                search_text=search_filter,
                tickers_filter=[ticker_filter] if ticker_filter else None,
                limit=per_page,
                offset=offset
            )
        
        # Ensure articles is a list (not None)
        if articles is None:
            logger.warning("ResearchRepository returned None for articles")
            articles = []
        
        logger.info(f"Research dashboard: Fetched {len(articles)} articles")
            
        # Get common context
        user_email = get_user_email_flask()
        user_theme = get_user_preference('theme', default='system')
        nav_context = get_navigation_context(current_page='research')

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
