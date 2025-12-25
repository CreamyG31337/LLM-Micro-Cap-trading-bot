"""
Scheduled Jobs Definitions
==========================

Define all background jobs here. Each job should:
1. Be a function that takes no arguments
2. Handle its own error logging
3. Call log_job_execution() to record results
"""

import logging
import time
from datetime import datetime, timezone, timedelta, date, time as dt_time
from typing import Dict, Any, Optional
from decimal import Decimal
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from scheduler.scheduler_core import log_job_execution

logger = logging.getLogger(__name__)


# Job definitions with metadata
AVAILABLE_JOBS: Dict[str, Dict[str, Any]] = {
    'exchange_rates': {
        'name': 'Refresh Exchange Rates',
        'description': 'Fetch latest USD/CAD exchange rate and store in database',
        'default_interval_minutes': 120,  # Every 2 hours
        'enabled_by_default': True
    },
    'performance_metrics': {
        'name': 'Populate Performance Metrics',
        'description': 'Aggregate daily portfolio performance into metrics table',
        'default_interval_minutes': 1440,  # Once per day
        'enabled_by_default': True
    },
    'update_portfolio_prices': {
        'name': 'Update Portfolio Prices',
        'description': 'Fetch current stock prices and update portfolio positions for today',
        'default_interval_minutes': 15,  # Every 15 minutes during market hours
        'enabled_by_default': True
    },
    'market_research': {
        'name': 'Market Research Collection',
        'description': 'Scrape and store general market news articles',
        'default_interval_minutes': 360,  # Every 6 hours (but uses cron triggers instead)
        'enabled_by_default': True
    },
    'ticker_research': {
        'name': 'Ticker Research Collection',
        'description': 'Fetch news for specific companies in the portfolio',
        'default_interval_minutes': 360,  # Every 6 hours
        'enabled_by_default': True
    }
}


def market_research_job() -> None:
    """Fetch and store general market news articles.
    
    This job:
    1. Fetches general market news using SearXNG
    2. Extracts article content using trafilatura
    3. Generates AI summaries using Ollama
    4. Saves articles to the database
    """
    job_id = 'market_research'
    start_time = time.time()
    
    try:
        logger.info("Starting market research job...")
        
        # Import dependencies (lazy imports to avoid circular dependencies)
        try:
            from searxng_client import get_searxng_client, check_searxng_health
            from research_utils import extract_article_content
            from ollama_client import get_ollama_client
            from research_repository import ResearchRepository
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Check if SearXNG is available
        if not check_searxng_health():
            duration_ms = int((time.time() - start_time) * 1000)
            message = "SearXNG is not available - skipping research job"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Get clients
        searxng_client = get_searxng_client()
        ollama_client = get_ollama_client()
        
        if not searxng_client:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "SearXNG client not initialized"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Initialize research repository
        research_repo = ResearchRepository()
        
        # Load domain blacklist
        from settings import get_research_domain_blacklist
        blacklist = get_research_domain_blacklist()
        if blacklist:
            logger.info(f"Loaded domain blacklist: {blacklist}")
        else:
            logger.info("No domains blacklisted")
        
        # Fetch general market news
        logger.info("Fetching general market news...")
        search_results = searxng_client.search_news(
            query="stock market news",
            max_results=10
        )
        
        if not search_results or not search_results.get('results'):
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No search results found"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        articles_processed = 0
        articles_saved = 0
        articles_skipped = 0
        articles_blacklisted = 0
        
        for result in search_results['results']:
            try:
                url = result.get('url', '')
                title = result.get('title', '')
                
                if not url or not title:
                    logger.debug("Skipping result with missing URL or title")
                    continue
                
                # Check if domain is blacklisted
                from research_utils import is_domain_blacklisted
                is_blocked, domain = is_domain_blacklisted(url, blacklist)
                if is_blocked:
                    logger.info(f"ℹ️ Skipping blacklisted domain: {domain}")
                    articles_blacklisted += 1
                    continue
                
                
                # Check if article already exists
                if research_repo.article_exists(url):
                    logger.debug(f"Article already exists: {title[:50]}...")
                    articles_skipped += 1
                    continue
                
                # Extract article content
                logger.info(f"Extracting content: {title[:50]}...")
                extracted = extract_article_content(url)
                
                # Initialize health tracker (lazy import to avoid circular deps)
                from research_domain_health import DomainHealthTracker, normalize_domain
                tracker = DomainHealthTracker()
                
                # Get auto-blacklist threshold
                from settings import get_system_setting
                threshold = get_system_setting("auto_blacklist_threshold", default=4)
                
                # Check if extraction succeeded
                content = extracted.get('content', '')
                if not content or not extracted.get('success'):
                    # Record failure with reason
                    error_reason = extracted.get('error', 'unknown')
                    failure_count = tracker.record_failure(url, error_reason)
                    
                    domain = normalize_domain(url)
                    logger.warning(f"⚠️ Domain extraction failed: {domain} (failure {failure_count}/{threshold}) - Reason: {error_reason}")
                    
                    # Check if we should auto-blacklist
                    if tracker.should_auto_blacklist(url):
                        if tracker.auto_blacklist_domain(url):
                            logger.warning(f"🚫 AUTO-BLACKLISTED: {domain} ({failure_count} consecutive failures of type: {error_reason})")
                            articles_blacklisted += 1
                        else:
                            logger.warning(f"Failed to auto-blacklist {domain}")
                    
                    continue
                
                # Record success
                tracker.record_success(url)
                
                # Generate summary and embedding using Ollama (if available)
                summary = None
                embedding = None
                if ollama_client:
                    logger.info(f"Generating summary for: {title[:50]}...")
                    summary = ollama_client.generate_summary(content)
                    if not summary:
                        logger.warning(f"Failed to generate summary for {title[:50]}...")
                    
                    # Generate embedding for semantic search
                    logger.debug(f"Generating embedding for: {title[:50]}...")
                    embedding = ollama_client.generate_embedding(content[:6000])  # Truncate to avoid token limits
                    if not embedding:
                        logger.warning(f"Failed to generate embedding for {title[:50]}...")
                else:
                    logger.debug("Ollama not available - skipping summary and embedding generation")
                
                # Save article to database
                article_id = research_repo.save_article(
                    ticker=None,  # General market news, not ticker-specific
                    sector=None,
                    article_type="market_news",
                    title=extracted.get('title') or title,
                    url=url,
                    summary=summary,
                    content=content,
                    source=extracted.get('source'),
                    published_at=extracted.get('published_at'),
                    relevance_score=0.5,  # Default relevance for general market news
                    embedding=embedding
                )
                
                if article_id:
                    articles_saved += 1
                    logger.info(f"✅ Saved article: {title[:50]}...")
                else:
                    logger.warning(f"Failed to save article: {title[:50]}...")
                
                articles_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing article '{title[:50]}...': {e}")
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Processed {articles_processed} articles: {articles_saved} saved, {articles_skipped} skipped, {articles_blacklisted} blacklisted"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Market research job failed: {e}", exc_info=True)


