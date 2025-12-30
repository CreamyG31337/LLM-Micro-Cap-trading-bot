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
from typing import Dict, Any, Optional, List
from decimal import Decimal
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from scheduler.scheduler_core import log_job_execution


logger = logging.getLogger(__name__)

# Add project root to path for utils imports if running from web_dashboard
import sys
import os
from pathlib import Path

# If running from web_dashboard/scheduler, go up two levels
current_dir = Path(__file__).resolve().parent
if current_dir.name == 'scheduler':
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))



# Job definitions with metadata
AVAILABLE_JOBS: Dict[str, Dict[str, Any]] = {
    'exchange_rates': {
        'name': 'Refresh Exchange Rates',
        'description': 'Fetch latest USD/CAD exchange rate and store in database',
        'default_interval_minutes': 120,  # Every 2 hours
        'enabled_by_default': True,
        'icon': '💰'
    },
    'performance_metrics': {
        'name': 'Populate Performance Metrics',
        'description': 'Aggregate daily portfolio performance into metrics table',
        'default_interval_minutes': 1440,  # Once per day
        'enabled_by_default': True,
        'icon': '📊'
    },
    'update_portfolio_prices': {
        'name': 'Update Portfolio Prices',
        'description': 'Fetch current stock prices and update portfolio positions for today',
        'default_interval_minutes': 15,  # Every 15 minutes during market hours
        'enabled_by_default': True,
        'icon': '📈'
    },
    'market_research': {
        'name': 'Market Research Collection',
        'description': 'Scrape and store general market news articles',
        'default_interval_minutes': 360,  # Every 6 hours (but uses cron triggers instead)
        'enabled_by_default': True,
        'icon': '📰'
    },
    'ticker_research': {
        'name': 'Ticker Research Collection',
        'description': 'Fetch news for specific companies in the portfolio',
        'default_interval_minutes': 360,  # Every 6 hours
        'enabled_by_default': True,
        'icon': '🔍'
    },
    'opportunity_discovery': {
        'name': 'Opportunity Discovery',
        'description': 'Hunt for new investment opportunities using targeted search queries',
        'default_interval_minutes': 720,  # Every 12 hours
        'enabled_by_default': True,
        'icon': '🔍'
    },
    'benchmark_refresh': {
        'name': 'Refresh Benchmark Data',
        'description': 'Fetch and cache benchmark data (S&P 500, QQQ, Russell 2000, VTI) for chart performance',
        'default_interval_minutes': 1440,  # Once per day
        'enabled_by_default': True,
        'icon': '📊',
        'cron_triggers': [
            {'hour': 15, 'minute': 15, 'timezone': 'America/Los_Angeles'}  # 15:15 PST / 18:15 EST - after market close
        ]
    },
    'social_sentiment': {
        'name': 'Social Sentiment Tracking',
        'description': 'Fetch retail hype and sentiment from StockTwits and Reddit',
        'default_interval_minutes': 30,  # Every 30 minutes
        'enabled_by_default': True,
        'icon': '💬'
    },
    'social_metrics_cleanup': {
        'name': 'Social Metrics Cleanup',
        'description': 'Daily cleanup: remove raw_data JSON after 14 days, delete rows after 60 days',
        'default_interval_minutes': 1440,  # Once per day
        'enabled_by_default': True,
        'icon': '🧹'
    },
    'social_sentiment_ai': {
        'name': 'Social Sentiment AI Analysis',
        'description': 'Extract posts, create sessions, and perform AI analysis on social sentiment data',
        'default_interval_minutes': 60,  # Every hour
        'enabled_by_default': True,
        'icon': '🤖'
    },
    'congress_trades': {
        'name': 'Fetch Congress Trades',
        'description': 'Fetch and analyze congressional stock trades from FMP API',
        'default_interval_minutes': 360,  # 6 hours (but uses cron triggers)
        'enabled_by_default': True,
        'icon': '🏛️'
    },
    'analyze_congress_trades': {
        'name': 'Analyze Congress Trades',
        'description': 'Calculate conflict scores for unscored congress trades using committee data',
        'default_interval_minutes': 30,  # Every 30 minutes
        'enabled_by_default': False,  # DISABLED during session backfill - re-enable after
        'icon': '🔍'
    },
    'rss_feed_ingest': {
        'name': 'RSS Feed Ingestion',
        'description': 'Fetch articles from validated RSS feeds (Push strategy)',
        'default_interval_minutes': 180,  # Every 3 hours
        'enabled_by_default': True,
        'icon': '📡'
    },
    'alpha_research': {
        'name': 'Alpha Hunter',
        'description': 'Targeted research on high-value alpha domains',
        'default_interval_minutes': 360,  # Every 6 hours
        'enabled_by_default': True,
        'icon': '🦊'
    },
    'rescore_congress_sessions': {
        'name': 'Rescore Congress Sessions (Manual)',
        'description': 'One-time backfill: Rescore 1000 sessions with new AI logic',
        'default_interval_minutes': 0,  # Manual only, no schedule
        'enabled_by_default': False,  # Manual execution only
        'icon': '🔄',
        'parameters': {
            'limit': {
                'type': 'number', 
                'default': 1000, 
                'description': 'Number of sessions to process'
            },
            'batch_size': {
                'type': 'number', 
                'default': 10, 
                'description': 'Sessions to process per batch'
            },
            'model': {
                'type': 'text', 
                'default': 'granite3.3:8b', 
                'description': 'Ollama model name'
            }
        }
    }
}


def get_job_icon(job_id: str) -> str:
    """Get the icon emoji for a job ID.
    
    Handles special cases for job variants:
    - update_portfolio_prices_close uses same icon as update_portfolio_prices
    - market_research_* variants use same icon as market_research
    - ticker_research_job uses icon from ticker_research
    - opportunity_discovery_job uses icon from opportunity_discovery
    
    Args:
        job_id: The job identifier
        
    Returns:
        Icon emoji string, or empty string if not found
    """
    # Handle special cases for job variants
    if job_id == 'update_portfolio_prices_close':
        job_id = 'update_portfolio_prices'
    elif job_id.startswith('market_research_'):
        job_id = 'market_research'
    elif job_id == 'ticker_research_job':
        job_id = 'ticker_research'
    elif job_id == 'opportunity_discovery_job':
        job_id = 'opportunity_discovery'
    
    # Look up icon from AVAILABLE_JOBS
    if job_id in AVAILABLE_JOBS:
        return AVAILABLE_JOBS[job_id].get('icon', '')
    
    return ''


def benchmark_refresh_job() -> None:
    """Refresh benchmark data cache for chart performance.
    
    This job:
    1. Fetches latest benchmark data from Yahoo Finance
    2. Caches it in the benchmark_data table
    3. Ensures charts always have up-to-date market index data
    
    Benchmarks refreshed:
    - S&P 500 (^GSPC)
    - Nasdaq-100 (QQQ)
    - Russell 2000 (^RUT)
    - Total Market (VTI)
    """
    job_id = 'benchmark_refresh'
    start_time = time.time()
    target_date = datetime.now(timezone.utc).date()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting benchmark refresh job...")
        
        # Mark job as started in database
        mark_job_started('benchmark_refresh', target_date)
        
        # Import dependencies
        try:
            import yfinance as yf
            from supabase_client import SupabaseClient
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Initialize Supabase client (use service role for writing)
        client = SupabaseClient(use_service_role=True)
        
        # Define benchmarks to refresh
        benchmarks = [
            {"ticker": "^GSPC", "name": "S&P 500"},
            {"ticker": "QQQ", "name": "Nasdaq-100"},
            {"ticker": "^RUT", "name": "Russell 2000"},
            {"ticker": "VTI", "name": "Total Market"}
        ]
        
        # Fetch data for the last 30 days to ensure we have recent data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        benchmarks_updated = 0
        benchmarks_failed = 0
        total_rows_cached = 0
        
        for benchmark in benchmarks:
            ticker = benchmark["ticker"]
            name = benchmark["name"]
            
            try:
                logger.info(f"Fetching {name} ({ticker})...")
                
                # Fetch data from Yahoo Finance
                data = yf.download(
                    ticker,
                    start=start_date,
                    end=end_date,
                    progress=False,
                    auto_adjust=False
                )
                
                if data.empty:
                    logger.warning(f"No data available for {name} ({ticker})")
                    benchmarks_failed += 1
                    continue
                
                # Reset index to get Date as a column
                data = data.reset_index()
                
                # Handle MultiIndex columns from yfinance
                if hasattr(data.columns, 'levels'):
                    data.columns = data.columns.get_level_values(0)
                
                # Convert to list of dicts for caching
                rows = data.to_dict('records')
                
                # Cache in database
                if client.cache_benchmark_data(ticker, rows):
                    total_rows_cached += len(rows)
                    benchmarks_updated += 1
                    logger.info(f"✅ Cached {len(rows)} rows for {name} ({ticker})")
                else:
                    benchmarks_failed += 1
                    logger.warning(f"Failed to cache data for {name} ({ticker})")
                
            except Exception as e:
                logger.error(f"Error fetching {name} ({ticker}): {e}")
                benchmarks_failed += 1
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Updated {benchmarks_updated} benchmarks ({total_rows_cached} rows), {benchmarks_failed} failed"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('benchmark_refresh', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('benchmark_refresh', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
        logger.error(f"❌ Benchmark refresh job failed: {e}", exc_info=True)


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
    target_date = datetime.now(timezone.utc).date()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting market research job...")
        
        # Mark job as started in database
        mark_job_started('market_research', target_date)
        
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
                summary_data = {}
                extracted_tickers = []
                extracted_sector = None
                embedding = None
                if ollama_client:
                    logger.info(f"Generating summary for: {title[:50]}...")
                    summary_data = ollama_client.generate_summary(content)
                    
                    # Handle backward compatibility: if old string format is returned
                    if isinstance(summary_data, str):
                        summary = summary_data
                        logger.debug("Received old string format summary, using as-is")
                    elif isinstance(summary_data, dict) and summary_data:
                        summary = summary_data.get("summary", "")
                        
                        # Extract ticker and sector from structured data
                        tickers = summary_data.get("tickers", [])
                        sectors = summary_data.get("sectors", [])
                        
                        # Extract all validated tickers
                        from research_utils import validate_ticker_format, normalize_ticker
                        for ticker in tickers:
                            # Validate format only (reject company names, invalid formats)
                            # NOTE: We no longer check if ticker appears in content, because AI infers tickers
                            # from company names (e.g., "Apple" -> "AAPL"). The AI marks uncertain tickers with '?'
                            if not validate_ticker_format(ticker):
                                logger.warning(f"Rejected invalid ticker format: {ticker} (likely company name or invalid format)")
                                continue
                            normalized = normalize_ticker(ticker)
                            if normalized:
                                extracted_tickers.append(normalized)
                                logger.debug(f"Extracted ticker from article: {normalized}")
                        
                        if extracted_tickers:
                            logger.info(f"Extracted {len(extracted_tickers)} validated ticker(s): {extracted_tickers}")
                        
                        # Use first sector if available
                        if sectors:
                            extracted_sector = sectors[0]
                            logger.info(f"Extracted sector from article: {extracted_sector}")
                        
                        # Log extracted metadata
                        if tickers or sectors:
                            logger.debug(f"Extracted metadata - Tickers: {tickers}, Sectors: {sectors}, Themes: {summary_data.get('key_themes', [])}")
                    
                    if not summary:
                        logger.warning(f"Failed to generate summary for {title[:50]}...")
                    
                    # Generate embedding for semantic search
                    logger.debug(f"Generating embedding for: {title[:50]}...")
                    embedding = ollama_client.generate_embedding(content[:6000])  # Truncate to avoid token limits
                    if not embedding:
                        logger.warning(f"Failed to generate embedding for {title[:50]}...")
                else:
                    logger.debug("Ollama not available - skipping summary and embedding generation")
                
                # Calculate relevance score (market_research_job doesn't check owned tickers - always 0.5 for general market news)
                relevance_score = calculate_relevance_score(extracted_tickers, extracted_sector, owned_tickers=None)
                
                # Extract logic_check for relationship confidence scoring
                logic_check = summary_data.get("logic_check") if isinstance(summary_data, dict) else None
                
                # Save article to database
                article_id = research_repo.save_article(
                    tickers=extracted_tickers if extracted_tickers else None,  # Use extracted tickers if available
                    sector=extracted_sector,  # Use extracted sector if available
                    article_type="market_news",
                    title=extracted.get('title') or title,
                    url=url,
                    summary=summary,
                    content=content,
                    source=extracted.get('source'),
                    published_at=extracted.get('published_at'),
                    relevance_score=relevance_score,
                    embedding=embedding,
                    claims=summary_data.get("claims") if isinstance(summary_data, dict) else None,
                    fact_check=summary_data.get("fact_check") if isinstance(summary_data, dict) else None,
                    conclusion=summary_data.get("conclusion") if isinstance(summary_data, dict) else None,
                    sentiment=summary_data.get("sentiment") if isinstance(summary_data, dict) else None,
                    sentiment_score=summary_data.get("sentiment_score") if isinstance(summary_data, dict) else None,
                    logic_check=logic_check
                )
                
                if article_id:
                    articles_saved += 1
                    logger.info(f"✅ Saved article: {title[:50]}...")
                    
                    # Extract and save relationships (GraphRAG edges)
                    if isinstance(summary_data, dict) and logic_check and logic_check != "HYPE_DETECTED":
                        relationships = summary_data.get("relationships", [])
                        if relationships and isinstance(relationships, list):
                            # Calculate initial confidence based on logic_check
                            if logic_check == "DATA_BACKED":
                                initial_confidence = 0.8
                            else:  # NEUTRAL
                                initial_confidence = 0.4
                            
                            # Normalize and save each relationship
                            from research_utils import normalize_relationship
                            relationships_saved = 0
                            for rel in relationships:
                                if isinstance(rel, dict):
                                    source = rel.get("source", "").strip()
                                    target = rel.get("target", "").strip()
                                    rel_type = rel.get("type", "").strip()
                                    
                                    if source and target and rel_type:
                                        # Normalize relationship direction (Option A: Supplier -> Buyer)
                                        norm_source, norm_target, norm_type = normalize_relationship(source, target, rel_type)
                                        
                                        # Save relationship
                                        rel_id = research_repo.save_relationship(
                                            source_ticker=norm_source,
                                            target_ticker=norm_target,
                                            relationship_type=norm_type,
                                            initial_confidence=initial_confidence,
                                            source_article_id=article_id
                                        )
                                        if rel_id:
                                            relationships_saved += 1
                            
                            if relationships_saved > 0:
                                logger.info(f"✅ Saved {relationships_saved} relationship(s) from article: {title[:50]}...")
                else:
                    logger.warning(f"Failed to save article: {title[:50]}...")
                
                articles_processed += 1
                
            except Exception as e:
                logger.error(f"Error processing article '{title[:50]}...': {e}")
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Processed {articles_processed} articles: {articles_saved} saved, {articles_skipped} skipped, {articles_blacklisted} blacklisted"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('market_research', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('market_research', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
        logger.error(f"❌ Market research job failed: {e}", exc_info=True)


