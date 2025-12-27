#!/usr/bin/env python3
"""
Social Sentiment Service
========================

Service for fetching and storing social sentiment data from StockTwits and Reddit.
Part of Phase 2: Social Sentiment Tracking.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from web_dashboard/.env
# Try web_dashboard/.env first (when running from project root)
# Then fall back to .env in current directory
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()  # Fallback to current directory

logger = logging.getLogger(__name__)

# FlareSolverr configuration (for bypassing Cloudflare on StockTwits)
# Default: host.docker.internal for Docker containers
# Override: FLARESOLVERR_URL env variable for local testing (e.g., Tailscale)
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "http://host.docker.internal:8191")

# Import clients
from web_dashboard.postgres_client import PostgresClient
from web_dashboard.supabase_client import SupabaseClient
from web_dashboard.ollama_client import OllamaClient, get_ollama_client


class SocialSentimentService:
    """Service for fetching and storing social sentiment metrics"""
    
    def __init__(
        self,
        postgres_client: Optional[PostgresClient] = None,
        supabase_client: Optional[SupabaseClient] = None,
        ollama_client: Optional[OllamaClient] = None
    ):
        """Initialize social sentiment service
        
        Args:
            postgres_client: Optional PostgresClient instance
            supabase_client: Optional SupabaseClient instance
            ollama_client: Optional OllamaClient instance
        """
        try:
            self.postgres = postgres_client or PostgresClient()
        except Exception as e:
            logger.error(f"Failed to initialize PostgresClient: {e}")
            raise
        
        try:
            self.supabase = supabase_client or SupabaseClient(use_service_role=True)
        except Exception as e:
            logger.error(f"Failed to initialize SupabaseClient: {e}")
            raise
        
        self.ollama = ollama_client or get_ollama_client()
        
        # FlareSolverr URL (can be overridden per instance if needed)
        self.flaresolverr_url = FLARESOLVERR_URL
    
    def make_flaresolverr_request(self, url: str) -> Optional[Dict[str, Any]]:
        """Make a request through FlareSolverr to bypass Cloudflare protection.
        
        Args:
            url: Target URL to fetch via FlareSolverr
            
        Returns:
            Dictionary with parsed JSON data if successful, None if failed
        """
        try:
            flaresolverr_endpoint = f"{self.flaresolverr_url}/v1"
            
            payload = {
                "cmd": "request.get",
                "url": url,
                "maxTimeout": 60000  # 60 seconds
            }
            
            logger.debug(f"Requesting via FlareSolverr: {url}")
            response = requests.post(
                flaresolverr_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=70  # Slightly longer than maxTimeout
            )
            
            response.raise_for_status()
            flaresolverr_data = response.json()
            
            # Check FlareSolverr status
            if flaresolverr_data.get("status") != "ok":
                error_msg = flaresolverr_data.get("message", "Unknown error")
                logger.warning(f"FlareSolverr returned error status: {error_msg}")
                return None
            
            # Extract solution
            solution = flaresolverr_data.get("solution", {})
            if not solution:
                logger.warning("FlareSolverr response missing solution")
                return None
            
            # Get the actual HTTP status from the solution
            http_status = solution.get("status", 0)
            response_body = solution.get("response", "")
            
            # Check if the target site returned an error
            if http_status != 200:
                logger.warning(f"Target site returned HTTP {http_status} via FlareSolverr")
                # Log first 200 chars of response for debugging
                if response_body:
                    preview = response_body[:200] if len(response_body) > 200 else response_body
                    logger.debug(f"Response preview: {preview}")
                return None
            
            # Check if response body is empty
            if not response_body or not response_body.strip():
                logger.warning("FlareSolverr returned empty response body")
                return None
            
            # Parse the response body (should be JSON for StockTwits API)
            # FlareSolverr may return HTML with JSON inside, so try to extract JSON
            try:
                # Try parsing as-is first
                data = json.loads(response_body)
                logger.debug(f"Successfully fetched data via FlareSolverr (status: {http_status}, {len(response_body)} bytes)")
                return data
            except json.JSONDecodeError:
                # If direct parse fails, try to extract JSON from HTML
                # FlareSolverr sometimes wraps JSON in HTML (e.g., <pre> tags)
                import re
                # Look for JSON object in the response (starts with { and ends with })
                json_match = re.search(r'\{.*\}', response_body, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        data = json.loads(json_str)
                        logger.debug(f"Successfully extracted JSON from HTML response via FlareSolverr")
                        return data
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse extracted JSON from FlareSolverr response: {e}")
                else:
                    # Log first 500 chars to help debug what we got
                    preview = response_body[:500] if len(response_body) > 500 else response_body
                    logger.warning(f"Failed to find JSON in FlareSolverr response")
                    logger.debug(f"Response preview (first 500 chars): {preview}")
                    # Check if it looks like HTML (Cloudflare challenge page)
                    if response_body.strip().startswith('<') or 'cloudflare' in response_body.lower():
                        logger.warning("Response appears to be HTML (Cloudflare challenge) - FlareSolverr may need more time")
                return None
                
        except requests.exceptions.ConnectionError:
            logger.debug(f"FlareSolverr unavailable at {self.flaresolverr_url} - will fallback to direct request")
            return None
        except requests.exceptions.Timeout:
            logger.warning(f"FlareSolverr request timed out - will fallback to direct request")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"FlareSolverr request failed: {e} - will fallback to direct request")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error with FlareSolverr: {e} - will fallback to direct request")
            return None
    
    def get_watched_tickers(self) -> List[str]:
        """Get list of active tickers from watched_tickers table
        
        Returns:
            List of ticker symbols to monitor
        """
        try:
            result = self.supabase.supabase.table("watched_tickers")\
                .select("ticker")\
                .eq("is_active", True)\
                .execute()
            
            tickers = [row['ticker'] for row in result.data if row.get('ticker')]
            logger.debug(f"Found {len(tickers)} active watched tickers")
            return tickers
            
        except Exception as e:
            logger.error(f"Error fetching watched tickers: {e}")
            return []
    
    def fetch_stocktwits_sentiment(self, ticker: str) -> Dict[str, Any]:
        """Fetch sentiment data from StockTwits API
        
        Args:
            ticker: Ticker symbol to fetch
            
        Returns:
            Dictionary with:
            - volume: Post count in last 60 minutes
            - bull_bear_ratio: Ratio of Bullish to Bearish posts (0.0 to 1.0)
            - raw_data: Top 3 posts as JSONB
        """
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
        
        # Try FlareSolverr first to bypass Cloudflare protection
        data = None
        try:
            data = self.make_flaresolverr_request(url)
        except Exception as e:
            logger.debug(f"FlareSolverr request failed for {ticker}: {e}")
        
        # Fallback to direct request if FlareSolverr failed or unavailable
        if data is None:
            logger.debug(f"Falling back to direct request for {ticker}")
            # Use browser-like User-Agent (required by StockTwits)
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9"
            }
            
            try:
                response = requests.get(url, headers=headers, timeout=10)
                
                # Handle 403 Forbidden (may be rate limiting or IP blocking)
                if response.status_code == 403:
                    logger.warning(f"StockTwits API returned 403 Forbidden for {ticker} (direct request).")
                    logger.warning("  FlareSolverr may be unavailable or Cloudflare blocking persists.")
                    return {
                        'volume': 0,
                        'bull_bear_ratio': 0.0,
                        'raw_data': None
                    }
                
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Direct StockTwits API request failed for {ticker}: {e}")
                return {
                    'volume': 0,
                    'bull_bear_ratio': 0.0,
                    'raw_data': None
                }
        
        # Process the data (from either FlareSolverr or direct request)
        if not data:
            return {
                'volume': 0,
                'bull_bear_ratio': 0.0,
                'raw_data': None
            }
        
        try:
            messages = data.get('messages', [])
            if not messages:
                logger.debug(f"No messages found for {ticker} on StockTwits")
                return {
                    'volume': 0,
                    'bull_bear_ratio': 0.0,
                    'raw_data': None
                }
            
            # Filter messages by created_at (last 60 minutes)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=60)
            recent_messages = []
            bull_count = 0
            bear_count = 0
            
            for msg in messages:
                created_at_str = msg.get('created_at')
                if not created_at_str:
                    continue
                
                try:
                    # Parse timestamp (StockTwits uses ISO format like "2024-01-15T10:30:00Z")
                    msg_dt = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
                    
                    if msg_dt >= cutoff_time:
                        recent_messages.append(msg)
                        
                        # Check sentiment entities
                        entities = msg.get('entities', {})
                        sentiment = entities.get('sentiment')
                        if sentiment and isinstance(sentiment, dict):
                            basic = sentiment.get('basic')
                            if basic == 'Bullish':
                                bull_count += 1
                            elif basic == 'Bearish':
                                bear_count += 1
                except (ValueError, AttributeError) as e:
                    logger.debug(f"Could not parse timestamp for message: {e}")
                    continue
            
            # Calculate bull/bear ratio
            total_labeled = bull_count + bear_count
            if total_labeled > 0:
                bull_bear_ratio = bull_count / total_labeled
            else:
                bull_bear_ratio = 0.0
            
            # Get top 3 posts for raw_data
            top_posts = recent_messages[:3]
            raw_data = None
            if top_posts:
                raw_data = [
                    {
                        'body': msg.get('body', ''),
                        'created_at': msg.get('created_at', ''),
                        'user': msg.get('user', {}).get('username', 'Unknown')
                    }
                    for msg in top_posts
                ]
            
            logger.debug(f"StockTwits {ticker}: volume={len(recent_messages)}, ratio={bull_bear_ratio:.2f}")
            
            return {
                'volume': len(recent_messages),
                'bull_bear_ratio': bull_bear_ratio,
                'raw_data': raw_data
            }
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"StockTwits API request failed for {ticker}: {e}")
            return {
                'volume': 0,
                'bull_bear_ratio': 0.0,
                'raw_data': None
            }
        except Exception as e:
            logger.error(f"Error fetching StockTwits sentiment for {ticker}: {e}", exc_info=True)
            return {
                'volume': 0,
                'bull_bear_ratio': 0.0,
                'raw_data': None
            }
    
    def fetch_reddit_sentiment(self, ticker: str) -> Dict[str, Any]:
        """Fetch sentiment data from Reddit using public JSON endpoint
        
        Uses Reddit's public search API without authentication.
        Respects rate limits with 2-second delay between requests.
        
        Args:
            ticker: Ticker symbol to fetch
            
        Returns:
            Dictionary with:
            - volume: Post count in last 24 hours
            - sentiment_label: AI-categorized label (EUPHORIC, BULLISH, NEUTRAL, BEARISH, FEARFUL)
            - sentiment_score: Numeric score mapped from label (-2.0 to 2.0)
            - raw_data: Top 3 posts/comments as JSONB
        """
        try:
            # Rate limiting: wait 2 seconds before request to respect unauthenticated rate limits
            time.sleep(2)
            
            # Use browser-like User-Agent to avoid 429 errors
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Search Reddit for ticker (with $ prefix and without)
            search_queries = [f"${ticker}", ticker]
            all_posts = []
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            
            for query in search_queries:
                try:
                    # Reddit public search JSON endpoint
                    url = f"https://www.reddit.com/search.json?q={query}&sort=new&t=day&limit=10"
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    # Handle rate limiting
                    if response.status_code == 429:
                        logger.warning(f"Reddit rate limit hit for {ticker}. Waiting longer...")
                        time.sleep(5)  # Wait longer if rate limited
                        continue
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    # Parse nested JSON structure: response['data']['children'][i]['data']
                    if 'data' in data and 'children' in data['data']:
                        for child in data['data']['children']:
                            if 'data' not in child:
                                continue
                            
                            post_data = child['data']
                            
                            # Extract fields
                            title = post_data.get('title', '')
                            selftext = post_data.get('selftext', '')
                            ups = post_data.get('ups', 0)  # upvotes
                            num_comments = post_data.get('num_comments', 0)
                            created_utc = post_data.get('created_utc', 0)
                            url = post_data.get('url', '')
                            subreddit = post_data.get('subreddit', '')
                            
                            # Convert created_utc (Unix timestamp) to datetime
                            if created_utc:
                                post_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                                
                                # Filter posts from last 24 hours
                                if post_dt >= cutoff_time:
                                    all_posts.append({
                                        'title': title,
                                        'selftext': selftext,
                                        'score': ups,  # Use upvotes as score
                                        'num_comments': num_comments,
                                        'created_utc': created_utc,
                                        'url': url,
                                        'subreddit': subreddit
                                    })
                
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        logger.warning(f"Reddit rate limit for {ticker} query '{query}'. Skipping.")
                        time.sleep(5)
                    else:
                        logger.debug(f"HTTP error searching Reddit for {query}: {e}")
                    continue
                except Exception as e:
                    logger.debug(f"Error searching Reddit for {query}: {e}")
                    continue
            
            # Deduplicate by URL
            seen_urls = set()
            unique_posts = []
            for post in all_posts:
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    unique_posts.append(post)
            
            # Sort by score (upvotes) and take top 5 for AI analysis
            unique_posts.sort(key=lambda x: x['score'], reverse=True)
            top_5_posts = unique_posts[:5]
            
            # Combine post titles and bodies for AI analysis
            texts_for_ai = []
            for post in top_5_posts:
                text = f"{post['title']}\n{post['selftext'][:500]}"
                texts_for_ai.append(text)
            
            # Analyze sentiment with Ollama
            sentiment_label = 'NEUTRAL'
            sentiment_score = 0.0
            reasoning = ""
            
            if texts_for_ai and self.ollama:
                try:
                    result = self.ollama.analyze_crowd_sentiment(texts_for_ai, ticker)
                    sentiment_label = result.get('sentiment', 'NEUTRAL')
                    reasoning = result.get('reasoning', '')
                    sentiment_score = self.map_sentiment_label_to_score(sentiment_label)
                except Exception as e:
                    logger.warning(f"Ollama sentiment analysis failed for {ticker}: {e}")
            
            # Prepare raw_data (top 3 posts)
            raw_data = None
            if unique_posts:
                raw_data = [
                    {
                        'title': post['title'],
                        'selftext': post['selftext'][:500],  # Limit length
                        'score': post['score'],
                        'num_comments': post['num_comments'],
                        'subreddit': post['subreddit'],
                        'url': post['url']
                    }
                    for post in unique_posts[:3]
                ]
            
            logger.debug(f"Reddit {ticker}: volume={len(unique_posts)}, sentiment={sentiment_label} ({sentiment_score:.1f})")
            
            return {
                'volume': len(unique_posts),
                'sentiment_label': sentiment_label,
                'sentiment_score': sentiment_score,
                'raw_data': raw_data
            }
            
        except Exception as e:
            logger.error(f"Error fetching Reddit sentiment for {ticker}: {e}", exc_info=True)
            return {
                'volume': 0,
                'sentiment_label': 'NEUTRAL',
                'sentiment_score': 0.0,
                'raw_data': None
            }
    
    def map_sentiment_label_to_score(self, label: str) -> float:
        """Map sentiment label to numeric score
        
        Args:
            label: Sentiment label (EUPHORIC, BULLISH, NEUTRAL, BEARISH, FEARFUL)
            
        Returns:
            Numeric score from -2.0 to 2.0
        """
        mapping = {
            "EUPHORIC": 2.0,
            "BULLISH": 1.0,
            "NEUTRAL": 0.0,
            "BEARISH": -1.0,
            "FEARFUL": -2.0
        }
        return mapping.get(label.upper(), 0.0)
    
    def save_metrics(self, ticker: str, platform: str, metrics: Dict[str, Any]) -> None:
        """Save social sentiment metrics to database
        
        Args:
            ticker: Ticker symbol
            platform: 'stocktwits' or 'reddit'
            metrics: Dictionary with metric data
        """
        try:
            # Prepare raw_data as JSONB
            raw_data_json = None
            if metrics.get('raw_data'):
                raw_data_json = json.dumps(metrics['raw_data'])
            
            # Build query based on platform
            if platform == 'stocktwits':
                query = """
                    INSERT INTO social_metrics 
                    (ticker, platform, volume, bull_bear_ratio, raw_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                """
                params = (
                    ticker,
                    platform,
                    metrics.get('volume', 0),
                    metrics.get('bull_bear_ratio', 0.0),
                    raw_data_json
                )
            elif platform == 'reddit':
                query = """
                    INSERT INTO social_metrics 
                    (ticker, platform, volume, sentiment_label, sentiment_score, raw_data, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                params = (
                    ticker,
                    platform,
                    metrics.get('volume', 0),
                    metrics.get('sentiment_label', 'NEUTRAL'),
                    metrics.get('sentiment_score', 0.0),
                    raw_data_json
                )
            else:
                logger.error(f"Unknown platform: {platform}")
                return
            
            self.postgres.execute_update(query, params)
            logger.debug(f"Saved {platform} metrics for {ticker}")
            
        except Exception as e:
            logger.error(f"Error saving {platform} metrics for {ticker}: {e}", exc_info=True)
            raise
    
    def run_daily_cleanup(self) -> Dict[str, int]:
        """Run daily cleanup to implement two-tier retention policy.
        
        Tier 1 (7 days): Remove raw_data JSON from old records (keep metrics)
        Tier 2 (90 days): Delete entire rows older than 90 days
        
        Returns:
            Dictionary with 'rows_updated' and 'rows_deleted' counts
        """
        try:
            logger.info("🧹 Starting social metrics cleanup...")
            
            # Step 1: The Lobotomy (Remove heavy JSON, keep the metrics)
            logger.info("  Step 1: Removing raw_data JSON from records older than 7 days...")
            update_query = """
                UPDATE social_metrics 
                SET raw_data = NULL 
                WHERE created_at < NOW() - INTERVAL '7 days' 
                  AND raw_data IS NOT NULL
            """
            rows_updated = self.postgres.execute_update(update_query)
            logger.info(f"  ✅ Removed raw_data from {rows_updated} records (7+ days old)")
            
            # Step 2: The Grim Reaper (Delete old rows)
            logger.info("  Step 2: Deleting records older than 90 days...")
            delete_query = """
                DELETE FROM social_metrics 
                WHERE created_at < NOW() - INTERVAL '90 days'
            """
            rows_deleted = self.postgres.execute_update(delete_query)
            logger.info(f"  ✅ Deleted {rows_deleted} records (90+ days old)")
            
            logger.info(f"✅ Social metrics cleanup complete: {rows_updated} updated, {rows_deleted} deleted")
            
            return {
                'rows_updated': rows_updated,
                'rows_deleted': rows_deleted
            }
            
        except Exception as e:
            logger.error(f"❌ Error during social metrics cleanup: {e}", exc_info=True)
            raise