def ticker_research_job() -> None:
    """Fetch news for companies held in the portfolio.
    
    This job:
    1. Identifies all tickers held in production funds
    2. Searches for news specific to each ticker + company name
    3. Saves relevant articles to the database
    """
    job_id = 'ticker_research'
    start_time = time.time()
    
    try:
        logger.info("Starting ticker research job...")
        
        # Import dependencies (lazy imports)
        try:
            from searxng_client import get_searxng_client, check_searxng_health
            from research_utils import extract_article_content
            from ollama_client import get_ollama_client
            from research_repository import ResearchRepository
            from supabase_client import SupabaseClient
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Check SearXNG health
        if not check_searxng_health():
            duration_ms = int((time.time() - start_time) * 1000)
            message = "SearXNG is not available - skipping ticker research"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
            
        searxng_client = get_searxng_client()
        ollama_client = get_ollama_client()
        research_repo = ResearchRepository()
        
        if not searxng_client:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "SearXNG client not initialized"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return

        # Load domain blacklist
        from settings import get_research_domain_blacklist
        blacklist = get_research_domain_blacklist()

        # Connect to Supabase
        client = SupabaseClient(use_service_role=True)
        
        # 1. Get production funds
        funds_result = client.supabase.table("funds")\
            .select("name")\
            .eq("is_production", True)\
            .execute()
            
        if not funds_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No production funds found"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
            
        prod_funds = [f['name'] for f in funds_result.data]
        logger.info(f"Scanning holdings for funds: {prod_funds}")
        
        # 2. Get distinct tickers and company names from portfolio_positions for these funds
        # We look at the most recent snapshot for each fund
        
        # Efficient query to get distinct ticker/company pairs from current positions
        # Using the current_positions view is easiest as it aggregates valid positions
        positions_result = client.supabase.table("current_positions")\
            .select("ticker, company, fund")\
            .in_("fund", prod_funds)\
            .execute()
            
        if not positions_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No active positions found in production funds"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Deduplicate tickers (same ticker might be in multiple funds)
        # Store as dict: ticker -> company_name
        targets = {}
        for pos in positions_result.data:
            ticker = pos['ticker']
            company = pos.get('company')
            
            # Prefer longer company name if multiple exist (more descriptive)
            if ticker not in targets:
                targets[ticker] = company
            elif company and (not targets[ticker] or len(company) > len(targets[ticker])):
                targets[ticker] = company
                
        logger.info(f"Found {len(targets)} unique tickers to research: {list(targets.keys())}")
        
        articles_saved = 0
        articles_failed = 0
        tickers_processed = 0
        
        # 3. Iterate and search for each ticker
        for ticker, company in targets.items():
            try:
                # Construct search query
                # Use company name if available for better results, otherwise just ticker + "stock"
                if company and company.lower() != 'none':
                    query = f"{ticker} {company} stock news"
                else:
                    query = f"{ticker} stock news"
                
                logger.info(f"🔎 Searching for: '{query}'")
                
                # Fetch search results
                # Limit to 5 per ticker to avoid overwhelming the system/logs
                search_results = searxng_client.search_news(query=query, max_results=5)
                
                if not search_results or not search_results.get('results'):
                    logger.debug(f"No results for {ticker}")
                    continue
                
                # Process results
                for result in search_results['results']:
                    try:
                        url = result.get('url', '')
                        title = result.get('title', '')
                        
                        if not url or not title:
                            continue
                        
                        # Check blacklist
                        from research_utils import is_domain_blacklisted
                        is_blocked, domain = is_domain_blacklisted(url, blacklist)
                        if is_blocked:
                            logger.debug(f"Skipping blacklisted: {domain}")
                            continue

                         # Deduplicate
                        if research_repo.article_exists(url):
                            continue
                        
                        # Extract content
                        logger.info(f"  Extracting: {title[:40]}...")
                        extracted = extract_article_content(url)
                        
                        content = extracted.get('content', '')
                        if not content:
                            continue
                        
                        # Summarize and generate embedding
                        summary = None
                        embedding = None
                        if ollama_client:
                            summary = ollama_client.generate_summary(content)
                            
                            # Generate embedding for semantic search
                            embedding = ollama_client.generate_embedding(content[:6000])  # Truncate to avoid token limits
                            if not embedding:
                                logger.warning(f"Failed to generate embedding for {ticker}")
                        
                        # Save
                        article_id = research_repo.save_article(
                            ticker=ticker,
                            sector=None,  # Could fetch sector if available in metadata
                            article_type="ticker_news",
                            title=extracted.get('title') or title,
                            url=url,
                            summary=summary,
                            content=content,
                            source=extracted.get('source'),
                            published_at=extracted.get('published_at'),
                            relevance_score=0.8,  # Higher relevance for targeted ticker news
                            embedding=embedding
                        )
                        
                        if article_id:
                            articles_saved += 1
                            logger.info(f"  ✅ Saved: {title[:30]}")
                        
                        # Small delay between articles to be nice
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing article for {ticker}: {e}")
                        articles_failed += 1
                
                tickers_processed += 1
                
                # Delay between tickers to avoid rate limiting SearXNG
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error searching for {ticker}: {e}")
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Processed {tickers_processed} tickers. Saved {articles_saved} new articles."
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Ticker research job failed: {e}", exc_info=True)



