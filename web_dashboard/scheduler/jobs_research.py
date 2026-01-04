"""
Research Jobs
=============

Jobs for fetching and storing market research articles from various sources.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add parent directory to path if needed (standard boilerplate for these jobs)
import sys

# Add project root to path for utils imports
current_dir = Path(__file__).resolve().parent
if current_dir.name == "scheduler":
    project_root = current_dir.parent.parent
else:
    project_root = current_dir.parent.parent

# Also ensure web_dashboard is in path for supabase_client imports
web_dashboard_path = str(Path(__file__).resolve().parent.parent)
if web_dashboard_path not in sys.path:
    sys.path.insert(0, web_dashboard_path)

# CRITICAL: Project root must be inserted LAST (at index 0) to ensure it comes
# BEFORE web_dashboard in sys.path. This prevents web_dashboard/utils from
# shadowing the project root's utils package.
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
elif sys.path[0] != str(project_root):
    # If it is in path but not first, move it to front
    sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))

from scheduler.scheduler_core import log_job_execution
from scheduler.jobs_common import calculate_relevance_score

# Initialize logger
logger = logging.getLogger(__name__)

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
        
        # specific, high-quality queries to avoid junk (astrology, etc.)
        queries = [
            "microcap stock analysis",
            "small cap undervalued stocks",
            "biotech stock catalysts upcoming",
            "penny stock signs of breakout",
            "stock market spinoffs 2025",
            "insider buying small cap stocks",
            "merger arbitrage opportunities small cap",
            # ETF / Index Rotation Tracking
            "stock added to Russell 2000 index",
            "S&P SmallCap 600 constituent change",
            "ETF rebalancing announcement"
        ]
        
        # Select query based on hour to rotate coverage
        query_index = datetime.now().hour % len(queries)
        base_query = queries[query_index]
        
        # Add negative keywords to explicitly block known junk
        # "astrology", "horoscope", "zodiac" -> The user specifically mentioned these
        negative_keywords = "-astrology -horoscope -zodiac -lottery"
        final_query = f"{base_query} {negative_keywords}"
        
        logger.info(f"Fetching market news with query: '{final_query}'")
        search_results = searxng_client.search_news(
            query=final_query,
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