def rss_feed_ingest_job() -> None:
    """Ingest articles from validated RSS feeds (Push strategy).
    
    This job:
    1. Fetches all enabled RSS feeds from database
    2. Parses each feed for new articles
    3. Applies junk filtering before AI processing
    4. Saves high-quality articles to research database
    """
    job_id = 'rss_feed_ingest'
    start_time = time.time()
    target_date = datetime.now(timezone.utc).date()
   
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting RSS feed ingestion job...")
        
        # Mark job as started in database
        mark_job_started('rss_feed_ingest', target_date)
        
        # Import dependencies
        try:
            from rss_utils import get_rss_client
            from research_utils import extract_article_content
            from ollama_client import get_ollama_client
            from research_repository import ResearchRepository
            from postgres_client import PostgresClient
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Get clients
        rss_client = get_rss_client()
        ollama_client = get_ollama_client()
        research_repo = ResearchRepository()
        postgres_client = PostgresClient()
        
        # Fetch enabled RSS feeds from database
        try:
            feeds_result = postgres_client.execute_query(
                "SELECT id, name, url FROM rss_feeds WHERE enabled = true"
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Error fetching RSS feeds from database: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        if not feeds_result:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No enabled RSS feeds found"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        logger.info(f"Found {len(feeds_result)} enabled RSS feeds")
        
        total_articles_processed = 0
        total_articles_saved = 0
        total_articles_skipped = 0
        total_junk_filtered = 0  # NEW: Track junk filtering
        feeds_processed = 0
        feeds_failed = 0
        
        # Get owned tickers for relevance scoring
        from supabase_client import SupabaseClient
        client = SupabaseClient(use_service_role=True)
        funds_result = client.supabase.table("funds").select("name").eq("is_production", True).execute()
        
        owned_tickers = set()
        if funds_result.data:
            prod_funds = [f['name'] for f in funds_result.data]
            positions_result = client.supabase.table("latest_positions").select("ticker").in_("fund", prod_funds).execute()
            if positions_result.data:
                owned_tickers = set(pos['ticker'] for pos in positions_result.data)
        
        # Process each feed
        for feed in feeds_result:
            feed_id = feed['id']
            feed_name = feed['name']
            feed_url = feed['url']
            
            try:
                logger.info(f"📡 Fetching feed: {feed_name}")
                
                # Fetch and parse RSS feed
                feed_data = rss_client.fetch_feed(feed_url)
                
                if not feed_data or not feed_data.get('items'):
                    logger.warning(f"No items found in feed: {feed_name}")
                    feeds_failed += 1
                    continue
                
                items = feed_data['items']
                junk_filtered = feed_data.get('junk_filtered', 0)
                total_junk_filtered += junk_filtered
                
                logger.info(f"  Found {len(items)} items (filtered {junk_filtered} junk articles)")
                
                # Process each item
                for item in items:
                    try:
                        url = item.get('url')
                        title = item.get('title')
                        content = item.get('content', '')
                        
                        if not url or not title:
                            continue
                        
                        # Check if already exists
                        if research_repo.article_exists(url):
                            logger.debug(f"Article already exists: {title[:50]}...")
                            total_articles_skipped += 1
                            continue
                        
                        # Use RSS content if available, otherwise fetch from URL
                        if not content or len(content) < 200:
                            logger.info(f"  Extracting full content: {title[:40]}...")
                            extracted = extract_article_content(url)
                            content = extracted.get('content', '')
                            if not content:
                                logger.warning(f"Failed to extract content for {title[:40]}...")
                                continue
                        
                        # Generate AI summary and embedding
                        summary = None
                        summary_data = {}
                        extracted_tickers = item.get('tickers', []) or []  # May be from RSS metadata
                        extracted_sector = None
                        embedding = None
                        
                        if ollama_client:
                            summary_data = ollama_client.generate_summary(content)
                            
                            if isinstance(summary_data, str):
                                summary = summary_data
                            elif isinstance(summary_data, dict) and summary_data:
                                summary = summary_data.get("summary", "")
                                
                                # Extract tickers from AI if not already from RSS
                                if not extracted_tickers:
                                    ai_tickers = summary_data.get("tickers", [])
                                    from research_utils import validate_ticker_format, normalize_ticker
                                    for ticker in ai_tickers:
                                        # Only validate format, trust AI inference (AI marks uncertain tickers with '?')
                                        if validate_ticker_format(ticker):
                                            normalized = normalize_ticker(ticker)
                                            if normalized:
                                                extracted_tickers.append(normalized)
                                
                                # Extract sector
                                sectors = summary_data.get("sectors", [])
                                if sectors:
                                    extracted_sector = sectors[0]
                            
                            # Generate embedding
                            embedding = ollama_client.generate_embedding(content[:6000])
                        
                        # Calculate relevance score
                        relevance_score = calculate_relevance_score(
                            extracted_tickers if extracted_tickers else [],
                            extracted_sector,
                            owned_tickers=list(owned_tickers) if owned_tickers else None
                        )
                        
                        # Extract logic_check for relationship confidence
                        logic_check = summary_data.get("logic_check") if isinstance(summary_data, dict) else None
                        
                        # Save article
                        article_id = research_repo.save_article(
                            tickers=extracted_tickers if extracted_tickers else None,
                            sector=extracted_sector,
                            article_type="market_news",  # RSS feeds are general news
                            title=title,
                            url=url,
                            summary=summary,
                            content=content,
                            source=item.get('source'),
                            published_at=item.get('published_at'),
                            relevance_score=relevance_score,
                            embedding=embedding,
                            claims=summary_data.get("claims") if isinstance(summary_data, dict) else None,
                            fact_check=summary_data.get("fact_check") if isinstance(summary_data, dict) else None,
                            conclusion=summary_data.get("conclusion") if isinstance(summary_data, dict) else None,
                            sentiment=summary_data.get("sentiment") if isinstance(summary_data, dict) else None,
                            sentiment_score=summary_data.get("sentiment_score") if isinstance(summary_data, dict) else None,
                            logic_check=logic_check
                        )
                        
                        if article_id:
                            total_articles_saved += 1
                            logger.info(f"  ✅ Saved: {title[:40]}...")
                            
                            # Extract and save relationships
                            if isinstance(summary_data, dict) and logic_check and logic_check != "HYPE_DETECTED":
                                relationships = summary_data.get("relationships", [])
                                if relationships and isinstance(relationships, list):
                                    if logic_check == "DATA_BACKED":
                                        initial_confidence = 0.8
                                    else:
                                        initial_confidence = 0.4
                                    
                                    from research_utils import normalize_relationship
                                    relationships_saved = 0
                                    for rel in relationships:
                                        if isinstance(rel, dict):
                                            source = rel.get("source", "").strip()
                                            target = rel.get("target", "").strip()
                                            rel_type = rel.get("type", "").strip()
                                            
                                            if source and target and rel_type:
                                                norm_source, norm_target, norm_type = normalize_relationship(source, target, rel_type)
                                                rel_id = research_repo.save_relationship(
                                                    source_ticker=norm_source,
                                                    target_ticker=norm_target,
                                                    relationship_type=norm_type,
                                                    initial_confidence=initial_confidence,
                                                    source_article_id=article_id
                                                )
                                                if rel_id:
                                                    relationships_saved += 1
                                    
                                    if relationships_saved > 0:
                                        logger.info(f"  ✅ Saved {relationships_saved} relationship(s)")
                        
                        total_articles_processed += 1
                        time.sleep(0.5)  # Small delay between articles
                        
                    except Exception as e:
                        logger.error(f"Error processing RSS item: {e}")
                        continue
                
                # Update feed's last_fetched_at timestamp
                try:
                    postgres_client.execute_update(
                        "UPDATE rss_feeds SET last_fetched_at = NOW() WHERE id = %s",
                        (feed_id,)
                    )
                except Exception as e:
                    logger.warning(f"Failed to update last_fetched_at for {feed_name}: {e}")
                
                feeds_processed += 1
                time.sleep(2)  # Delay between feeds
                
            except Exception as e:
                logger.error(f"Error processing feed '{feed_name}': {e}")
                feeds_failed += 1
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Processed {feeds_processed} feeds: {total_articles_saved} saved, {total_articles_skipped} skipped, {total_junk_filtered} junk filtered"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('rss_feed_ingest', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('rss_feed_ingest', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass
        logger.error(f"❌ RSS feed ingestion job failed: {e}", exc_info=True)



def ticker_research_job() -> None:
    """Fetch news for companies held in the portfolio.
    
    This job:
    1. Identifies all tickers held in production funds
    2. Searches for news specific to each ticker + company name
    3. Saves relevant articles to the database
    """
    job_id = 'ticker_research'
    start_time = time.time()
    target_date = datetime.now(timezone.utc).date()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting ticker research job...")
        
        # Mark job as started in database
        mark_job_started('ticker_research', target_date)
        
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
        # Using the latest_positions view is easiest as it aggregates valid positions
        positions_result = client.supabase.table("latest_positions")\
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
        
        # Separate ETFs from regular tickers
        # ETFs will be researched by sector instead
        etf_tickers = {}
        regular_tickers = {}
        
        for ticker, company in targets.items():
            # Check if ticker or company name contains "ETF" (case-insensitive)
            is_etf = (
                'etf' in ticker.lower() or 
                (company and 'etf' in company.lower())
            )
            
            if is_etf:
                etf_tickers[ticker] = company
            else:
                regular_tickers[ticker] = company
        
        # Get sectors for ETF tickers from securities table
        etf_sectors = set()
        if etf_tickers:
            etf_ticker_list = list(etf_tickers.keys())
            # Query securities table for sector information
            # Need to query in batches if there are many ETFs
            batch_size = 50
            for i in range(0, len(etf_ticker_list), batch_size):
                batch = etf_ticker_list[i:i + batch_size]
                try:
                    securities_result = client.supabase.table("securities")\
                        .select("ticker, sector")\
                        .in_("ticker", batch)\
                        .execute()
                    
                    for sec in securities_result.data:
                        sector = sec.get('sector')
                        if sector and sector.strip():
                            etf_sectors.add(sector.strip())
                except Exception as e:
                    logger.warning(f"Error fetching sectors for ETFs: {e}")
        
        if etf_tickers:
            logger.info(f"Found {len(etf_tickers)} ETF tickers (skipping direct research): {list(etf_tickers.keys())}")
            if etf_sectors:
                logger.info(f"Will research {len(etf_sectors)} sectors instead: {sorted(etf_sectors)}")
            else:
                logger.warning("No sector information found for ETFs - they will be skipped")
        
        logger.info(f"Found {len(regular_tickers)} regular tickers to research: {list(regular_tickers.keys())}")
        
        # Create owned_tickers set for relevance scoring (includes both ETFs and regular tickers)
        owned_tickers = set(targets.keys())
        
        articles_saved = 0
        articles_failed = 0
        tickers_processed = 0
        sectors_researched = 0
        
        # 3. Research sectors for ETFs first
        for sector in sorted(etf_sectors):
            try:
                query = f"{sector} sector news investment"
                logger.info(f"🔎 Researching sector for ETFs: '{query}'")
                
                search_results = searxng_client.search_news(query=query, max_results=5)
                
                if not search_results or not search_results.get('results'):
                    logger.debug(f"No results for sector: {sector}")
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
                        summary_data = {}
                        embedding = None
                        if ollama_client:
                            summary_data = ollama_client.generate_summary(content)
                            
                            if isinstance(summary_data, str):
                                summary = summary_data
                            elif isinstance(summary_data, dict) and summary_data:
                                summary = summary_data.get("summary", "")
                            
                            # Generate embedding for semantic search
                            embedding = ollama_client.generate_embedding(content[:6000])
                            if not embedding:
                                logger.warning(f"Failed to generate embedding for sector {sector}")
                        
                        # Extract logic_check for relationship confidence scoring
                        logic_check = summary_data.get("logic_check") if isinstance(summary_data, dict) else None
                        
                        # Save with sector but no specific ticker (since it's ETF sector research)
                        article_id = research_repo.save_article(
                            tickers=None,  # No specific ticker for ETF sector research
                            sector=sector,
                            article_type="ticker_news",  # Still use ticker_news type
                            title=extracted.get('title') or title,
                            url=url,
                            summary=summary,
                            content=content,
                            source=extracted.get('source'),
                            published_at=extracted.get('published_at'),
                            relevance_score=0.7,  # Slightly lower relevance for sector-level news
                            embedding=embedding,
                            claims=summary_data.get("claims") if isinstance(summary_data, dict) else None,
                            fact_check=summary_data.get("fact_check") if isinstance(summary_data, dict) else None,
                            conclusion=summary_data.get("conclusion") if isinstance(summary_data, dict) else None,
                            sentiment=summary_data.get("sentiment") if isinstance(summary_data, dict) else None,
                            sentiment_score=summary_data.get("sentiment_score") if isinstance(summary_data, dict) else None,
                            logic_check=logic_check
                        )
                        
                        if article_id:
                            articles_saved += 1
                            logger.info(f"  ✅ Saved sector news: {title[:30]}")
                            
                            # Extract and save relationships (GraphRAG edges)
                            if isinstance(summary_data, dict) and logic_check and logic_check != "HYPE_DETECTED":
                                relationships = summary_data.get("relationships", [])
                                if relationships and isinstance(relationships, list):
                                    # Calculate initial confidence based on logic_check
                                    if logic_check == "DATA_BACKED":
                                        initial_confidence = 0.8
                                    else:  # NEUTRAL
                                        initial_confidence = 0.4
                                    
                                    # Normalize and save each relationship
                                    from research_utils import normalize_relationship
                                    relationships_saved = 0
                                    for rel in relationships:
                                        if isinstance(rel, dict):
                                            source = rel.get("source", "").strip()
                                            target = rel.get("target", "").strip()
                                            rel_type = rel.get("type", "").strip()
                                            
                                            if source and target and rel_type:
                                                # Normalize relationship direction (Option A: Supplier -> Buyer)
                                                norm_source, norm_target, norm_type = normalize_relationship(source, target, rel_type)
                                                
                                                # Save relationship
                                                rel_id = research_repo.save_relationship(
                                                    source_ticker=norm_source,
                                                    target_ticker=norm_target,
                                                    relationship_type=norm_type,
                                                    initial_confidence=initial_confidence,
                                                    source_article_id=article_id
                                                )
                                                if rel_id:
                                                    relationships_saved += 1
                                    
                                    if relationships_saved > 0:
                                        logger.info(f"  ✅ Saved {relationships_saved} relationship(s) from sector article: {title[:30]}")
                        
                        # Small delay between articles
                        time.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing sector article for {sector}: {e}")
                        articles_failed += 1
                
                sectors_researched += 1
                
                # Delay between sectors
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error researching sector {sector}: {e}")
        
        # 4. Iterate and search for each regular (non-ETF) ticker
        for ticker, company in regular_tickers.items():
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
                        summary_data = {}
                        extracted_tickers = []
                        extracted_sector = None
                        embedding = None
                        if ollama_client:
                            summary_data = ollama_client.generate_summary(content)
                            
                            # Handle backward compatibility: if old string format is returned
                            if isinstance(summary_data, str):
                                summary = summary_data
                                logger.debug("Received old string format summary, using as-is")
                            elif isinstance(summary_data, dict) and summary_data:
                                summary = summary_data.get("summary", "")
                                
                                # Extract ticker and sector from structured data
                                tickers = summary_data.get("tickers", [])
                                sectors = summary_data.get("sectors", [])
                                
                                # Extract all validated tickers
                                from research_utils import validate_ticker_in_content, validate_ticker_format
                                for candidate_ticker in tickers:
                                    # First validate format (reject company names, invalid formats)
                                    if not validate_ticker_format(candidate_ticker):
                                        logger.warning(f"Rejected invalid ticker format: {candidate_ticker} (likely company name or invalid format)")
                                        continue
                                    # Then validate it appears in content
                                    if validate_ticker_in_content(candidate_ticker, content):
                                        extracted_tickers.append(candidate_ticker)
                                        logger.debug(f"Extracted ticker from article: {candidate_ticker} (validated in content)")
                                    else:
                                        logger.warning(f"Ticker {candidate_ticker} not found in article content - skipping")
                                
                                if extracted_tickers:
                                    logger.info(f"Extracted {len(extracted_tickers)} validated ticker(s): {extracted_tickers}")
                                
                                # Use first sector if available
                                if sectors:
                                    extracted_sector = sectors[0]
                                    logger.info(f"Extracted sector from article: {extracted_sector}")
                                
                                # Log extracted metadata
                                if tickers or sectors or summary_data.get("key_themes"):
                                    logger.debug(f"Extracted metadata - Tickers: {tickers}, Sectors: {sectors}, Themes: {summary_data.get('key_themes', [])}")
                            
                            # Generate embedding for semantic search
                            embedding = ollama_client.generate_embedding(content[:6000])  # Truncate to avoid token limits
                            if not embedding:
                                logger.warning(f"Failed to generate embedding for {ticker}")
                        
                        # If AI didn't extract any tickers, use the search ticker (we're searching for it, so it's relevant)
                        if not extracted_tickers:
                            extracted_tickers = [ticker]
                        
                        # Calculate relevance score (check if any tickers are owned)
                        relevance_score = calculate_relevance_score(extracted_tickers, extracted_sector, owned_tickers=owned_tickers)
                        
                        # Extract logic_check for relationship confidence scoring
                        logic_check = summary_data.get("logic_check") if isinstance(summary_data, dict) else None
                        
                        # Save article
                        article_id = research_repo.save_article(
                            tickers=extracted_tickers,
                            sector=extracted_sector,  # Use extracted sector if available
                            article_type="ticker_news",
                            title=extracted.get('title') or title,
                            url=url,
                            summary=summary,
                            content=content,
                            source=extracted.get('source'),
                            published_at=extracted.get('published_at'),
                            relevance_score=relevance_score,
                            embedding=embedding,
                            claims=summary_data.get("claims") if isinstance(summary_data, dict) else None,
                            fact_check=summary_data.get("fact_check") if isinstance(summary_data, dict) else None,
                            conclusion=summary_data.get("conclusion") if isinstance(summary_data, dict) else None,
                            sentiment=summary_data.get("sentiment") if isinstance(summary_data, dict) else None,
                            sentiment_score=summary_data.get("sentiment_score") if isinstance(summary_data, dict) else None,
                            logic_check=logic_check
                        )
                        
                        if article_id:
                            articles_saved += 1
                            logger.info(f"  ✅ Saved: {title[:30]}")
                            
                            # Extract and save relationships (GraphRAG edges)
                            if isinstance(summary_data, dict) and logic_check and logic_check != "HYPE_DETECTED":
                                relationships = summary_data.get("relationships", [])
                                if relationships and isinstance(relationships, list):
                                    # Calculate initial confidence based on logic_check
                                    if logic_check == "DATA_BACKED":
                                        initial_confidence = 0.8
                                    else:  # NEUTRAL
                                        initial_confidence = 0.4
                                    
                                    # Normalize and save each relationship
                                    from research_utils import normalize_relationship
                                    relationships_saved = 0
                                    for rel in relationships:
                                        if isinstance(rel, dict):
                                            source = rel.get("source", "").strip()
                                            target = rel.get("target", "").strip()
                                            rel_type = rel.get("type", "").strip()
                                            
                                            if source and target and rel_type:
                                                # Normalize relationship direction (Option A: Supplier -> Buyer)
                                                norm_source, norm_target, norm_type = normalize_relationship(source, target, rel_type)
                                                
                                                # Save relationship
                                                rel_id = research_repo.save_relationship(
                                                    source_ticker=norm_source,
                                                    target_ticker=norm_target,
                                                    relationship_type=norm_type,
                                                    initial_confidence=initial_confidence,
                                                    source_article_id=article_id
                                                )
                                                if rel_id:
                                                    relationships_saved += 1
                                    
                                    if relationships_saved > 0:
                                        logger.info(f"  ✅ Saved {relationships_saved} relationship(s) from article: {title[:30]}")
                        
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
        message_parts = [f"Processed {tickers_processed} tickers"]
        if sectors_researched > 0:
            message_parts.append(f"{sectors_researched} sectors (for ETFs)")
        message_parts.append(f"Saved {articles_saved} new articles")
        message = ". ".join(message_parts) + "."
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('ticker_research', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('ticker_research', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
        logger.error(f"❌ Ticker research job failed: {e}", exc_info=True)


def opportunity_discovery_job() -> None:
    """Hunt for new investment opportunities using targeted search queries.
    
    This job:
    1. Rotates through a list of "hunting" queries (e.g., "undervalued microcaps")
    2. Searches for relevant news using SearXNG
    3. Saves articles with article_type="opportunity_discovery"
    """
    job_id = 'opportunity_discovery'
    start_time = time.time()
    target_date = datetime.now(timezone.utc).date()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting opportunity discovery job...")
        
        # Mark job as started in database
        mark_job_started('opportunity_discovery', target_date)
        
        # Import dependencies
        try:
            from searxng_client import get_searxng_client, check_searxng_health
            from research_utils import extract_article_content
            from ollama_client import get_ollama_client
            from research_repository import ResearchRepository
            from settings import get_discovery_search_queries
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Check SearXNG health
        if not check_searxng_health():
            duration_ms = int((time.time() - start_time) * 1000)
            message = "SearXNG is not available - skipping opportunity discovery"
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
        
        # Get discovery queries
        queries = get_discovery_search_queries()
        logger.info(f"Using {len(queries)} discovery queries")
        
        # Rotate through queries (pick one per run to avoid overwhelming the system)
        # Use the current hour to deterministically select which query to use
        from datetime import datetime
        query_index = datetime.now().hour % len(queries)
        selected_query = queries[query_index]
        
        logger.info(f"🔭 Discovery Query: '{selected_query}'")
        
        # Search
        search_results = searxng_client.search_news(
            query=selected_query,
            max_results=8  # Get more results for discovery
        )
        
        if not search_results or not search_results.get('results'):
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"No results for query: {selected_query}"
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
                    continue
                
                # Check blacklist
                from research_utils import is_domain_blacklisted
                is_blocked, domain = is_domain_blacklisted(url, blacklist)
                if is_blocked:
                    logger.debug(f"Skipping blacklisted: {domain}")
                    articles_blacklisted += 1
                    continue
                
                # Check if already exists
                if research_repo.article_exists(url):
                    logger.debug(f"Article already exists: {title[:50]}...")
                    articles_skipped += 1
                    continue
                
                # Extract content
                logger.info(f"  💎 Extracting: {title[:40]}...")
                extracted = extract_article_content(url)
                
                # Health tracking
                from research_domain_health import DomainHealthTracker
                tracker = DomainHealthTracker()
                from settings import get_system_setting
                threshold = get_system_setting("auto_blacklist_threshold", default=4)
                
                content = extracted.get('content', '')
                if not content or not extracted.get('success'):
                    error_reason = extracted.get('error', 'unknown')
                    failure_count = tracker.record_failure(url, error_reason)
                    
                    if tracker.should_auto_blacklist(url):
                        if tracker.auto_blacklist_domain(url):
                            logger.warning(f"🚫 AUTO-BLACKLISTED: {domain}")
                            articles_blacklisted += 1
                    continue
                
                tracker.record_success(url)
                
                # Generate summary and embedding
                summary = None
                summary_data = {}
                extracted_tickers = []
                extracted_sector = None
                embedding = None
                
                if ollama_client:
                    summary_data = ollama_client.generate_summary(content)
                    
                    if isinstance(summary_data, str):
                        summary = summary_data
                    elif isinstance(summary_data, dict) and summary_data:
                        summary = summary_data.get("summary", "")
                        
                        # Extract ticker and sector
                        tickers = summary_data.get("tickers", [])
                        sectors = summary_data.get("sectors", [])
                        
                        # Extract all validated tickers
                        from research_utils import validate_ticker_format, normalize_ticker
                        for ticker in tickers:
                            # Validate format only (trust AI inference for company name -> ticker conversion)
                            if not validate_ticker_format(ticker):
                                logger.warning(f"Rejected invalid ticker format: {ticker} (likely company name or invalid format)")
                                continue
                            normalized = normalize_ticker(ticker)
                            if normalized:
                                extracted_tickers.append(normalized)
                                logger.debug(f"  🎯 Discovered ticker: {normalized}")
                        
                        if extracted_tickers:
                            logger.info(f"  🎯 Discovered {len(extracted_tickers)} validated ticker(s): {extracted_tickers}")
                        
                        if sectors:
                            extracted_sector = sectors[0]
                    
                    # Generate embedding
                    embedding = ollama_client.generate_embedding(content[:6000])
                
                # Calculate relevance score (check if any tickers are owned)
                relevance_score = calculate_relevance_score(extracted_tickers, extracted_sector, owned_tickers=owned_tickers)
                
                # Extract logic_check for relationship confidence scoring
                logic_check = summary_data.get("logic_check") if isinstance(summary_data, dict) else None
                
                # Check if tickers were found - for opportunity discovery, we only want actionable ideas
                if not extracted_tickers:
                    logger.info(f"Skipping opportunity discovery article (no tickers found): {title[:50]}...")
                    articles_skipped += 1
                    continue

                # Save article with opportunity_discovery type
                article_id = research_repo.save_article(
                    tickers=extracted_tickers,
                    sector=extracted_sector,
                    article_type="opportunity_discovery",  # Special tag
                    title=extracted.get('title') or title,
                    url=url,
                    summary=summary,
                    content=content,
                    source=extracted.get('source'),
                    published_at=extracted.get('published_at'),
                    relevance_score=relevance_score,
                    embedding=embedding,
                    claims=summary_data.get("claims") if isinstance(summary_data, dict) else None,
                    fact_check=summary_data.get("fact_check") if isinstance(summary_data, dict) else None,
                    conclusion=summary_data.get("conclusion") if isinstance(summary_data, dict) else None,
                    sentiment=summary_data.get("sentiment") if isinstance(summary_data, dict) else None,
                    sentiment_score=summary_data.get("sentiment_score") if isinstance(summary_data, dict) else None,
                    logic_check=logic_check
                )
                
                if article_id:
                    articles_saved += 1
                    logger.info(f"  ✅ Saved opportunity: {title[:30]}")
                    
                    # Extract and save relationships (GraphRAG edges)
                    if isinstance(summary_data, dict) and logic_check and logic_check != "HYPE_DETECTED":
                        relationships = summary_data.get("relationships", [])
                        if relationships and isinstance(relationships, list):
                            # Calculate initial confidence based on logic_check
                            if logic_check == "DATA_BACKED":
                                initial_confidence = 0.8
                            else:  # NEUTRAL
                                initial_confidence = 0.4
                            
                            # Normalize and save each relationship
                            from research_utils import normalize_relationship
                            relationships_saved = 0
                            for rel in relationships:
                                if isinstance(rel, dict):
                                    source = rel.get("source", "").strip()
                                    target = rel.get("target", "").strip()
                                    rel_type = rel.get("type", "").strip()
                                    
                                    if source and target and rel_type:
                                        # Normalize relationship direction (Option A: Supplier -> Buyer)
                                        norm_source, norm_target, norm_type = normalize_relationship(source, target, rel_type)
                                        
                                        # Save relationship
                                        rel_id = research_repo.save_relationship(
                                            source_ticker=norm_source,
                                            target_ticker=norm_target,
                                            relationship_type=norm_type,
                                            initial_confidence=initial_confidence,
                                            source_article_id=article_id
                                        )
                                        if rel_id:
                                            relationships_saved += 1
                            
                            if relationships_saved > 0:
                                logger.info(f"  ✅ Saved {relationships_saved} relationship(s) from opportunity article: {title[:30]}")
                
                articles_processed += 1
                
                # Delay between articles
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing discovery article: {e}")
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Query: '{selected_query[:50]}...' - Processed {articles_processed}: {articles_saved} saved, {articles_skipped} skipped, {articles_blacklisted} blacklisted"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('opportunity_discovery', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('opportunity_discovery', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
        logger.error(f"❌ Opportunity discovery job failed: {e}", exc_info=True)




def opportunity_discovery_job() -> None:
    """Hunt for new investment opportunities using targeted search queries.
    
    This job:
    1. Rotates through a list of "hunting" queries (e.g., "undervalued microcaps")
    2. Searches for relevant news using SearXNG
    3. Saves articles with article_type="opportunity_discovery"
    """
    job_id = 'opportunity_discovery'
    start_time = time.time()
    
    try:
        logger.info("Starting opportunity discovery job...")
        
        # Import dependencies
        try:
            from searxng_client import get_searxng_client, check_searxng_health
            from research_utils import extract_article_content
            from ollama_client import get_ollama_client
            from research_repository import ResearchRepository
            from settings import get_discovery_search_queries
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Check SearXNG health
        if not check_searxng_health():
            duration_ms = int((time.time() - start_time) * 1000)
            message = "SearXNG is not available - skipping opportunity discovery"
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
        
        # Get discovery queries
        queries = get_discovery_search_queries()
        logger.info(f"Using {len(queries)} discovery queries")
        
        # Rotate through queries (pick one per run to avoid overwhelming the system)
        # Use the current hour to deterministically select which query to use
        from datetime import datetime
        query_index = datetime.now().hour % len(queries)
        selected_query = queries[query_index]
        
        logger.info(f"🔭 Discovery Query: '{selected_query}'")
        
        # Search
        search_results = searxng_client.search_news(
            query=selected_query,
            max_results=8  # Get more results for discovery
        )
        
        if not search_results or not search_results.get('results'):
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"No results for query: {selected_query}"
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
                    continue
                
                # Check blacklist
                from research_utils import is_domain_blacklisted
                is_blocked, domain = is_domain_blacklisted(url, blacklist)
                if is_blocked:
                    logger.debug(f"Skipping blacklisted: {domain}")
                    articles_blacklisted += 1
                    continue
                
                # Check if already exists
                if research_repo.article_exists(url):
                    logger.debug(f"Article already exists: {title[:50]}...")
                    articles_skipped += 1
                    continue
                
                # Extract content
                logger.info(f"  💎 Extracting: {title[:40]}...")
                extracted = extract_article_content(url)
                
                # Health tracking
                from research_domain_health import DomainHealthTracker
                tracker = DomainHealthTracker()
                from settings import get_system_setting
                threshold = get_system_setting("auto_blacklist_threshold", default=4)
                
                content = extracted.get('content', '')
                if not content or not extracted.get('success'):
                    error_reason = extracted.get('error', 'unknown')
                    failure_count = tracker.record_failure(url, error_reason)
                    
                    if tracker.should_auto_blacklist(url):
                        if tracker.auto_blacklist_domain(url):
                            logger.warning(f"🚫 AUTO-BLACKLISTED: {domain}")
                            articles_blacklisted += 1
                    continue
                
                tracker.record_success(url)
                
                # Generate summary and embedding
                summary = None
                summary_data = {}
                extracted_tickers = []
                extracted_sector = None
                embedding = None
                
                if ollama_client:
                    summary_data = ollama_client.generate_summary(content)
                    
                    if isinstance(summary_data, str):
                        summary = summary_data
                    elif isinstance(summary_data, dict) and summary_data:
                        summary = summary_data.get("summary", "")
                        
                        # Extract ticker and sector
                        tickers = summary_data.get("tickers", [])
                        sectors = summary_data.get("sectors", [])
                        
                        # Extract all validated tickers
                        from research_utils import validate_ticker_format, normalize_ticker
                        for ticker in tickers:
                            # Validate format only (trust AI inference)
                            if not validate_ticker_format(ticker):
                                logger.warning(f"Rejected invalid ticker format: {ticker} (likely company name or invalid format)")
                                continue
                            normalized = normalize_ticker(ticker)
                            if normalized:
                                extracted_tickers.append(normalized)
                                logger.debug(f"  🎯 Discovered ticker: {normalized}")
                        
                        if extracted_tickers:
                            logger.info(f"  🎯 Discovered {len(extracted_tickers)} validated ticker(s): {extracted_tickers}")
                        
                        if sectors:
                            extracted_sector = sectors[0]
                    
                    # Generate embedding
                    embedding = ollama_client.generate_embedding(content[:6000])
                
                # Calculate relevance score (check if any tickers are owned)
                relevance_score = calculate_relevance_score(extracted_tickers, extracted_sector, owned_tickers=owned_tickers)
                
                # Extract logic_check for relationship confidence scoring
                logic_check = summary_data.get("logic_check") if isinstance(summary_data, dict) else None
                
                # Save article with opportunity_discovery type
                article_id = research_repo.save_article(
                    tickers=extracted_tickers if extracted_tickers else None,
                    sector=extracted_sector,
                    article_type="opportunity_discovery",  # Special tag
                    title=extracted.get('title') or title,
                    url=url,
                    summary=summary,
                    content=content,
                    source=extracted.get('source'),
                    published_at=extracted.get('published_at'),
                    relevance_score=relevance_score,
                    embedding=embedding,
                    claims=summary_data.get("claims") if isinstance(summary_data, dict) else None,
                    fact_check=summary_data.get("fact_check") if isinstance(summary_data, dict) else None,
                    conclusion=summary_data.get("conclusion") if isinstance(summary_data, dict) else None,
                    sentiment=summary_data.get("sentiment") if isinstance(summary_data, dict) else None,
                    sentiment_score=summary_data.get("sentiment_score") if isinstance(summary_data, dict) else None,
                    logic_check=logic_check
                )
                
                if article_id:
                    articles_saved += 1
                    logger.info(f"  ✅ Saved opportunity: {title[:30]}")
                    
                    # Extract and save relationships (GraphRAG edges)
                    if isinstance(summary_data, dict) and logic_check and logic_check != "HYPE_DETECTED":
                        relationships = summary_data.get("relationships", [])
                        if relationships and isinstance(relationships, list):
                            # Calculate initial confidence based on logic_check
                            if logic_check == "DATA_BACKED":
                                initial_confidence = 0.8
                            else:  # NEUTRAL
                                initial_confidence = 0.4
                            
                            # Normalize and save each relationship
                            from research_utils import normalize_relationship
                            relationships_saved = 0
                            for rel in relationships:
                                if isinstance(rel, dict):
                                    source = rel.get("source", "").strip()
                                    target = rel.get("target", "").strip()
                                    rel_type = rel.get("type", "").strip()
                                    
                                    if source and target and rel_type:
                                        # Normalize relationship direction (Option A: Supplier -> Buyer)
                                        norm_source, norm_target, norm_type = normalize_relationship(source, target, rel_type)
                                        
                                        # Save relationship
                                        rel_id = research_repo.save_relationship(
                                            source_ticker=norm_source,
                                            target_ticker=norm_target,
                                            relationship_type=norm_type,
                                            initial_confidence=initial_confidence,
                                            source_article_id=article_id
                                        )
                                        if rel_id:
                                            relationships_saved += 1
                            
                            if relationships_saved > 0:
                                logger.info(f"  ✅ Saved {relationships_saved} relationship(s) from opportunity article: {title[:30]}")
                
                articles_processed += 1
                
                # Delay between articles
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing discovery article: {e}")
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Query: '{selected_query[:50]}...' - Processed {articles_processed}: {articles_saved} saved, {articles_skipped} skipped, {articles_blacklisted} blacklisted"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('opportunity_discovery', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('opportunity_discovery', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
        logger.error(f"❌ Opportunity discovery job failed: {e}", exc_info=True)





def refresh_exchange_rates_job() -> None:
    """Fetch and store the latest exchange rate.
    
    This ensures the dashboard always has up-to-date rates for currency conversion.
    """
    job_id = 'exchange_rates'
    start_time = time.time()
    target_date = datetime.now(timezone.utc).date()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting exchange rates refresh job...")
        
        # Mark job as started in database
        mark_job_started('exchange_rates', target_date)
        
        # Import here to avoid circular imports
        from exchange_rates_utils import reload_exchange_rate_for_date
        
        # Fetch today's rate
        today = datetime.now(timezone.utc)
        rate = reload_exchange_rate_for_date(today, 'USD', 'CAD')
        
        if rate is not None:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Updated USD/CAD rate: {rate}"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            mark_job_completed('exchange_rates', target_date, None, [], duration_ms=duration_ms)
            logger.info(f"✅ {message}")
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "Failed to fetch exchange rate from API"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            mark_job_failed('exchange_rates', target_date, None, message, duration_ms=duration_ms)
            logger.warning(f"⚠️ {message}")
            
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            from utils.job_tracking import mark_job_failed
            mark_job_failed('exchange_rates', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
        logger.error(f"❌ Exchange rates job failed: {e}")


def populate_performance_metrics_job() -> None:
    """Aggregate daily portfolio performance into performance_metrics table.
    
    This pre-calculates daily metrics to speed up chart queries (90 rows vs 1338 rows).
    Runs yesterday's data to ensure market close prices are final.
    """
    job_id = 'performance_metrics'
    start_time = time.time()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting performance metrics population job...")
        
        # Import here to avoid circular imports
        from supabase_client import SupabaseClient
        from datetime import date
        from decimal import Decimal
        
        # Use service role key to bypass RLS (background job needs full access)
        client = SupabaseClient(use_service_role=True)
        
        # Process yesterday's data (today's data may still be updating)
        yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
        
        # Mark job as started in database
        mark_job_started('performance_metrics', yesterday)
        
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
                    datetime.combine(yesterday, dt_time(0, 0, 0)),
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
        mark_job_completed('performance_metrics', yesterday, None, list(fund_totals.keys()), duration_ms=duration_ms)
        logger.info(f"✅ {message}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            from utils.job_tracking import mark_job_failed
            yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
            mark_job_failed('performance_metrics', yesterday, None, message, duration_ms=duration_ms)
        except Exception:
            pass  # Don't fail if tracking fails
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
            is_before_open = current_time < dt_time(market_open_hour, market_open_minute)
            is_after_close = current_time >= dt_time(market_close_hour, 0)
            
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
                        datetime.combine(target_date, dt_time(0, 0, 0)),
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
                        start_dt = datetime.combine(target_date, dt_time(0, 0, 0))
                        end_dt = datetime.combine(target_date, dt_time(23, 59, 59, 999999))
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
                    # Calculate date_only for unique constraint (fund, ticker, date_only)
                    date_only = utc_datetime.date()
                    
                    updated_positions.append({
                        'fund': fund_name,
                        'ticker': ticker,
                        'shares': float(shares),
                        'price': float(current_price),
                        'cost_basis': float(cost_basis),
                        'pnl': float(unrealized_pnl),
                        'currency': holding['currency'],
                        'date': utc_datetime.isoformat(),
                        'date_only': date_only.isoformat(),  # Include for unique constraint upsert
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
                start_of_day = datetime.combine(target_date, dt_time(0, 0, 0)).isoformat()
                end_of_day = datetime.combine(target_date, dt_time(23, 59, 59, 999999)).isoformat()
                
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
                
                # ATOMIC UPDATE: Upsert updated positions (insert or update on conflict)
                # Using upsert instead of insert to handle race conditions gracefully
                # The unique constraint on (fund, date, ticker) prevents duplicates
                # If delete+insert pattern fails due to race condition, upsert will handle it
                if updated_positions:
                    try:
                        # Use upsert with on_conflict to handle duplicates from race conditions
                        # This is safer than insert alone - if the job runs twice concurrently,
                        # or if delete+insert fails, upsert will update existing records instead of erroring
                        # The unique constraint is on (fund, ticker, date_only) - date_only is auto-populated by trigger
                        upsert_result = client.supabase.table("portfolio_positions")\
                            .upsert(
                                updated_positions,
                                on_conflict="fund,ticker,date_only"
                            )\
                            .execute()
                        
                        upserted_count = len(upsert_result.data) if upsert_result.data else len(updated_positions)
                        total_positions_updated += upserted_count
                        total_funds_processed += 1
                        funds_completed.append(fund_name)  # Track successful completion
                        
                        logger.info(f"  ✅ Upserted {upserted_count} positions for {fund_name}")
                    except Exception as upsert_error:
                        # Upsert failed - log error but don't fail entire job
                        # The delete already happened, but upsert failure is less likely than insert failure
                        # This is acceptable because:
                        # 1. Next run (15 min) will fix it
                        # 2. Historical data is preserved
                        # 3. We continue processing other funds
                        logger.error(f"  ❌ Failed to upsert positions for {fund_name}: {upsert_error}")
                        logger.warning(f"  ⚠️  {fund_name} has no positions for {target_date} until next run")
                        # Don't increment counters for failed upsert
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
        mark_job_completed('update_portfolio_prices', target_date, None, funds_completed, duration_ms=duration_ms)
        
        # Bump cache version to invalidate Streamlit cache immediately
        try:
            import sys
            from pathlib import Path
            web_dashboard_path = str(Path(__file__).resolve().parent.parent)
            if web_dashboard_path not in sys.path:
                sys.path.insert(0, web_dashboard_path)
            from cache_version import bump_cache_version
            bump_cache_version()
            logger.info("Cache version bumped - Streamlit will show fresh data")
        except Exception as e:
            logger.warning(f"Failed to bump cache version: {e}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Portfolio price update job failed: {e}", exc_info=True)
        
        # Mark job as failed in database
        # If target_date not defined (early crash), use today as fallback
        fallback_date = date.today() if 'target_date' not in locals() else target_date
        mark_job_failed('update_portfolio_prices', fallback_date, None, str(e), duration_ms=duration_ms)
    finally:
        # Always release the lock, even if job fails
        _update_prices_lock.release()


def backfill_portfolio_prices_range(start_date: date, end_date: date) -> None:
    """Backfill portfolio positions for a date range efficiently.
    
    This is a batch-optimized version of update_portfolio_prices_job that:
    1. Fetches price data for ALL tickers for the ENTIRE date range at once (1 API call per ticker)
    2. Correctly filters trades by date for each historical snapshot
    3. Processes all dates in the range with a single batch delete/insert
    
    Args:
        start_date: First date to backfill (inclusive)
        end_date: Last date to backfill (inclusive)
    
    Performance: O(Tickers) API calls instead of O(Days * Tickers)
    Correctness: Only includes trades up to each snapshot date
    """
    job_id = 'backfill_portfolio_prices_range'
    start_time = time.time()
    
    try:
        # CRITICAL: Add project root to path FIRST
        import sys
        from pathlib import Path
        
        project_root = Path(__file__).resolve().parent.parent.parent
        project_root_str = str(project_root)
        
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)
        
        web_dashboard_path = str(Path(__file__).resolve().parent.parent)
        if web_dashboard_path not in sys.path:
            sys.path.insert(0, web_dashboard_path)
        
        logger.info(f"Starting batch backfill for date range: {start_date} to {end_date}")
        
        # Import dependencies
        from market_data.data_fetcher import MarketDataFetcher
        from utils.market_holidays import MarketHolidays
        from supabase_client import SupabaseClient
        from exchange_rates_utils import get_exchange_rate_for_date_from_db
        import pytz
        
        # Initialize components
        market_fetcher = MarketDataFetcher()
        market_holidays = MarketHolidays()
        client = SupabaseClient(use_service_role=True)
        
        # Get all production funds
        funds_result = client.supabase.table("funds")\
            .select("name, base_currency")\
            .eq("is_production", True)\
            .execute()
            
        if not funds_result.data:
            logger.info("No production funds found")
            return
        
        funds = [(f['name'], f.get('base_currency', 'CAD')) for f in funds_result.data]
        logger.info(f"Processing {len(funds)} production funds")
        
        # Build list of trading days in the range
        trading_days = []
        current = start_date
        while current <= end_date:
            if market_holidays.is_trading_day(current, market="any"):
                trading_days.append(current)
            current += timedelta(days=1)
        
        if not trading_days:
            logger.info(f"No trading days in range {start_date} to {end_date}")
            return
        
        logger.info(f"Backfilling {len(trading_days)} trading days: {trading_days[0]} to {trading_days[-1]}")
        
        total_positions_created = 0
        
        for fund_name, base_currency in funds:
            try:
                logger.info(f"Processing fund: {fund_name} (base_currency: {base_currency})")
                
                # Get ALL trades for this fund (we'll filter by date later)
                trades_result = client.supabase.table("trade_log")\
                    .select("*")\
                    .eq("fund", fund_name)\
                    .order("date")\
                    .execute()
                
                if not trades_result.data:
                    logger.info(f"  No trades found for {fund_name}")
                    continue
                
                # Convert trade dates to date objects for comparison
                trades_with_dates = []
                for trade in trades_result.data:
                    trade_date_str = trade.get('date')
                    if trade_date_str:
                        # Parse the date - handle both date and datetime formats
                        try:
                            if 'T' in trade_date_str:
                                trade_date = datetime.fromisoformat(trade_date_str.replace('Z', '+00:00')).date()
                            else:
                                trade_date = datetime.strptime(trade_date_str, '%Y-%m-%d').date()
                            trades_with_dates.append({**trade, '_parsed_date': trade_date})
                        except Exception as e:
                            logger.warning(f"  Could not parse trade date {trade_date_str}: {e}")
                            continue
                
                if not trades_with_dates:
                    logger.info(f"  No valid trades with parseable dates for {fund_name}")
                    continue
                
                # Identify all unique tickers across ALL trades
                all_tickers = set()
                for trade in trades_with_dates:
                    all_tickers.add(trade['ticker'])
                
                logger.info(f"  Found {len(all_tickers)} unique tickers across all trades")
                
                # OPTIMIZATION: Fetch price data for ALL tickers for the ENTIRE date range at once
                # This is 1 API call per ticker instead of 1 API call per ticker per day
                ticker_price_data = {}
                failed_tickers = []
                
                logger.info(f"  Fetching price data for {len(all_tickers)} tickers (batch mode)...")
                fetch_start = time.time()
                
                for ticker in all_tickers:
                    try:
                        # Fetch data for entire range with some padding
                        range_start = datetime.combine(trading_days[0], dt_time(0, 0, 0))
                        range_end = datetime.combine(trading_days[-1], dt_time(23, 59, 59, 999999))
                        
                        result = market_fetcher.fetch_price_data(ticker, start=range_start, end=range_end)
                        
                        if result and result.df is not None and not result.df.empty:
                            # Store the entire DataFrame - we'll lookup specific dates later
                            ticker_price_data[ticker] = result.df
                            logger.debug(f"    {ticker}: Fetched {len(result.df)} price records")
                        else:
                            failed_tickers.append(ticker)
                            logger.warning(f"    {ticker}: No price data available")
                    except Exception as e:
                        failed_tickers.append(ticker)
                        logger.warning(f"    {ticker}: Error fetching price data: {e}")
                
                fetch_duration = time.time() - fetch_start
                logger.info(f"  Batch fetch complete: {len(ticker_price_data)}/{len(all_tickers)} succeeded in {fetch_duration:.2f}s")
                
                if failed_tickers:
                    logger.warning(f"  Failed to fetch prices for {len(failed_tickers)} tickers: {failed_tickers}")
                
                # Now process each trading day
                all_positions = []  # Collect all position records for batch insert
                
                for target_date in trading_days:
                    # CORRECTNESS FIX: Filter trades to only those on or before target_date
                    trades_up_to_date = [t for t in trades_with_dates if t['_parsed_date'] <= target_date]
                    
                    # Build running positions from filtered trades
                    running_positions = defaultdict(lambda: {
                        'shares': Decimal('0'),
                        'cost': Decimal('0'),
                        'currency': 'USD'
                    })
                    
                    for trade in trades_up_to_date:
                        ticker = trade['ticker']
                        shares = Decimal(str(trade.get('shares', 0) or 0))
                        price = Decimal(str(trade.get('price', 0) or 0))
                        cost = shares * price
                        reason = str(trade.get('reason', '')).upper()
                        
                        if 'SELL' in reason:
                            if running_positions[ticker]['shares'] > 0:
                                cost_per_share = running_positions[ticker]['cost'] / running_positions[ticker]['shares']
                                running_positions[ticker]['shares'] -= shares
                                running_positions[ticker]['cost'] -= shares * cost_per_share
                                if running_positions[ticker]['shares'] < 0:
                                    running_positions[ticker]['shares'] = Decimal('0')
                                if running_positions[ticker]['cost'] < 0:
                                    running_positions[ticker]['cost'] = Decimal('0')
                        else:
                            running_positions[ticker]['shares'] += shares
                            running_positions[ticker]['cost'] += cost
                            currency = trade.get('currency', 'USD')
                            if currency and isinstance(currency, str):
                                currency_upper = currency.strip().upper()
                                if currency_upper and currency_upper not in ('NAN', 'NONE', 'NULL', ''):
                                    running_positions[ticker]['currency'] = currency_upper
                    
                    # Filter to only positions with shares > 0
                    current_holdings = {
                        ticker: pos for ticker, pos in running_positions.items()
                        if pos['shares'] > 0
                    }
                    
                    if not current_holdings:
                        logger.debug(f"  {target_date}: No active positions")
                        continue
                    
                    # Get exchange rate for this date
                    exchange_rate = Decimal('1.0')
                    if base_currency != 'USD':
                        rate = get_exchange_rate_for_date_from_db(
                            datetime.combine(target_date, dt_time(0, 0, 0)),
                            'USD',
                            base_currency
                        )
                        if rate is not None:
                            exchange_rate = Decimal(str(rate))
                        else:
                            exchange_rate = Decimal('1.35')  # Fallback
                    
                    # Create position records for this date
                    et_tz = pytz.timezone('America/New_York')
                    et_datetime = et_tz.localize(datetime.combine(target_date, dt_time(16, 0)))
                    utc_datetime = et_datetime.astimezone(pytz.UTC)
                    
                    for ticker, holding in current_holdings.items():
                        if ticker in failed_tickers:
                            continue  # Skip tickers with no price data
                        
                        # Lookup price for this specific date
                        price_df = ticker_price_data.get(ticker)
                        if price_df is None:
                            continue
                        
                        # Find price for target_date
                        try:
                            # Normalize target_date to match DataFrame index
                            target_ts = pd.Timestamp(target_date)
                            
                            # Try exact match first
                            if target_ts in price_df.index:
                                current_price = Decimal(str(price_df.loc[target_ts, 'Close']))
                            else:
                                # Find nearest date (forward fill - use last known price)
                                valid_dates = price_df.index[price_df.index <= target_ts]
                                if len(valid_dates) == 0:
                                    logger.debug(f"  {target_date} {ticker}: No price data for this date")
                                    continue
                                nearest_date = valid_dates[-1]
                                current_price = Decimal(str(price_df.loc[nearest_date, 'Close']))
                        except Exception as e:
                            logger.debug(f"  {target_date} {ticker}: Error looking up price: {e}")
                            continue
                        
                        shares = holding['shares']
                        cost_basis = holding['cost']
                        market_value = shares * current_price
                        unrealized_pnl = market_value - cost_basis
                        
                        # Convert to base currency
                        position_currency = holding['currency']
                        if position_currency == 'USD' and base_currency != 'USD':
                            market_value_base = market_value * exchange_rate
                            cost_basis_base = cost_basis * exchange_rate
                            pnl_base = unrealized_pnl * exchange_rate
                            conversion_rate = exchange_rate
                        elif position_currency == base_currency:
                            market_value_base = market_value
                            cost_basis_base = cost_basis
                            pnl_base = unrealized_pnl
                            conversion_rate = Decimal('1.0')
                        else:
                            market_value_base = market_value
                            cost_basis_base = cost_basis
                            pnl_base = unrealized_pnl
                            conversion_rate = Decimal('1.0')
                        
                        all_positions.append({
                            'fund': fund_name,
                            'ticker': ticker,
                            'shares': float(shares),
                            'price': float(current_price),
                            'cost_basis': float(cost_basis),
                            'pnl': float(unrealized_pnl),
                            'currency': holding['currency'],
                            'date': utc_datetime.isoformat(),
                            'base_currency': base_currency,
                            'total_value_base': float(market_value_base),
                            'cost_basis_base': float(cost_basis_base),
                            'pnl_base': float(pnl_base),
                            'exchange_rate': float(conversion_rate)
                        })
                
                if not all_positions:
                    logger.info(f"  No positions to backfill for {fund_name}")
                    continue
                
                logger.info(f"  Created {len(all_positions)} position records across {len(trading_days)} days")
                
                # BATCH DELETE: Remove all existing positions for this fund in the date range
                start_of_range = datetime.combine(trading_days[0], dt_time(0, 0, 0)).isoformat()
                end_of_range = datetime.combine(trading_days[-1], dt_time(23, 59, 59, 999999)).isoformat()
                
                deleted_total = 0
                while True:
                    existing_result = client.supabase.table("portfolio_positions")\
                        .select("id")\
                        .eq("fund", fund_name)\
                        .gte("date", start_of_range)\
                        .lte("date", end_of_range)\
                        .limit(1000)\
                        .execute()
                    
                    if not existing_result.data:
                        break
                    
                    ids_to_delete = [row['id'] for row in existing_result.data]
                    delete_result = client.supabase.table("portfolio_positions")\
                        .delete()\
                        .in_("id", ids_to_delete)\
                        .execute()
                    
                    deleted_count = len(delete_result.data) if delete_result.data else len(ids_to_delete)
                    deleted_total += deleted_count
                    
                    if len(existing_result.data) < 1000:
                        break
                
                if deleted_total > 0:
                    logger.info(f"  Deleted {deleted_total} existing positions")
                
                # BATCH INSERT: Insert all positions at once
                try:
                    insert_result = client.supabase.table("portfolio_positions")\
                        .insert(all_positions)\
                        .execute()
                    
                    inserted_count = len(insert_result.data) if insert_result.data else len(all_positions)
                    total_positions_created += inserted_count
                    
                    logger.info(f"  ✅ Inserted {inserted_count} positions for {fund_name}")
                except Exception as insert_error:
                    logger.error(f"  ❌ Failed to insert positions for {fund_name}: {insert_error}")
                
            except Exception as e:
                logger.error(f"  ❌ Error processing fund {fund_name}: {e}", exc_info=True)
                continue
        
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Backfilled {total_positions_created} positions for date range {start_date} to {end_date}"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        logger.info(f"✅ {message} in {duration_ms/1000:.2f}s")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Batch backfill failed: {e}", exc_info=True)


def fetch_social_sentiment_job() -> None:
    """Fetch social sentiment data from StockTwits and Reddit for watched tickers.
    
    This job:
    1. Fetches tickers from both watched_tickers (Supabase) and latest_positions (Supabase)
    2. Combines and deduplicates the ticker lists
    3. For each ticker, fetches sentiment from StockTwits and Reddit
    4. Saves metrics to the social_metrics table (Postgres)
    """
    job_id = 'social_sentiment'
    start_time = time.time()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting social sentiment job...")
        
        # Mark job as started
        target_date = datetime.now(timezone.utc).date()
        mark_job_started('social_sentiment', target_date)
        
        # Import dependencies (lazy imports)
        try:
            from social_service import SocialSentimentService
            from supabase_client import SupabaseClient
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Initialize service
        service = SocialSentimentService()
        supabase_client = SupabaseClient(use_service_role=True)
        
        # Check FlareSolverr availability
        try:
            import requests
            flaresolverr_url = os.getenv("FLARESOLVERR_URL", "http://host.docker.internal:8191")
            requests.get(f"{flaresolverr_url}/health", timeout=5)
            logger.info("✅ FlareSolverr is available")
        except Exception:
            logger.warning("⚠️  FlareSolverr unavailable - will fallback to direct requests")
        
        # Check Ollama availability
        if not service.ollama:
            logger.warning("⚠️  Ollama unavailable - Reddit sentiment will be NEUTRAL only")
        
        # 1. Get tickers from watched_tickers table
        watched_tickers = service.get_watched_tickers()
        logger.info(f"Found {len(watched_tickers)} watched tickers")
        
        # 2. Get tickers from latest_positions (owned positions)
        try:
            positions_result = supabase_client.supabase.table("latest_positions")\
                .select("ticker")\
                .execute()
            
            owned_tickers = list(set([row['ticker'] for row in positions_result.data if row.get('ticker')]))
            logger.info(f"Found {len(owned_tickers)} tickers from latest positions")
        except Exception as e:
            logger.warning(f"Failed to fetch tickers from latest_positions: {e}")
            owned_tickers = []
        
        # 3. Combine and deduplicate
        all_tickers = list(set(watched_tickers + owned_tickers))
        logger.info(f"Processing {len(all_tickers)} unique tickers for social sentiment")
        
        if not all_tickers:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "No tickers to process"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            mark_job_completed('social_sentiment', target_date, None, [], duration_ms=duration_ms)
            logger.info(f"ℹ️ {message}")
            return
        
        # 4. Process each ticker
        success_count = 0
        error_count = 0
        failed_tickers = []
        
        for ticker in all_tickers:
            try:
                # Fetch StockTwits sentiment
                stocktwits_data = service.fetch_stocktwits_sentiment(ticker)
                if stocktwits_data:
                    service.save_metrics(
                        ticker=ticker,
                        platform='stocktwits',
                        metrics=stocktwits_data  # Pass the entire dict
                    )
                    logger.debug(f"✅ Saved StockTwits data for {ticker}")
                
                # Fetch Reddit sentiment
                reddit_data = service.fetch_reddit_sentiment(ticker)
                if reddit_data:
                    service.save_metrics(
                        ticker=ticker,
                        platform='reddit',
                        metrics=reddit_data  # Pass the entire dict
                    )
                    logger.debug(f"✅ Saved Reddit data for {ticker}")
                
                success_count += 1
                
            except Exception as e:
                error_count += 1
                failed_tickers.append(ticker)
                logger.warning(f"Failed to process {ticker}: {e}")
                continue
        
        # 5. Log completion
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Processed {len(all_tickers)} tickers: {success_count} successful, {error_count} errors"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('social_sentiment', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ Social sentiment job completed: {message} in {duration_ms/1000:.2f}s")
        
        # Log failed tickers if any
        if failed_tickers:
            logger.warning(f"Failed tickers ({len(failed_tickers)}): {', '.join(failed_tickers)}")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        mark_job_failed('social_sentiment', target_date, None, str(e), duration_ms=duration_ms)
        logger.error(f"❌ Social sentiment job failed: {e}", exc_info=True)


def cleanup_social_metrics_job() -> None:
    """Daily cleanup job for social metrics retention policy.
    
    Implements two-tier retention:
    - Removes raw_data JSON from records older than 7 days
    - Deletes entire rows older than 90 days
    """
    job_id = 'social_metrics_cleanup'
    start_time = time.time()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting social metrics cleanup job...")
        
        # Mark job as started
        target_date = datetime.now(timezone.utc).date()
        mark_job_started('social_metrics_cleanup', target_date)
        
        # Import dependencies (lazy imports)
        try:
            from social_service import SocialSentimentService
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Initialize service
        service = SocialSentimentService()
        
        # Run cleanup
        results = service.run_daily_cleanup()
        
        # Log completion
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Updated {results['rows_updated']} records, deleted {results['rows_deleted']} records"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('social_metrics_cleanup', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ Social metrics cleanup job completed: {message} in {duration_ms/1000:.2f}s")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        mark_job_failed('social_metrics_cleanup', target_date, None, str(e), duration_ms=duration_ms)
        logger.error(f"❌ Social metrics cleanup job failed: {e}", exc_info=True)


def social_sentiment_ai_job() -> None:
    """AI analysis job for social sentiment data.

    This job:
    1. Extracts posts from raw_data into structured social_posts table
    2. Creates sentiment analysis sessions by grouping related posts
    3. Performs AI analysis on sessions using Ollama Granite model
    4. Stores detailed analysis results in research database
    """
    job_id = 'social_sentiment_ai'
    start_time = time.time()

    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed

        logger.info("🤖 Starting Social Sentiment AI Analysis job...")

        # Mark job as started
        target_date = datetime.now(timezone.utc).date()
        mark_job_started('social_sentiment_ai', target_date)

        # Import dependencies (lazy imports)
        try:
            from social_service import SocialSentimentService
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return

        # Initialize service
        service = SocialSentimentService()

        # Check Ollama availability
        if not service.ollama:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "Ollama client unavailable - cannot perform AI analysis"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return

        # Step 1: Extract posts from raw_data
        logger.info("📝 Step 1: Extracting posts from raw_data...")
        extraction_result = service.extract_posts_from_raw_data()

        # Step 2: Create sentiment sessions
        logger.info("🎯 Step 2: Creating sentiment analysis sessions...")
        session_result = service.create_sentiment_sessions()

        # Step 3: Perform AI analysis on pending sessions
        logger.info("🧠 Step 3: Performing AI analysis...")
        analyses_completed = 0

        # Get sessions that need analysis (limit to avoid timeouts)
        from postgres_client import PostgresClient
        pc = PostgresClient()
        pending_sessions = pc.execute_query("""
            SELECT id, ticker, platform FROM sentiment_sessions
            WHERE needs_ai_analysis = TRUE
            ORDER BY created_at ASC
            LIMIT 10  -- Process in batches to avoid timeouts
        """)

        for session in pending_sessions:
            session_id = session['id']
            ticker = session['ticker']
            platform = session['platform']

            logger.info(f"Analyzing session {session_id} for {ticker} ({platform})...")
            result = service.analyze_sentiment_session(session_id)

            if result:
                analyses_completed += 1
                logger.info(f"✅ Completed AI analysis for {ticker}")
            else:
                logger.warning(f"❌ Failed AI analysis for session {session_id}")

        # Log completion
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Extracted {extraction_result['posts_created']} posts, created {session_result['sessions_created']} sessions, completed {analyses_completed} AI analyses"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('social_sentiment_ai', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ Social Sentiment AI Analysis job completed: {message} in {duration_ms/1000:.2f}s")

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        mark_job_failed('social_sentiment_ai', target_date, None, str(e), duration_ms=duration_ms)
        logger.error(f"❌ Social Sentiment AI Analysis job failed: {e}", exc_info=True)


def fetch_congress_trades_job() -> None:
    """Fetch and analyze congressional stock trades from Financial Modeling Prep API.
    
    This job:
    1. Fetches House and Senate trading disclosures from FMP API
    2. Processes up to 10 records per chamber per run (API docs claim 0-25 but actual limit is 10)
    3. Cleans and normalizes the data
    4. Checks for duplicates before processing
    5. Analyzes each new trade with AI (Ollama Granite 3.3) for conflict of interest
    6. Saves trades to Supabase congress_trades table
    
    Note: FMP API documentation lies - they claim limit can be 0-25, but only 10 actually works.
    """
    import os
    import requests
    import json
    import re
    
    job_id = 'congress_trades'
    start_time = time.time()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting congress trades job...")
        
        # Mark job as started
        target_date = datetime.now(timezone.utc).date()
        mark_job_started('congress_trades', target_date)
        
        # Import dependencies (lazy imports)
        try:
            from supabase_client import SupabaseClient
            from ollama_client import get_ollama_client
            from utils.politician_mapping import lookup_politician_metadata, resolve_politician_name
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Get FMP API key
        fmp_api_key = os.getenv("FMP_API_KEY")
        if not fmp_api_key:
            duration_ms = int((time.time() - start_time) * 1000)
            message = "FMP_API_KEY not found in environment"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            return
        
        # Initialize clients
        supabase_client = SupabaseClient(use_service_role=True)
        ollama_client = get_ollama_client()
        
        if not ollama_client:
            logger.warning("⚠️  Ollama unavailable - trades will be saved without conflict analysis")
        
        # Calculate cutoff date (7 days ago)
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        
        # Base URL for FMP API (use /stable endpoints, not v3/v4 which are legacy)
        base_url = "https://financialmodelingprep.com/stable"
        
        # Track statistics
        total_trades_found = 0
        new_trades = 0
        skipped_duplicates = 0
        skipped_no_ticker = 0
        ai_analyzed = 0
        errors = 0
        
        # Process both House and Senate
        for chamber in ['House', 'Senate']:
            logger.info(f"Fetching {chamber} trades...")
            
            # Use stable API endpoints
            if chamber == 'House':
                endpoint = f"{base_url}/house-latest"
            else:  # Senate
                endpoint = f"{base_url}/senate-latest"
            
            # Note: FMP API is locked to page 0 only
            # API docs claim limit can be 0-25, but they're liars - only 10 actually works (as of 2025-12-27)
            page = 0
            limit = 10  # Actual API limit: 10 responses per call (docs falsely claim 0-25)
            
            try:
                # Fetch page 0 only (other pages are locked)
                params = {
                    'page': page,
                    'limit': limit,
                    'apikey': fmp_api_key
                }
                
                logger.info(f"Fetching {chamber} page {page} (limit {limit} records)...")
                response = requests.get(endpoint, params=params, timeout=30)
                response.raise_for_status()
                
                # Parse JSON response
                try:
                    data = response.json()
                    # Response is a list of trades
                    trades = data if isinstance(data, list) else []
                except json.JSONDecodeError as json_error:
                    logger.error(f"Failed to parse {chamber} response as JSON: {json_error}")
                    logger.debug(f"Response content: {response.text[:500]}")
                    continue  # Skip this chamber, try next
                
                if not trades:
                    logger.info(f"No trades found for {chamber}")
                    continue  # Skip this chamber, try next
                
                logger.info(f"Found {len(trades)} trades for {chamber}")
                
                # Process each trade
                for trade_data in trades:
                        total_trades_found += 1
                        
                        try:
                            # Extract and clean data
                            # FMP API uses 'symbol' for ticker
                            ticker = trade_data.get('symbol') or trade_data.get('ticker') or ''
                            if not ticker or ticker.strip() == '':
                                skipped_no_ticker += 1
                                continue
                            
                            ticker = ticker.strip().upper()
                            
                            # Get politician name (FMP uses firstName and lastName)
                            first_name = trade_data.get('firstName') or trade_data.get('first_name') or ''
                            last_name = trade_data.get('lastName') or trade_data.get('last_name') or ''
                            politician = f"{first_name} {last_name}".strip()
                            
                            # Fallback to other fields if firstName/lastName not available
                            if not politician:
                                politician = trade_data.get('politician') or trade_data.get('name') or ''
                            
                            if not politician:
                                logger.warning(f"Missing politician name for trade: {trade_data}")
                                continue
                            
                            politician = politician.strip()
                            
                            # Look up politician in database for canonical name + metadata
                            politician_meta = lookup_politician_metadata(supabase_client, politician)
                            politician_id = None
                            
                            if politician_meta:
                                # Use canonical name and metadata from database
                                politician = politician_meta['name']
                                politician_id = politician_meta['politician_id']
                                party = politician_meta['party']
                                state = politician_meta['state']
                                # Override chamber if DB has it
                                if politician_meta['chamber']:
                                    chamber = politician_meta['chamber']
                            else:
                                # Politician not in database - resolve name but mark for manual review
                                canonical_name, _ = resolve_politician_name(politician)
                                politician = canonical_name
                                party = None
                                state = None
                                logger.warning(f"Politician not in database: {politician}")
                            
                            # Parse dates (FMP uses disclosureDate and transactionDate)
                            disclosure_date_str = trade_data.get('disclosureDate') or trade_data.get('disclosure_date') or trade_data.get('date')
                            transaction_date_str = trade_data.get('transactionDate') or trade_data.get('transaction_date') or trade_data.get('trade_date')
                            
                            if not disclosure_date_str:
                                logger.warning(f"Missing disclosure date for trade: {trade_data}")
                                continue
                            
                            try:
                                # Parse dates (FMP may return in various formats)
                                # Try common date formats
                                date_formats = [
                                    '%Y-%m-%d',
                                    '%Y-%m-%dT%H:%M:%S',
                                    '%Y-%m-%dT%H:%M:%SZ',
                                    '%m/%d/%Y',
                                    '%d/%m/%Y',
                                    '%Y/%m/%d'
                                ]
                                
                                disclosure_date = None
                                for fmt in date_formats:
                                    try:
                                        disclosure_date = datetime.strptime(disclosure_date_str.split('T')[0], fmt).date()
                                        break
                                    except (ValueError, AttributeError):
                                        continue
                                
                                if not disclosure_date:
                                    # Try ISO format
                                    try:
                                        disclosure_date = datetime.fromisoformat(disclosure_date_str.replace('Z', '+00:00')).date()
                                    except (ValueError, AttributeError):
                                        logger.warning(f"Failed to parse disclosure date: {disclosure_date_str}")
                                        continue
                                
                                if transaction_date_str:
                                    transaction_date = None
                                    for fmt in date_formats:
                                        try:
                                            transaction_date = datetime.strptime(transaction_date_str.split('T')[0], fmt).date()
                                            break
                                        except (ValueError, AttributeError):
                                            continue
                                    
                                    if not transaction_date:
                                        try:
                                            transaction_date = datetime.fromisoformat(transaction_date_str.replace('Z', '+00:00')).date()
                                        except (ValueError, AttributeError):
                                            transaction_date = disclosure_date  # Fallback to disclosure date
                                else:
                                    transaction_date = disclosure_date  # Fallback to disclosure date
                            except Exception as date_error:
                                logger.warning(f"Failed to parse dates: {date_error}, data: {trade_data}")
                                continue
                            
                            # Check if disclosure date is too old
                            # Note: Since we only get 10 records per chamber, we'll process all of them
                            # and let the 7-day cutoff be handled by the duplicate check
                            if disclosure_date < cutoff_date.date():
                                # Skip old trades (older than 7 days)
                                # But continue processing other trades since we only get 10 total per chamber
                                continue
                            
                            # Get transaction type (FMP may use 'type' or 'transactionType')
                            trade_type = trade_data.get('type') or trade_data.get('transactionType') or trade_data.get('transaction_type') or ''
                            if not trade_type:
                                # Try to infer from other fields
                                description = str(trade_data.get('description', '') or trade_data.get('transaction', '') or '').lower()
                                if 'purchase' in description or 'buy' in description:
                                    trade_type = 'Purchase'
                                elif 'sale' in description or 'sell' in description:
                                    trade_type = 'Sale'
                                else:
                                    trade_type = 'Purchase'  # Default
                            
                            # Normalize to Purchase or Sale
                            trade_type_lower = trade_type.lower()
                            if 'purchase' in trade_type_lower or 'buy' in trade_type_lower:
                                trade_type = 'Purchase'
                            else:
                                trade_type = 'Sale'
                            
                            # Get amount (keep as string - FMP may use 'amount' or 'value')
                            amount = trade_data.get('amount') or trade_data.get('value') or trade_data.get('range') or ''
                            if amount:
                                amount = str(amount).strip()
                            
                            # Get asset type (default to Stock)
                            asset_type = trade_data.get('assetType') or trade_data.get('asset_type') or 'Stock'
                            asset_type_lower = str(asset_type).lower()
                            if 'crypto' in asset_type_lower:
                                asset_type = 'Crypto'
                            else:
                                asset_type = 'Stock'
                            
                            # Extract additional fields if available
                            price_per_share = trade_data.get('pricePerShare') or trade_data.get('price_per_share') or trade_data.get('price')
                            
                            # Extract office field (may contain party/state as fallback)
                            office = trade_data.get('office') or ''
                            
                            # party and state already set from politician lookup above
                            # Only extract from office field if not found in database
                            if not party and not state:
                                if office:
                                    # Look for patterns like (D-CA), (R-TX), (I-VT)
                                    import re
                                    match = re.search(r'\(([DIR])-([A-Z]{2})\)', office)
                                    if match:
                                        party_code = match.group(1)
                                        state = match.group(2)
                                        if party_code == 'D':
                                            party = 'Democratic'
                                        elif party_code == 'R':
                                            party = 'Republican'
                                        elif party_code == 'I':
                                            party = 'Independent'
                            
                            # Extract owner (Self/Spouse/Dependent)
                            owner = trade_data.get('owner') or trade_data.get('assetOwner') or trade_data.get('ownerType')
                            if owner:
                                owner = str(owner).strip().title()
                            else:
                                owner = 'Not-Disclosed'
                            
                            # Extract disclosure link
                            disclosure_link = trade_data.get('link') or trade_data.get('disclosureUrl') or trade_data.get('url')
                            
                            # Extract capital gains flag
                            capital_gains = trade_data.get('capitalGains') or trade_data.get('capital_gains')
                            
                            # Extract any notes/description fields
                            notes = None
                            for field in ['description', 'comment', 'notes', 'memo']:
                                if field in trade_data and trade_data[field]:
                                    notes = str(trade_data[field]).strip()
                                    break
                            
                            # Build notes from available info
                            notes_parts = []
                            if notes:
                                notes_parts.append(notes)
                            if capital_gains:
                                notes_parts.append(f"Capital Gains: {capital_gains}")
                            if disclosure_link:
                                notes_parts.append(f"Disclosure: {disclosure_link}")
                            
                            final_notes = " | ".join(notes_parts) if notes_parts else None
                            
                            # Check for duplicate before processing
                            # Note: We use upsert with on_conflict, so duplicate check is optional
                            # Skip duplicate check if amount has special characters that cause URL encoding issues
                            try:
                                # Only check if amount is simple (no special chars that cause encoding issues)
                                if amount and politician_id and not any(char in amount for char in ['$', ',', '-', ' ']):
                                    existing = supabase_client.supabase.table("congress_trades")\
                                        .select("id")\
                                        .eq("politician_id", politician_id)\
                                        .eq("ticker", ticker)\
                                        .eq("transaction_date", transaction_date.isoformat())\
                                        .eq("amount", amount)\
                                        .maybe_single()\
                                        .execute()
                                    
                                    if existing and existing.data:
                                        skipped_duplicates += 1
                                        continue
                            except Exception as dup_check_error:
                                # Skip duplicate check if it fails - upsert will handle duplicates anyway
                                logger.debug(f"Duplicate check skipped (will use upsert): {dup_check_error}")
                                pass
                            
                            # This is a new trade - analyze with AI
                            conflict_score = None
                            notes = None
                            
                            if ollama_client:
                                try:
                                    # Build prompt for AI analysis
                                    prompt = f"Analyze this trade: {politician} {'bought' if trade_type == 'Purchase' else 'sold'} {ticker} on {transaction_date}. Asset: {asset_type}. Amount: {amount}. Is this suspicious given current events? Return JSON: {{'conflict_score': 0.0-1.0, 'reasoning': '...'}}"
                                    
                                    # Query Ollama (non-streaming for structured response)
                                    full_response = ""
                                    for chunk in ollama_client.query_ollama(
                                        prompt=prompt,
                                        model="granite3.3",
                                        stream=True,
                                        temperature=0.3  # Lower temperature for more consistent analysis
                                    ):
                                        full_response += chunk
                                    
                                    # Parse JSON response
                                    json_match = re.search(r'\{[^{}]*"conflict_score"[^{}]*\}', full_response, re.DOTALL)
                                    if json_match:
                                        json_str = json_match.group(0)
                                    else:
                                        json_str = full_response.strip()
                                    
                                    # Remove markdown code blocks if present
                                    json_str = re.sub(r'```json\s*', '', json_str)
                                    json_str = re.sub(r'```\s*', '', json_str)
                                    json_str = json_str.strip()
                                    
                                    parsed = json.loads(json_str)
                                    
                                    conflict_score = float(parsed.get("conflict_score", 0.0))
                                    # Clamp to 0.0-1.0 range
                                    conflict_score = max(0.0, min(1.0, conflict_score))
                                    notes = parsed.get("reasoning", "AI analysis completed")
                                    
                                    ai_analyzed += 1
                                    
                                except json.JSONDecodeError as e:
                                    logger.warning(f"Failed to parse AI response for {politician} {ticker}: {e}")
                                    logger.debug(f"Response was: {full_response[:500]}")
                                    conflict_score = None
                                    notes = "Failed to parse AI response"
                                except Exception as ai_error:
                                    logger.warning(f"AI analysis failed for {politician} {ticker}: {ai_error}")
                                    conflict_score = None
                                    notes = "AI analysis error"
                            
                            # Prepare trade record with ALL available fields
                            trade_record = {
                                'ticker': ticker,
                                'politician_id': politician_id,  # FK to politicians table
                                'chamber': chamber,
                                'party': party,  # From politicians table lookup
                                'state': state,  # From politicians table lookup
                                'owner': owner,  # Self/Spouse/Dependent if available
                                'transaction_date': transaction_date.isoformat(),
                                'disclosure_date': disclosure_date.isoformat(),
                                'type': trade_type,
                                'amount': amount,
                                'price': price_per_share,  # Price per share if available
                                'asset_type': asset_type,
                                'conflict_score': conflict_score,
                                'notes': final_notes  # Includes description, capital gains, disclosure link
                            }
                            
                            # Insert to Supabase (use upsert to handle any race conditions)
                            try:
                                result = supabase_client.supabase.table("congress_trades")\
                                    .upsert(
                                        trade_record,
                                        on_conflict="politician_id,ticker,transaction_date,amount,type,owner"
                                    )\
                                    .execute()
                                
                                if result.data:
                                    new_trades += 1
                                    logger.debug(f"✅ Saved trade: {politician} {trade_type} {ticker} on {transaction_date}")
                                else:
                                    skipped_duplicates += 1
                                    
                            except Exception as insert_error:
                                errors += 1
                                logger.error(f"Failed to insert trade for {politician} {ticker}: {insert_error}")
                                continue
                        
                        except Exception as trade_error:
                            errors += 1
                            logger.warning(f"Error processing trade: {trade_error}, data: {trade_data}")
                            continue
                    
                # Note: API is locked to page 0 only, so we don't paginate
                # We only get the 10 most recent trades per chamber per run
                # API docs claim 0-25 limit, but they're liars - only 10 works (as of 2025-12-27)
                
            except requests.exceptions.HTTPError as http_error:
                logger.error(f"HTTP error for {chamber}: {http_error}")
            except requests.exceptions.RequestException as req_error:
                logger.error(f"Request error for {chamber}: {req_error}")
            except Exception as e:
                logger.error(f"Unexpected error processing {chamber}: {e}", exc_info=True)
        
        # Log completion
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Found {total_trades_found} trades: {new_trades} new, {skipped_duplicates} duplicates, {skipped_no_ticker} no ticker, {ai_analyzed} AI analyzed, {errors} errors"
        log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
        mark_job_completed('congress_trades', target_date, None, [], duration_ms=duration_ms)
        logger.info(f"✅ Congress trades job completed: {message} in {duration_ms/1000:.2f}s")
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('congress_trades', target_date, None, str(e), duration_ms=duration_ms)
        except Exception:
            pass
        logger.error(f"❌ Congress trades job failed: {e}", exc_info=True)


def analyze_congress_trades_job() -> None:
    """Analyze unscored congress trades using committee data to calculate conflict scores.
    
    This job:
    1. Finds trades where conflict_score IS NULL
    2. Enriches with committee assignments and sector data
    3. Uses Granite AI to calculate conflict scores
    4. Updates conflict_score and notes fields
    
    Note: This is a wrapper around analyze_congress_trades_batch.py logic.
    Processes in batches to avoid overwhelming Ollama.
    """
    job_id = 'analyze_congress_trades'
    start_time = time.time()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info("Starting congress trades analysis job...")
        
        # Mark job as started
        target_date = datetime.now(timezone.utc).date()
        mark_job_started('analyze_congress_trades', target_date)
        
        # Import dependencies (lazy imports)
        try:
            from supabase_client import SupabaseClient
            from ollama_client import OllamaClient
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            mark_job_failed('analyze_congress_trades', target_date, None, message, duration_ms=duration_ms)
            return
        
        # Import analysis functions from batch script
        # We'll import the functions directly to reuse the logic
        import sys
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(project_root))
        sys.path.insert(0, str(project_root / 'web_dashboard'))
        
        # Import the analysis functions
        # Note: fix_failed_scores is NOT imported - it should only be run manually via --fix-only flag
        from scripts.analyze_congress_trades_batch import (
            get_trade_context,
            analyze_trade,
            is_low_risk_asset
        )
        
        # Initialize clients
        client = SupabaseClient(use_service_role=True)
        ollama = OllamaClient()
        
        # Check Ollama health
        if not ollama or not ollama.check_health():
            duration_ms = int((time.time() - start_time) * 1000)
            message = "Ollama is not accessible - skipping analysis"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.warning(f"⚠️  {message}")
            mark_job_completed('analyze_congress_trades', target_date, None, [], duration_ms=duration_ms)
            return
        
        # Note: fix_failed_scores() is NOT called here automatically
        # It should only be run manually via the batch script with --fix-only flag
        # This is because 0.0 might be a legitimate score in the future
        
        # Process unscored trades in batches
        batch_size = 10  # Process 10 trades per run to avoid overwhelming Ollama
        total_processed = 0
        total_errors = 0
        
        try:
            # Fetch unscored trades (newest first)
            response = client.supabase.table("congress_trades_enriched")\
                .select("*")\
                .is_("conflict_score", "null")\
                .order("transaction_date", desc=True)\
                .limit(batch_size)\
                .execute()
            
            trades = response.data
            
            if not trades:
                duration_ms = int((time.time() - start_time) * 1000)
                message = "No unscored trades found"
                log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
                logger.info(f"✅ {message}")
                mark_job_completed('analyze_congress_trades', target_date, None, [], duration_ms=duration_ms)
                return
            
            logger.info(f"Processing {len(trades)} unscored trades...")
            
            # Process each trade
            for trade in trades:
                try:
                    # Enrich with committee data and sector info
                    context = get_trade_context(client, trade)
                    
                    # Check if this is a low-risk asset that doesn't need AI analysis
                    is_low_risk, filter_reason = is_low_risk_asset(context)
                    
                    if is_low_risk:
                        # Automatically assign low conflict score without AI analysis
                        analysis = {
                            'conflict_score': 0.0,
                            'confidence_score': 1.0,
                            'reasoning': f"Auto-filtered: {filter_reason}"
                        }
                        logger.info(f"   [FILTERED] {context['politician']} - {context['ticker']}: {filter_reason}")
                    else:
                        # Analyze with AI
                        analysis = analyze_trade(ollama, context, model='granite3.3:8b')
                    
                    if analysis and 'conflict_score' in analysis:
                        score = float(analysis['conflict_score'])
                        confidence = float(analysis.get('confidence_score', 0.75))  # Default to 0.75 if missing
                        reasoning = analysis.get('reasoning', 'No reasoning provided')
                        
                        # Save to PostgreSQL (separate database to save Supabase costs)
                        try:
                            from postgres_client import PostgresClient
                            postgres = PostgresClient()
                            
                            postgres.execute_update(
                                """
                                INSERT INTO congress_trades_analysis 
                                    (trade_id, conflict_score, confidence_score, reasoning, model_used, analysis_version)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (trade_id, model_used, analysis_version) 
                                DO UPDATE SET 
                                    conflict_score = EXCLUDED.conflict_score,
                                    confidence_score = EXCLUDED.confidence_score,
                                    reasoning = EXCLUDED.reasoning,
                                    analyzed_at = NOW()
                                """,
                                (trade['id'], score, confidence, reasoning, 'granite3.3:8b', 1)
                            )
                            
                            logger.info(f"   [SCORED] {context['politician']} - {context['ticker']}: conflict={score:.2f}, confidence={confidence:.2f}")
                            total_processed += 1
                        except Exception as db_error:
                            logger.error(f"   [ERROR] Failed to save analysis to Postgres: {db_error}")
                            total_errors += 1
                    else:
                        logger.warning(f"   [WARN] Failed to parse AI response for trade ID {trade['id']}")
                        total_errors += 1
                        # Don't update - leave as NULL so it can be retried
                        
                except Exception as e:
                    logger.error(f"Error processing trade {trade.get('id', 'unknown')}: {e}", exc_info=True)
                    total_errors += 1
                    # Continue processing other trades
            
            # Log completion
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Processed {total_processed} trades, {total_errors} errors"
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            logger.info(f"✅ Congress trades analysis job completed: {message} in {duration_ms/1000:.2f}s")
            mark_job_completed('analyze_congress_trades', target_date, None, [], duration_ms=duration_ms)
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Error during analysis: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}", exc_info=True)
            mark_job_failed('analyze_congress_trades', target_date, None, str(e), duration_ms=duration_ms)
            
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Critical error: {e}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        logger.error(f"❌ Congress trades analysis job failed: {e}", exc_info=True)
        try:
            from utils.job_tracking import mark_job_failed
            target_date = datetime.now(timezone.utc).date()
            mark_job_failed('analyze_congress_trades', target_date, None, str(e), duration_ms=duration_ms)
        except:
            pass