def refresh_exchange_rates_job() -> None:
    """Fetch and store the latest exchange rate.
    
    This ensures the dashboard always has up-to-date rates for currency conversion.
    """
    job_id = 'exchange_rates'
    start_time = time.time()
    
    try:
        logger.info("Starting exchange rates refresh job...")
        
        # Import here to avoid circular imports
        from exchange_rates_utils import reload_exchange_rate_for_date
        
        # Fetch today's rate
        today = datetime.now(timezone.utc)
        rate = reload_exchange_rate_for_date(today, 'USD', 'CAD')
        
        if rate is not None:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Updated USD/CAD rate: {rate}"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"✅ {message}")
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "Failed to fetch exchange rate from API"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.warning(f"⚠️ {message}")
            
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Exchange rates job failed: {e}")


def populate_performance_metrics_job() -> None:
    """Aggregate daily portfolio performance into performance_metrics table.
    
    This pre-calculates daily metrics to speed up chart queries (90 rows vs 1338 rows).
    Runs yesterday's data to ensure market close prices are final.
    """
    job_id = 'performance_metrics'
    start_time = time.time()
    
    try:
        logger.info("Starting performance metrics population job...")
        
        # Import here to avoid circular imports
        from supabase_client import SupabaseClient
        from datetime import date
        from decimal import Decimal
        
        # Use service role key to bypass RLS (background job needs full access)
        client = SupabaseClient(use_service_role=True)
        
        # Process yesterday's data (today's data may still be updating)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        
        # Get all funds that have data for yesterday
        positions_result = client.supabase.table("portfolio_positions")\
            .select("fund, total_value, cost_basis, pnl, currency, date")\
            .gte("date", f"{yesterday}T00:00:00")\
            .lt("date", f"{yesterday}T23:59:59.999999")\
            .execute()
        
        if not positions_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"No position data found for {yesterday}"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Group by fund and aggregate
        from collections import defaultdict
        fund_totals = defaultdict(lambda: {
            'total_value': Decimal('0'),
            'cost_basis': Decimal('0'),
            'unrealized_pnl': Decimal('0'),
            'total_trades': 0
        })
        
        # Load exchange rates if needed for USD conversion
        from exchange_rates_utils import get_exchange_rate_for_date_from_db
        
        for pos in positions_result.data:
            fund = pos['fund']
            original_currency = pos.get('currency', 'CAD')
            currency = original_currency
            # Validate currency: treat 'nan', None, or empty strings as 'CAD'
            if not currency or not isinstance(currency, str):
                currency = 'CAD'
                logger.warning(f"⚠️ Position in fund '{fund}' has invalid currency (None/non-string). Defaulting to CAD.")
            else:
                currency = currency.strip().upper()
                if currency in ('NAN', 'NONE', 'NULL', ''):
                    logger.warning(f"⚠️ Position in fund '{fund}' ticker '{pos.get('ticker', 'unknown')}' has invalid currency '{original_currency}'. Defaulting to CAD.")
                    currency = 'CAD'
            
            # Convert to Decimal for precision
            total_value = Decimal(str(pos.get('total_value', 0) or 0))
            cost_basis = Decimal(str(pos.get('cost_basis', 0) or 0))
            pnl = Decimal(str(pos.get('pnl', 0) or 0))
            
            # Convert USD to CAD if needed
            if currency == 'USD':
                rate = get_exchange_rate_for_date_from_db(
                    datetime.combine(yesterday, datetime.min.time()),
                    'USD',
                    'CAD'
                )
                if rate:
                    rate_decimal = Decimal(str(rate))
                    total_value *= rate_decimal
                    cost_basis *= rate_decimal
                    pnl *= rate_decimal
            
            fund_totals[fund]['total_value'] += total_value
            fund_totals[fund]['cost_basis'] += cost_basis
            fund_totals[fund]['unrealized_pnl'] += pnl
            fund_totals[fund]['total_trades'] += 1
        
        # Insert/update performance_metrics for each fund
        rows_inserted = 0
        for fund, totals in fund_totals.items():
            performance_pct = (
                (float(totals['unrealized_pnl']) / float(totals['cost_basis']) * 100)
                if totals['cost_basis'] > 0 else 0.0
            )
            
            # Upsert into performance_metrics
            client.supabase.table("performance_metrics").upsert({
                'fund': fund,
                'date': str(yesterday),
                'total_value': float(totals['total_value']),
                'cost_basis': float(totals['cost_basis']),
                'unrealized_pnl': float(totals['unrealized_pnl']),
                'performance_pct': round(performance_pct, 2),
                'total_trades': totals['total_trades'],
                'winning_trades': 0,  # Not calculated in this version
                'losing_trades': 0     # Not calculated in this version
            }, on_conflict='fund,date').execute()
            
            rows_inserted += 1
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Populated {rows_inserted} fund(s) for {yesterday}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Performance metrics job failed: {e}")


