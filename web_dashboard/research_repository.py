#!/usr/bin/env python3
"""
Research Articles Repository
Handles CRUD operations for research articles stored in local Postgres
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from web_dashboard.postgres_client import PostgresClient

logger = logging.getLogger(__name__)


class ResearchRepository:
    """Repository for research articles stored in local Postgres"""
    
    def __init__(self, postgres_client: Optional[PostgresClient] = None):
        """Initialize research repository
        
        Args:
            postgres_client: Optional PostgresClient instance. If not provided, creates a new one.
        """
        try:
            self.client = postgres_client or PostgresClient()
            logger.debug("ResearchRepository initialized successfully")
        except Exception as e:
            logger.error(f"ResearchRepository initialization failed: {e}")
            raise
    
    def save_article(
        self,
        ticker: Optional[str] = None,
        sector: Optional[str] = None,
        article_type: str = "ticker_news",
        title: str = "",
        url: str = "",
        summary: Optional[str] = None,
        content: Optional[str] = None,
        source: Optional[str] = None,
        published_at: Optional[datetime] = None,
        relevance_score: Optional[float] = None,
        embedding: Optional[List[float]] = None
    ) -> Optional[str]:
        """Save a research article to the database
        
        Args:
            ticker: Stock ticker symbol (e.g., "NVDA")
            sector: Sector name (e.g., "Technology")
            article_type: Type of article ('ticker_news', 'market_news', 'earnings')
            title: Article title (required)
            url: Article URL (required, must be unique)
            summary: AI-generated summary
            content: Full article content
            source: Source name (e.g., "Yahoo Finance")
            published_at: When the article was published
            relevance_score: Relevance score (0.00 to 1.00)
            embedding: Vector embedding (list of 768 floats)
            
        Returns:
            Article ID (UUID as string) if successful, None otherwise
        """
        if not title or not url:
            logger.error("Title and URL are required")
            return None
        
        try:
            # Prepare published_at timestamp
            published_at_str = None
            if published_at:
                if published_at.tzinfo is None:
                    published_at = published_at.replace(tzinfo=timezone.utc)
                published_at_str = published_at.isoformat()
            
            # Prepare embedding (convert list to PostgreSQL vector format)
            embedding_str = None
            if embedding:
                # PostgreSQL vector format: '[0.1,0.2,0.3]'
                embedding_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
            
            # Build query dynamically based on whether embedding is provided
            if embedding_str:
                query = """
                    INSERT INTO research_articles (
                        ticker, sector, article_type, title, url, summary, content,
                        source, published_at, relevance_score, embedding
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector
                    )
                    ON CONFLICT (url) DO UPDATE SET
                        fetched_at = NOW(),
                        relevance_score = EXCLUDED.relevance_score,
                        summary = COALESCE(EXCLUDED.summary, research_articles.summary)
                    RETURNING id
                """
                params = (
                    ticker,
                    sector,
                    article_type,
                    title,
                    url,
                    summary,
                    content,
                    source,
                    published_at_str,
                    relevance_score,
                    embedding_str
                )
            else:
                query = """
                    INSERT INTO research_articles (
                        ticker, sector, article_type, title, url, summary, content,
                        source, published_at, relevance_score
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (url) DO UPDATE SET
                        fetched_at = NOW(),
                        relevance_score = EXCLUDED.relevance_score,
                        summary = COALESCE(EXCLUDED.summary, research_articles.summary)
                    RETURNING id
                """
                params = (
                    ticker,
                    sector,
                    article_type,
                    title,
                    url,
                    summary,
                    content,
                    source,
                    published_at_str,
                    relevance_score
                )
            
            with self.client.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                result = cursor.fetchone()
                conn.commit()
                
                if result:
                    article_id = str(result[0])
                    logger.info(f"✅ Saved article: {title[:50]}... (ID: {article_id})")
                    return article_id
                else:
                    logger.warning("Article saved but no ID returned")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error saving article: {e}")
            return None
    
    def get_articles_by_ticker(
        self,
        ticker: str,
        limit: int = 20,
        offset: int = 0,
        article_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get articles for a specific ticker
        
        Args:
            ticker: Stock ticker symbol
            limit: Maximum number of results
            offset: Number of results to skip
            article_type: Optional filter by article type
            
        Returns:
            List of article dictionaries
        """
        try:
            query = """
                SELECT id, ticker, sector, article_type, title, url, summary, content,
                       source, published_at, fetched_at, relevance_score
                FROM research_articles
                WHERE ticker = %s
            """
            params = [ticker]
            
            if article_type:
                query += " AND article_type = %s"
                params.append(article_type)
            
            query += " ORDER BY fetched_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            results = self.client.execute_query(query, tuple(params))
            
            # Convert timestamps to datetime objects
            for article in results:
                if article.get('published_at'):
                    article['published_at'] = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                if article.get('fetched_at'):
                    article['fetched_at'] = datetime.fromisoformat(article['fetched_at'].replace('Z', '+00:00'))
            
            logger.debug(f"Retrieved {len(results)} articles for ticker {ticker}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting articles by ticker: {e}")
            return []
    
    def get_recent_articles(
        self,
        limit: int = 20,
        days: int = 7,
        article_type: Optional[str] = None,
        ticker: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent articles
        
        Args:
            limit: Maximum number of results
            days: Number of days to look back
            article_type: Optional filter by article type
            ticker: Optional filter by ticker
            
        Returns:
            List of article dictionaries
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = """
                SELECT id, ticker, sector, article_type, title, url, summary, content,
                       source, published_at, fetched_at, relevance_score
                FROM research_articles
                WHERE fetched_at >= %s
            """
            params = [cutoff_date.isoformat()]
            
            if article_type:
                query += " AND article_type = %s"
                params.append(article_type)
            
            if ticker:
                query += " AND ticker = %s"
                params.append(ticker)
            
            query += " ORDER BY fetched_at DESC LIMIT %s"
            params.append(limit)
            
            results = self.client.execute_query(query, tuple(params))
            
            # Convert timestamps to datetime objects
            for article in results:
                if article.get('published_at'):
                    article['published_at'] = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                if article.get('fetched_at'):
                    article['fetched_at'] = datetime.fromisoformat(article['fetched_at'].replace('Z', '+00:00'))
            
            logger.debug(f"Retrieved {len(results)} recent articles")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting recent articles: {e}")
            return []
    
    def delete_old_articles(self, days_to_keep: int = 30) -> int:
        """Delete articles older than specified days
        
        Args:
            days_to_keep: Number of days of articles to keep
            
        Returns:
            Number of articles deleted
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
            
            query = "DELETE FROM research_articles WHERE fetched_at < %s"
            params = (cutoff_date.isoformat(),)
            
            rows_deleted = self.client.execute_update(query, params)
            logger.info(f"✅ Deleted {rows_deleted} old articles (older than {days_to_keep} days)")
            return rows_deleted
            
        except Exception as e:
            logger.error(f"❌ Error deleting old articles: {e}")
            return 0
    
    def search_articles(
        self,
        query_text: str,
        ticker: Optional[str] = None,
        limit: int = 10,
        min_relevance: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Search articles by text (basic text search, vector search coming later)
        
        Args:
            query_text: Search query
            ticker: Optional filter by ticker
            limit: Maximum number of results
            min_relevance: Minimum relevance score
            
        Returns:
            List of article dictionaries
        """
        try:
            search_query = """
                SELECT id, ticker, sector, article_type, title, url, summary, content,
                       source, published_at, fetched_at, relevance_score
                FROM research_articles
                WHERE (title ILIKE %s OR summary ILIKE %s OR content ILIKE %s)
                  AND relevance_score >= %s
            """
            params = [f"%{query_text}%", f"%{query_text}%", f"%{query_text}%", min_relevance]
            
            if ticker:
                search_query += " AND ticker = %s"
                params.append(ticker)
            
            search_query += " ORDER BY relevance_score DESC, fetched_at DESC LIMIT %s"
            params.append(limit)
            
            results = self.client.execute_query(search_query, tuple(params))
            
            # Convert timestamps to datetime objects
            for article in results:
                if article.get('published_at'):
                    article['published_at'] = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                if article.get('fetched_at'):
                    article['fetched_at'] = datetime.fromisoformat(article['fetched_at'].replace('Z', '+00:00'))
            
            logger.debug(f"Found {len(results)} articles matching '{query_text}'")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching articles: {e}")
            return []
    
    def article_exists(self, url: str) -> bool:
        """Check if an article with the given URL already exists
        
        Args:
            url: Article URL
            
        Returns:
            True if article exists, False otherwise
        """
        try:
            query = "SELECT id FROM research_articles WHERE url = %s LIMIT 1"
            results = self.client.execute_query(query, (url,))
            return len(results) > 0
        except Exception as e:
            logger.error(f"❌ Error checking if article exists: {e}")
            return False