def rescore_congress_sessions_job(limit: int = 1000, batch_size: int = 10, model: str = 'granite3.3:8b') -> None:
    """Manual job: Rescore congress trades sessions using updated AI logic.
    
    This is a ONE-TIME job for backfilling the entire database with the new:
    - Intent Classification logic
    - Leadership jurisdiction fix
    - Batch prefetching optimization
    
    Args:
        limit: Max sessions to process (default 1000)
        batch_size: Number of sessions per batch (default 10)
        model: Model to use (default granite3.3:8b)
    """
    job_id = 'rescore_congress_sessions'
    start_time = time.time()
    
    try:
        # Import job tracking
        from utils.job_tracking import mark_job_started, mark_job_completed, mark_job_failed
        
        logger.info(f"Starting congress sessions rescore job (Limit: {limit}, Batch: {batch_size}, Model: {model})...")
        
        # Mark job as started
        target_date = datetime.now(timezone.utc).date()
        mark_job_started('rescore_congress_sessions', target_date)
        
        # Import dependencies
        try:
            import subprocess
            from pathlib import Path
        except ImportError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Missing dependency: {e}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            mark_job_failed('rescore_congress_sessions', target_date, None, message, duration_ms=duration_ms)
            return
        
        # Build script path
        project_root = Path(__file__).parent.parent.parent
        script_path = project_root / 'web_dashboard' / 'scripts' / 'analyze_congress_trades_batch.py'
        
        if not script_path.exists():
            duration_ms = int((time.time() - start_time) * 1000)
            message = f"Analysis script not found: {script_path}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            logger.error(f"❌ {message}")
            mark_job_failed('rescore_congress_sessions', target_date, None, message, duration_ms=duration_ms)
            return
        
        # Run the batch analysis script with rescore parameters
        # Cast to int to handle float values from Streamlit number_input
        limit = int(limit)
        batch_size = int(batch_size)
        
        cmd = [
            'python', '-u', str(script_path),
            '--sessions',
            '--rescore',
            '--batch-size', str(batch_size),
            '--model', str(model),
            '--limit', str(limit)
        ]
        logger.info(f"Executing command: {' '.join(cmd)}")
        logger.info(f"Working Directory: {str(project_root)}")

        
        # Use Popen to stream output line-by-line
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout
            text=True,
            bufsize=1,  # Line buffered
            encoding='utf-8'
        )

        # Stream output
        full_output = []
        last_log_time = time.time()
        
        # Read stdout line by line
        for line in iter(process.stdout.readline, ''):
            clean_line = line.strip()
            full_output.append(clean_line)
            
            # Log significant lines to main logger immediately
            # This makes them visible in the console/logs in real-time
            if clean_line:
                if any(x in clean_line for x in ["SESSION ANALYZED", "Completed processing", "Starting AI Analysis", "Traceback", "Error"]):
                    logger.info(f"   [Script] {clean_line}")
                # Log progress every 60 seconds regardless of content
                elif time.time() - last_log_time > 60:
                    logger.info(f"   [Script] {clean_line}")
                    last_log_time = time.time()
        
        process.stdout.close()
        return_code = process.wait()
        
        if return_code == 0:
            duration_ms = int((time.time() - start_time) * 1000)
            # Find completion message
            completed_lines = [line for line in full_output if 'Completed processing' in line]
            
            if completed_lines:
                # Remove timestamp/level prefix if present to keep it clean
                msg_text = completed_lines[-1]
                if "INFO -" in msg_text:
                    message = msg_text.split('INFO -')[-1].strip()
                else:
                    message = msg_text
            else:
                message = f"Rescore completed ({limit} sessions)"
            
            log_job_execution(job_id, success=True, message=message, duration_ms=duration_ms)
            mark_job_completed('rescore_congress_sessions', target_date, None, [], duration_ms=duration_ms)
            logger.info(f"✅ {message}")
        else:
            duration_ms = int((time.time() - start_time) * 1000)
            # Use last 10 lines as error snippet
            error_snippet = "\n".join(full_output[-10:])
            message = f"Script failed with exit code {return_code}. Last output:\n{error_snippet}"
            log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
            mark_job_failed('rescore_congress_sessions', target_date, None, message, duration_ms=duration_ms)
            logger.error(f"❌ Script failed: {message}")
        
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start_time) * 1000)
        message = "Job timed out after 2 hours"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('rescore_congress_sessions', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass
        logger.error(f"❌ {message}")
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        message = f"Error: {str(e)}"
        log_job_execution(job_id, success=False, message=message, duration_ms=duration_ms)
        try:
            mark_job_failed('rescore_congress_sessions', target_date, None, message, duration_ms=duration_ms)
        except Exception:
            pass
        logger.error(f"❌ Congress sessions rescore job failed: {e}", exc_info=True)



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
            name=f"{get_job_icon('exchange_rates')} Refresh Exchange Rates",
            replace_existing=True
        )
        logger.info("Registered job: exchange_rates (every 2 hours)")
    
    # Performance metrics job - daily at 5 PM EST (after market close)
    if AVAILABLE_JOBS['performance_metrics']['enabled_by_default']:
        scheduler.add_job(
            populate_performance_metrics_job,
            trigger=CronTrigger(hour=17, minute=0, timezone='America/New_York'),
            id='performance_metrics',
            name=f"{get_job_icon('performance_metrics')} Populate Performance Metrics",
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
            name=f"{get_job_icon('update_portfolio_prices')} Update Portfolio Prices",
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
            name=f"{get_job_icon('update_portfolio_prices_close')} Update Portfolio Prices (Market Close)",
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
            name=f"{get_job_icon('market_research_premarket')} Market Research (Pre-Market)",
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
            name=f"{get_job_icon('market_research_midmorning')} Market Research (Mid-Morning)",
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
            name=f"{get_job_icon('market_research_powerhour')} Market Research (Power Hour)",
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
            name=f"{get_job_icon('market_research_postmarket')} Market Research (Post-Market)",
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
            name=f"{get_job_icon('market_research_premarket')} Market Research (Pre-Market)",
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
            name=f"{get_job_icon('market_research_midmorning')} Market Research (Mid-Morning)",
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
            name=f"{get_job_icon('market_research_powerhour')} Market Research (Power Hour)",
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
            name=f"{get_job_icon('market_research_postmarket')} Market Research (Post-Market)",
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
            name=f"{get_job_icon('ticker_research_job')} Ticker Specific Research",
            replace_existing=True
        )
        logger.info("Registered job: ticker_research_job (every 6 hours)")

        # Opportunity Discovery: Every 12 hours
        scheduler.add_job(
            opportunity_discovery_job,
            trigger=CronTrigger(
                hour='*/12',
                minute=30,
                timezone='America/New_York'
            ),
            id='opportunity_discovery_job',
            name=f"{get_job_icon('opportunity_discovery_job')} Opportunity Discovery",
            replace_existing=True
        )
        logger.info("Registered job: opportunity_discovery_job (every 12 hours)")

    # Alpha Research Job: Every 6 hours (offset)
    if AVAILABLE_JOBS.get('alpha_research', {}).get('enabled_by_default'):
        from scheduler.jobs_alpha import alpha_research_job
        scheduler.add_job(
            alpha_research_job,
            trigger=CronTrigger(
                hour='*/6',
                minute=45, # Offset from others
                timezone='America/New_York'
            ),
            id='alpha_research',
            name=f"{get_job_icon('alpha_research')} Alpha Hunter",
            replace_existing=True
        )
        logger.info("Registered job: alpha_research (every 6 hours)")
    
    # Benchmark refresh job - daily after market close
    if AVAILABLE_JOBS['benchmark_refresh']['enabled_by_default']:
        cron_config = AVAILABLE_JOBS['benchmark_refresh']['cron_triggers'][0]
        scheduler.add_job(
            benchmark_refresh_job,
            trigger=CronTrigger(
                hour=cron_config['hour'],
                minute=cron_config['minute'],
                timezone=cron_config['timezone']
            ),
            id='benchmark_refresh',
            name=f"{get_job_icon('benchmark_refresh')} Refresh Benchmark Data",
            replace_existing=True
        )
        logger.info(f"Registered job: benchmark_refresh (daily at {cron_config['hour']}:{cron_config['minute']:02d} {cron_config['timezone']})")
    
    # Social sentiment job - every 30 minutes
    if AVAILABLE_JOBS['social_sentiment']['enabled_by_default']:
        scheduler.add_job(
            fetch_social_sentiment_job,
            trigger=IntervalTrigger(minutes=AVAILABLE_JOBS['social_sentiment']['default_interval_minutes']),
            id='social_sentiment',
            name=f"{get_job_icon('social_sentiment')} Social Sentiment Tracking",
            replace_existing=True
        )
        logger.info("Registered job: social_sentiment (every 30 minutes)")
    
    # Social sentiment AI analysis job - every 2 hours
    if AVAILABLE_JOBS['social_sentiment_ai']['enabled_by_default']:
        scheduler.add_job(
            social_sentiment_ai_job,
            trigger=IntervalTrigger(minutes=AVAILABLE_JOBS['social_sentiment_ai']['default_interval_minutes']),
            id='social_sentiment_ai',
            name=f"{get_job_icon('social_sentiment_ai')} Social Sentiment AI Analysis",
            replace_existing=True
        )
        logger.info("Registered job: social_sentiment_ai (every 2 hours)")
    
    # Social metrics cleanup job - daily at 3:00 AM
    scheduler.add_job(
        cleanup_social_metrics_job,
        trigger=CronTrigger(
            hour=3,
            minute=0,
            timezone='America/New_York'
        ),
        id='social_metrics_cleanup',
        name=f"{get_job_icon('social_metrics_cleanup')} Social Metrics Cleanup",
        replace_existing=True
    )
    logger.info("Registered job: social_metrics_cleanup (daily at 3:00 AM EST)")
    
    # Rescore Congress Sessions (Manual Only)
    # Always register this so it appears in UI, but it has no schedule
    # We use a dummy date trigger far in the future
    scheduler.add_job(
        rescore_congress_sessions_job,
        trigger='date', 
        run_date=datetime(9999, 12, 31, tzinfo=timezone.utc), # Effectively never
        id='rescore_congress_sessions',
        name=f"{get_job_icon('rescore_congress_sessions')} Rescore Congress Sessions (Manual)",
        replace_existing=True
    )
    scheduler.pause_job('rescore_congress_sessions') # Ensure it's paused/manual only
    logger.info("Registered job: rescore_congress_sessions (Manual only)")
    
    # Congress trades job - every 12 minutes (120 runs/day × 2 API calls = 240 total, stays under 250 limit)
    if AVAILABLE_JOBS['congress_trades']['enabled_by_default']:
        scheduler.add_job(
            fetch_congress_trades_job,
            trigger=IntervalTrigger(minutes=12),
            id='congress_trades',
            name=f"{get_job_icon('congress_trades')} Fetch Congress Trades",
            replace_existing=True
        )
        logger.info("Registered job: congress_trades (every 12 minutes - 120 runs/day, 240 API calls/day)")
    
    # Analyze congress trades job - every 30 minutes (processes unscored trades with committee data)
    if AVAILABLE_JOBS['analyze_congress_trades']['enabled_by_default']:
        scheduler.add_job(
            analyze_congress_trades_job,
            trigger=IntervalTrigger(minutes=AVAILABLE_JOBS['analyze_congress_trades']['default_interval_minutes']),
            id='analyze_congress_trades',
            name=f"{get_job_icon('analyze_congress_trades')} Analyze Congress Trades",
            replace_existing=True
        )
        logger.info("Registered job: analyze_congress_trades (every 30 minutes - processes unscored trades)")