# Thread-safe lock to prevent concurrent execution
# A simple boolean was causing race conditions when backfill and scheduled jobs ran simultaneously
import threading
_update_prices_lock = threading.Lock()

def update_portfolio_prices_job(target_date: Optional[date] = None) -> None:
    """Update portfolio positions with current market prices for a specific date.
    
    Args:
        target_date: Date to update. If None, auto-determines (today or last trading day).
    
    This job:
    1. Gets current positions from the latest snapshot (or rebuilds from trade log)
    2. Fetches current market prices for all positions
    3. Updates only the target date's snapshot
    4. Does NOT delete any historical data
    
    Based on logic from debug/rebuild_portfolio_complete.py but modified to:
    - Only update current/last day (or specified date)
    - Not wipe historical data
    - Work with Supabase directly
    
    Safety Features:
    - Prevents concurrent execution (thread-safe lock + APScheduler max_instances=1)
    - Atomic delete+insert per fund (all or nothing)
    - Skips failed tickers but continues with successful ones
    - Handles partial failures gracefully
    """
    # Acquire lock with non-blocking check - if another thread is already running, skip
    acquired = _update_prices_lock.acquire(blocking=False)
    if not acquired:
        logger.warning("Portfolio price update job already running - skipping (lock not acquired)")
        return
    
    job_id = 'update_portfolio_prices'
    start_time = time.time()
    
    try:
        
        # CRITICAL: Add project root to path FIRST, before any imports
        import sys
        import os
        from pathlib import Path
        
        # Get absolute path to project root
        # __file__ is scheduler/jobs.py
        # parent is scheduler/, parent.parent is web_dashboard/, parent.parent.parent is project root
        project_root = Path(__file__).resolve().parent.parent.parent
        project_root_str = str(project_root)
        
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
            logger.debug(f"Added project root to sys.path: {project_root_str}")
        
        # Also ensure web_dashboard is in path for supabase_client imports
        web_dashboard_path = str(Path(__file__).resolve().parent.parent)
        if web_dashboard_path not in sys.path:
            sys.path.insert(0, web_dashboard_path)
            logger.debug(f"Added web_dashboard to sys.path: {web_dashboard_path}")
        
        logger.info("Starting portfolio price update job...")
        
        # Import here to avoid circular imports
        from market_data.data_fetcher import MarketDataFetcher
        from market_data.price_cache import PriceCache
        from market_data.market_hours import MarketHours
        from utils.market_holidays import MarketHolidays
        from supabase_client import SupabaseClient
        from data.repositories.repository_factory import RepositoryFactory
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        # Initialize components
        market_fetcher = MarketDataFetcher()
        price_cache = PriceCache()
        market_hours = MarketHours()
        market_holidays = MarketHolidays()
        # Use service role key to bypass RLS (background job needs full access)
        client = SupabaseClient(use_service_role=True)
        
        # Determine target date if not specified
        if target_date is None:
            # Auto-detect based on time of day and market hours
            # This matches the logic in utils/portfolio_update_logic.py from console app
            # Key principle: 
            # - Before 9:30 AM ET: Use yesterday (market hasn't opened yet)
            # - After 4:00 PM ET: Use today (market has closed)
            # - Between 9:30 AM - 4:00 PM: Use today if trading day (for live prices)
            
            # CRITICAL: Get current time in ET FIRST, then derive 'today' from ET time
            # Using server time (UTC) for 'today' causes wrong date selection
            from datetime import datetime as dt
            import pytz
            
            et = pytz.timezone('America/New_York')
            now_et = dt.now(et)
            today = now_et.date()  # Use ET date, not server/UTC date
            
            # Market hours: 9:30 AM - 4:00 PM ET
            market_open_hour = 9
            market_open_minute = 30
            market_close_hour = 16
            
            # Determine time of day status
            current_time = now_et.time()
            is_before_open = current_time < time(market_open_hour, market_open_minute)
            is_after_close = current_time >= time(market_close_hour, 0)
            
            use_today = False
            if market_holidays.is_trading_day(today, market="any"):
                if is_before_open:
                    # Before 9:30 AM - market hasn't opened yet, use yesterday
                    logger.info(f"Current time is {now_et.strftime('%I:%M %p ET')} - before market open (9:30 AM ET) - will use last trading day")
                elif is_after_close:
                    # After 4:00 PM - market has closed, use today
                    use_today = True
                else:
                    # During market hours (9:30 AM - 4:00 PM) - use today for live prices
                    use_today = True
            
            if use_today:
                target_date = today
            else:
                # Use last trading day
                target_date = None
                for i in range(1, 8):
                    check_date = today - timedelta(days=i)
                    if market_holidays.is_trading_day(check_date, market="any"):
                        target_date = check_date
                        break
                
                if target_date is None:
                    duration_ms = int((time.time() - start_time) * 1000)
                    message = f"No trading day found in last 7 days - skipping update"
                    log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
                    logger.info(f"ℹ️ {message}")
                    return
        
        # Log the target date with timezone info for debugging
        from datetime import datetime as dt
        import pytz
        et_tz = pytz.timezone('America/New_York')
        now_et = dt.now(et_tz)
        logger.info(f"Target date for price update: {target_date}")
        logger.info(f"Current time: {now_et.strftime('%Y-%m-%d %I:%M %p %Z')} (ET)")
        logger.info(f"Server time: {datetime.now()} (local)")
        
        # CRITICAL: Double-check that target_date is actually a trading day
        # This prevents the job from running on holidays/weekends even if cron triggers it
        if not market_holidays.is_trading_day(target_date, market="any"):
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Target date {target_date} is not a trading day - skipping update"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Get all production funds from database (skip test/dev funds)
        funds_result = client.supabase.table("funds")\
            .select("name, base_currency")\
            .eq("is_production", True)\
            .execute()
            
        if not funds_result.data:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No production funds found in database"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # Build list of production funds with their base currency settings
        funds = [(f['name'], f.get('base_currency', 'CAD')) for f in funds_result.data]
        logger.info(f"Processing {len(funds)} production funds")
        
        # Mark job as started (for completion tracking)
        mark_job_started('update_portfolio_prices', target_date)
        
        total_positions_updated = 0
        total_funds_processed = 0
        funds_completed = []  # Track which funds completed successfully
        
        for fund_name, base_currency in funds:
            try:
                logger.info(f"Processing fund: {fund_name} (base_currency: {base_currency})")
                
                # Rebuild current positions from trade log (source of truth)
                # This ensures we have accurate positions even if database is stale
                from data.repositories.repository_factory import RepositoryFactory
                
                # Get data directory for this fund (try to find it)
                # For now, we'll use Supabase repository directly
                try:
                    repository = RepositoryFactory.create_repository(
                        repository_type='supabase',
                        fund_name=fund_name
                    )
                except Exception as e:
                    logger.warning(f"  Could not create repository for {fund_name}: {e}")
                    continue
                
                # Get all trades for this fund
                trades_result = client.supabase.table("trade_log")\
                    .select("*")\
                    .eq("fund", fund_name)\
                    .order("date")\
                    .execute()
                
                if not trades_result.data:
                    logger.info(f"  No trades found for {fund_name}")
                    continue
                
                # Build running positions from trade log (same logic as rebuild script)
                running_positions = defaultdict(lambda: {
                    'shares': Decimal('0'),
                    'cost': Decimal('0'),
                    'currency': 'USD'
                })
                
                for trade in trades_result.data:
                    ticker = trade['ticker']
                    shares = Decimal(str(trade.get('shares', 0) or 0))
                    price = Decimal(str(trade.get('price', 0) or 0))
                    cost = shares * price
                    reason = str(trade.get('reason', '')).upper()
                    
                    if 'SELL' in reason:
                        # Simple FIFO: reduce shares and cost proportionally
                        if running_positions[ticker]['shares'] > 0:
                            cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                            running_positions[ticker]['shares'] -= shares
                            running_positions[ticker]['cost'] -= shares * cost_per_share
                            # Ensure we don't go negative
                            if running_positions[ticker]['shares'] < 0:
                                running_positions[ticker]['shares'] = Decimal('0')
                            if running_positions[ticker]['cost'] < 0:
                                running_positions[ticker]['cost'] = Decimal('0')
                    else:
                        # Default to BUY
                        running_positions[ticker]['shares'] += shares
                        running_positions[ticker]['cost'] += cost
                        currency = trade.get('currency', 'USD')
                        # Validate currency: must be a non-empty string and not 'nan'
                        if currency and isinstance(currency, str):
                            currency_upper = currency.strip().upper()
                            if currency_upper and currency_upper not in ('NAN', 'NONE', 'NULL', ''):
                                running_positions[ticker]['currency'] = currency_upper
                            else:
                                # Invalid currency string - keep default 'USD'
                                logger.warning(f"⚠️ Trade for '{ticker}' in fund '{fund_name}' has invalid currency '{currency}'. Defaulting to USD.")
                        else:
                            # If currency is None or not a string, keep default 'USD'
                            logger.warning(f"⚠️ Trade for '{ticker}' in fund '{fund_name}' has missing currency. Defaulting to USD.")
                
                # Filter to only positions with shares > 0
                current_holdings = {
                    ticker: pos for ticker, pos in running_positions.items()
                    if pos['shares'] > 0
                }
                
                if not current_holdings:
                    logger.info(f"  No active positions for {fund_name}")
                    continue
                
                logger.info(f"  Found {len(current_holdings)} active positions")
                
                # Get exchange rate for target date (for USD→base_currency conversion)
                from exchange_rates_utils import get_exchange_rate_for_date_from_db
                
                exchange_rate = Decimal('1.0')  # Default for same currency or no conversion needed
                if base_currency != 'USD':  # Only fetch rate if converting TO non-USD currency
                    rate = get_exchange_rate_for_date_from_db(
                        datetime.combine(target_date, datetime.min.time()),
                        'USD',
                        base_currency
                    )
                    if rate is not None:
                        exchange_rate = Decimal(str(rate))
                        logger.info(f"  Using exchange rate USD→{base_currency}: {exchange_rate}")
                    else:
                        # Fallback rate if no data available
                        exchange_rate = Decimal('1.35')
                        logger.warning(f"  Missing exchange rate for {target_date}, using fallback {exchange_rate}")
                
                # OPTIMIZATION: Fetch current prices for all tickers in parallel
                current_prices = {}
                failed_tickers = []
                rate_limit_errors = 0
                
                # Helper function to fetch price for a single ticker
                def fetch_ticker_price(ticker: str) -> tuple[str, Optional[Decimal], Optional[str]]:
                    """Fetch price for a single ticker. Returns (ticker, price, error_type)."""
                    try:
                        # Fetch price data for target date
                        start_dt = datetime.combine(target_date, datetime.min.time())
                        end_dt = datetime.combine(target_date, datetime.max.time())
                        result = market_fetcher.fetch_price_data(ticker, start=start_dt, end=end_dt)
                        
                        if result and result.df is not None and not result.df.empty:
                            # Get the most recent close price
                            latest_price = Decimal(str(result.df['Close'].iloc[-1]))
                            return (ticker, latest_price, None)
                        else:
                            # Try to get from cache or previous day
                            cached_data = price_cache.get_cached_price(ticker)
                            if cached_data is not None and not cached_data.empty:
                                latest_price = Decimal(str(cached_data['Close'].iloc[-1]))
                                return (ticker, latest_price, 'cached')
                            else:
                                return (ticker, None, 'no_data')
                    except Exception as e:
                        error_str = str(e).lower()
                        # Check for rate limiting errors (429, too many requests, etc.)
                        if '429' in error_str or 'rate limit' in error_str or 'too many requests' in error_str:
                            return (ticker, None, 'rate_limit')
                        else:
                            return (ticker, None, 'error')
                
                # Fetch prices in parallel using ThreadPoolExecutor
                # Use conservative max_workers=5 for free-tier APIs (Yahoo Finance) to avoid rate limiting
                tickers_list = list(current_holdings.keys())
                max_workers = min(5, len(tickers_list))
                
                if len(tickers_list) > 0:
                    logger.info(f"  Fetching prices for {len(tickers_list)} tickers in parallel (max_workers={max_workers})...")
                    price_fetch_start = time.time()
                    
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        # Submit all tasks
                        future_to_ticker = {executor.submit(fetch_ticker_price, ticker): ticker for ticker in tickers_list}
                        
                        # Process completed tasks
                        completed = 0
                        for future in as_completed(future_to_ticker):
                            completed += 1
                            ticker, price, error_type = future.result()
                            
                            if price is not None:
                                current_prices[ticker] = price
                                if error_type == 'cached':
                                    logger.debug(f"    {ticker}: ${price} (cached)")
                                else:
                                    logger.debug(f"    {ticker}: ${price}")
                            else:
                                if error_type == 'rate_limit':
                                    rate_limit_errors += 1
                                    if rate_limit_errors == 1:
                                        logger.warning(f"  ⚠️  Rate limiting detected for {ticker}")
                                    failed_tickers.append(ticker)
                                elif error_type == 'no_data':
                                    logger.warning(f"    {ticker}: Could not fetch price (no data)")
                                    failed_tickers.append(ticker)
                                else:
                                    logger.warning(f"    {ticker}: Error fetching price")
                                    failed_tickers.append(ticker)
                    
                    price_fetch_time = time.time() - price_fetch_start
                    avg_time_per_ticker = price_fetch_time / len(tickers_list) if tickers_list else 0
                    logger.info(f"  Parallel fetch complete: {len(current_prices)} succeeded, {len(failed_tickers)} failed ({price_fetch_time:.2f}s, ~{avg_time_per_ticker:.2f}s per ticker)")
                    
                    if rate_limit_errors > 0:
                        logger.warning(f"  ⚠️  Rate limiting detected: {rate_limit_errors} tickers hit 429 errors")
                        logger.warning(f"     Consider: reducing max_workers, adding delays, or using API keys")
                
                if failed_tickers:
                    logger.warning(f"  Failed to fetch prices for {len(failed_tickers)} tickers: {failed_tickers}")
                    # If ALL tickers failed, skip this fund (don't create empty snapshot)
                    if len(failed_tickers) == len(current_holdings):
                        logger.warning(f"  All tickers failed for {fund_name} - skipping update")
                        continue
                
                # Create updated positions for target date
                # Only include positions where we successfully fetched prices
                updated_positions = []
                successful_tickers = []
                for ticker, holding in current_holdings.items():
                    if ticker in failed_tickers:
                        logger.warning(f"  Skipping {ticker} - price fetch failed")
                        continue
                    
                    current_price = current_prices.get(ticker)
                    if current_price is None:
                        continue
                    
                    shares = holding['shares']
                    cost_basis = holding['cost']
                    avg_price = cost_basis / shares if shares > 0 else Decimal('0')
                    market_value = shares * current_price
                    unrealized_pnl = market_value - cost_basis
                    
                    # Convert to base currency if needed
                    position_currency = holding['currency']
                    if position_currency == 'USD' and base_currency != 'USD':
                        # Convert USD position to base currency (e.g., CAD)
                        market_value_base = market_value * exchange_rate
                        cost_basis_base = cost_basis * exchange_rate
                        pnl_base = unrealized_pnl * exchange_rate
                        conversion_rate = exchange_rate
                    elif position_currency == base_currency:
                        # Already in base currency - no conversion
                        market_value_base = market_value
                        cost_basis_base = cost_basis
                        pnl_base = unrealized_pnl
                        conversion_rate = Decimal('1.0')
                    else:
                        # Other currency combinations not yet supported - store as-is
                        logger.warning(f"  Unsupported currency conversion: {position_currency} → {base_currency}")
                        market_value_base = market_value
                        cost_basis_base = cost_basis
                        pnl_base = unrealized_pnl
                        conversion_rate = Decimal('1.0')
                    
                    # CRITICAL: Create datetime with ET timezone, then convert to UTC for storage
                    # This ensures the timestamp is correctly interpreted regardless of server timezone
                    from datetime import datetime as dt
                    import pytz
                    et_tz = pytz.timezone('America/New_York')
                    # Create datetime at 4 PM ET (market close) for the target date
                    et_datetime = et_tz.localize(dt.combine(target_date, dt_time(16, 0)))
                    # Convert to UTC for storage (Supabase stores timestamps in UTC)
                    utc_datetime = et_datetime.astimezone(pytz.UTC)
                    
                    updated_positions.append({
                        'fund': fund_name,
                        'ticker': ticker,
                        'shares': float(shares),
                        'price': float(current_price),
                        'cost_basis': float(cost_basis),
                        'pnl': float(unrealized_pnl),
                        'currency': holding['currency'],
                        'date': utc_datetime.isoformat(),
                        # New: Pre-converted values in base currency
                        'base_currency': base_currency,
                        'total_value_base': float(market_value_base),
                        'cost_basis_base': float(cost_basis_base),
                        'pnl_base': float(pnl_base),
                        'exchange_rate': float(conversion_rate)
                    })
                    successful_tickers.append(ticker)
                
                if not updated_positions:
                    logger.warning(f"  No positions to update for {fund_name} (all tickers failed or no active positions)")
                    continue
                
                # Log summary
                logger.info(f"  Successfully fetched prices for {len(successful_tickers)}/{len(current_holdings)} tickers")
                
                # CRITICAL: Delete ALL existing positions for target date BEFORE inserting
                # This prevents duplicates - there should only be one snapshot per day
                # Use a more comprehensive delete query to ensure we catch all records
                start_of_day = datetime.combine(target_date, datetime.min.time()).isoformat()
                end_of_day = datetime.combine(target_date, datetime.max.time()).isoformat()
                
                # Delete in batches to handle large datasets
                deleted_total = 0
                while True:
                    # Get IDs of positions to delete (limit to avoid timeout)
                    existing_result = client.supabase.table("portfolio_positions")\
                        .select("id")\
                        .eq("fund", fund_name)\
                        .gte("date", start_of_day)\
                        .lte("date", end_of_day)\
                        .limit(1000)\
                        .execute()
                    
                    if not existing_result.data:
                        break
                    
                    # Delete by IDs
                    ids_to_delete = [row['id'] for row in existing_result.data]
                    delete_result = client.supabase.table("portfolio_positions")\
                        .delete()\
                        .in_("id", ids_to_delete)\
                        .execute()
                    
                    deleted_count = len(delete_result.data) if delete_result.data else len(ids_to_delete)
                    deleted_total += deleted_count
                    
                    # If we got fewer than 1000, we're done
                    if len(existing_result.data) < 1000:
                        break
                
                if deleted_total > 0:
                    logger.info(f"  Deleted {deleted_total} existing positions for {target_date} (preventing duplicates)")
                
                # ATOMIC UPDATE: Insert updated positions
                # If insert fails, we've already deleted old data, but that's OK - next run will fix it
                # For better safety, we could use a transaction, but Supabase doesn't support multi-table transactions easily
                # Instead, we ensure delete+insert happens atomically per fund
                if updated_positions:
                    try:
                        insert_result = client.supabase.table("portfolio_positions")\
                            .insert(updated_positions)\
                            .execute()
                        
                        inserted_count = len(insert_result.data) if insert_result.data else len(updated_positions)
                        total_positions_updated += inserted_count
                        total_funds_processed += 1
                        funds_completed.append(fund_name)  # Track successful completion
                        
                        logger.info(f"  ✅ Updated {inserted_count} positions for {fund_name}")
                    except Exception as insert_error:
                        # Insert failed - log error but don't fail entire job
                        # The delete already happened, so we'll have missing data until next run
                        # This is acceptable because:
                        # 1. Next run (15 min) will fix it
                        # 2. Historical data is preserved
                        # 3. We continue processing other funds
                        logger.error(f"  ❌ Failed to insert positions for {fund_name}: {insert_error}")
                        logger.warning(f"  ⚠️  {fund_name} has no positions for {target_date} until next run")
                        # Don't increment counters for failed insert
                else:
                    logger.warning(f"  No positions to insert for {fund_name} (all tickers failed price fetch)")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing fund {fund_name}: {e}", exc_info=True)
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Updated {total_positions_updated} positions across {total_funds_processed} fund(s) for {target_date}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
        # Mark job as completed successfully
        mark_job_completed('update_portfolio_prices', target_date, None, funds_completed)
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Portfolio price update job failed: {e}", exc_info=True)
        
        # Mark job as failed
        if 'target_date' in locals():
            mark_job_failed('update_portfolio_prices', target_date, None, str(e))
    finally:
        # Always release the lock, even if job fails
        _update_prices_lock.release()



def register_default_jobs(scheduler) -> None:
    """Register all default jobs with the scheduler.
    
    Called by start_scheduler() during initialization.
    """
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    
    # Exchange rates job - every 2 hours
    if AVAILABLE_JOBS['exchange_rates']['enabled_by_default']:
        scheduler.add_job(
            refresh_exchange_rates_job,
            trigger=IntervalTrigger(minutes=AVAILABLE_JOBS['exchange_rates']['default_interval_minutes']),
            id='exchange_rates',
            name='Refresh Exchange Rates',
            replace_existing=True
        )
        logger.info("Registered job: exchange_rates (every 2 hours)")
    
    # Performance metrics job - daily at 5 PM EST (after market close)
    if AVAILABLE_JOBS['performance_metrics']['enabled_by_default']:
        scheduler.add_job(
            populate_performance_metrics_job,
            trigger=CronTrigger(hour=17, minute=0, timezone='America/New_York'),
            id='performance_metrics',
            name='Populate Performance Metrics',
            replace_existing=True
        )
        logger.info("Registered job: performance_metrics (daily at 5 PM EST)")
    
    # Portfolio price update job - during market hours only (weekdays 9:30 AM - 4:00 PM EST)
    # NOTE: Exchange rates are NOT required for this job - positions are stored in native currency
    # Exchange rates are only used for display/calculation purposes, not for saving positions
    if AVAILABLE_JOBS['update_portfolio_prices']['enabled_by_default']:
        # Run every 15 minutes during market hours on weekdays
        # CronTrigger ensures we don't waste API calls overnight/weekends
        scheduler.add_job(
            update_portfolio_prices_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour='9-15',  # 9 AM to 3:45 PM (last run at 3:45 catches most of trading day)
                minute='0,15,30,45',
                timezone='America/New_York'
            ),
            id='update_portfolio_prices',
            name='Update Portfolio Prices',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )
        logger.info("Registered job: update_portfolio_prices (weekdays 9:00-15:45 EST, every 15 min)")
        
        # Market close job at 4:05 PM EST to get official closing prices
        # Extended misfire_grace_time: if system is down at 4:05 PM, retry ASAP within 4 hours
        # This ensures we capture closing prices even after a reboot
        scheduler.add_job(
            update_portfolio_prices_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=5,
                timezone='America/New_York'
            ),
            id='update_portfolio_prices_close',
            name='Update Portfolio Prices (Market Close)',
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60 * 60 * 4  # 4 hours - if missed, run when system comes back up
        )
        logger.info("Registered job: update_portfolio_prices_close (weekdays 4:05 PM EST, 4hr misfire grace)")
    
    # Market research job - 4 times daily at strategic times
    if AVAILABLE_JOBS['market_research']['enabled_by_default']:
        # Pre-Market: 08:00 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=8,
                minute=0,
                timezone='America/New_York'
            ),
            id='market_research_premarket',
            name='Market Research (Pre-Market)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_premarket (weekdays 8:00 AM EST)")
        
        # Mid-Morning: 11:00 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=11,
                minute=0,
                timezone='America/New_York'
            ),
            id='market_research_midmorning',
            name='Market Research (Mid-Morning)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_midmorning (weekdays 11:00 AM EST)")
        
        # Power Hour: 14:00 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=14,
                minute=0,
                timezone='America/New_York'
            ),
            id='market_research_powerhour',
            name='Market Research (Power Hour)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_powerhour (weekdays 2:00 PM EST)")
        
        # Post-Market: 16:30 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=30,
                timezone='America/New_York'
            ),
            id='market_research_postmarket',
            name='Market Research (Post-Market)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_postmarket (weekdays 4:30 PM EST)")
    
    # Market research job - 4 times daily at strategic times
    if AVAILABLE_JOBS['market_research']['enabled_by_default']:
        # Pre-Market: 08:00 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=8,
                minute=0,
                timezone='America/New_York'
            ),
            id='market_research_premarket',
            name='Market Research (Pre-Market)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_premarket (weekdays 8:00 AM EST)")
        
        # Mid-Morning: 11:00 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=11,
                minute=0,
                timezone='America/New_York'
            ),
            id='market_research_midmorning',
            name='Market Research (Mid-Morning)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_midmorning (weekdays 11:00 AM EST)")
        
        # Power Hour: 14:00 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=14,
                minute=0,
                timezone='America/New_York'
            ),
            id='market_research_powerhour',
            name='Market Research (Power Hour)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_powerhour (weekdays 2:00 PM EST)")
        
        # Post-Market: 16:30 EST (Mon-Fri)
        scheduler.add_job(
            market_research_job,
            trigger=CronTrigger(
                day_of_week='mon-fri',
                hour=16,
                minute=30,
                timezone='America/New_York'
            ),
            id='market_research_postmarket',
            name='Market Research (Post-Market)',
            replace_existing=True
        )
        logger.info("Registered job: market_research_postmarket (weekdays 4:30 PM EST)")

        # Ticker Research: Every 6 hours
        scheduler.add_job(
            ticker_research_job,
            trigger=CronTrigger(
                hour='*/6',
                minute=15,
                timezone='America/New_York'
            ),
            id='ticker_research_job',
            name='Ticker Specific Research',
            replace_existing=True
        )
        logger.info("Registered job: ticker_research_job (every 6 hours)")
