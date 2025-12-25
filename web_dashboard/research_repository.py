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
                    ON CONFLICT (url) DO NOTHING
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
                    ON CONFLICT (url) DO NOTHING
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
            
            # Note: RealDictCursor already returns TIMESTAMP columns as datetime objects
            for article in results:
                if article.get('published_at') and isinstance(article['published_at'], datetime):
                    if article['published_at'].tzinfo is None:
                        article['published_at'] = article['published_at'].replace(tzinfo=timezone.utc)
                if article.get('fetched_at') and isinstance(article['fetched_at'], datetime):
                    if article['fetched_at'].tzinfo is None:
                        article['fetched_at'] = article['fetched_at'].replace(tzinfo=timezone.utc)
            
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
            
            # Note: RealDictCursor already returns TIMESTAMP columns as datetime objects
            for article in results:
                if article.get('published_at') and isinstance(article['published_at'], datetime):
                    if article['published_at'].tzinfo is None:
                        article['published_at'] = article['published_at'].replace(tzinfo=timezone.utc)
                if article.get('fetched_at') and isinstance(article['fetched_at'], datetime):
                    if article['fetched_at'].tzinfo is None:
                        article['fetched_at'] = article['fetched_at'].replace(tzinfo=timezone.utc)
            
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
            
            # Note: RealDictCursor already returns TIMESTAMP columns as datetime objects
            for article in results:
                if article.get('published_at') and isinstance(article['published_at'], datetime):
                    if article['published_at'].tzinfo is None:
                        article['published_at'] = article['published_at'].replace(tzinfo=timezone.utc)
                if article.get('fetched_at') and isinstance(article['fetched_at'], datetime):
                    if article['fetched_at'].tzinfo is None:
                        article['fetched_at'] = article['fetched_at'].replace(tzinfo=timezone.utc)
            
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
    
    def get_article_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get statistics about articles
        
        Args:
            days: Number of days to look back for statistics
            
        Returns:
            Dictionary with statistics:
            - total_count: Total number of articles
            - by_type: Count by article_type
            - by_source: Count by source
            - by_day: Count by day (last N days)
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            stats = {}
            
            # Total count
            total_result = self.client.execute_query("SELECT COUNT(*) as count FROM research_articles")
            stats['total_count'] = total_result[0]['count'] if total_result else 0
            
            # Count by type
            type_result = self.client.execute_query("""
                SELECT article_type, COUNT(*) as count
                FROM research_articles
                GROUP BY article_type
                ORDER BY count DESC
            """)
            stats['by_type'] = {row['article_type']: row['count'] for row in type_result} if type_result else {}
            
            # Count by source
            source_result = self.client.execute_query("""
                SELECT source, COUNT(*) as count
                FROM research_articles
                WHERE source IS NOT NULL
                GROUP BY source
                ORDER BY count DESC
            """)
            stats['by_source'] = {row['source']: row['count'] for row in source_result} if source_result else {}
            
            # Count by day (last N days)
            day_result = self.client.execute_query("""
                SELECT DATE(fetched_at) as day, COUNT(*) as count
                FROM research_articles
                WHERE fetched_at >= %s
                GROUP BY DATE(fetched_at)
                ORDER BY day DESC
            """, (cutoff_date.isoformat(),))
            stats['by_day'] = {str(row['day']): row['count'] for row in day_result} if day_result else {}
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Error getting article statistics: {e}")
            return {
                'total_count': 0,
                'by_type': {},
                'by_source': {},
                'by_day': {}
            }
    
    def get_unique_sources(self) -> List[str]:
        """Get list of all unique sources
        
        Returns:
            List of unique source names, sorted alphabetically
        """
        try:
            result = self.client.execute_query("""
                SELECT DISTINCT source
                FROM research_articles
                WHERE source IS NOT NULL
                ORDER BY source
            """)
            return [row['source'] for row in result] if result else []
        except Exception as e:
            logger.error(f"❌ Error getting unique sources: {e}")
            return []
    
    def get_articles_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        article_type: Optional[str] = None,
        source: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get articles within a date range with optional filters
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            article_type: Optional filter by article type
            source: Optional filter by source
            search_text: Optional text search in title, summary, content
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of article dictionaries
        """
        try:
            # Ensure timezone-aware datetimes
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            query = """
                SELECT id, ticker, sector, article_type, title, url, summary, content,
                       source, published_at, fetched_at, relevance_score
                FROM research_articles
                WHERE fetched_at >= %s AND fetched_at <= %s
            """
            # Convert to ISO format strings for PostgreSQL
            params = [start_date.isoformat(), end_date.isoformat()]
            
            if article_type:
                query += " AND article_type = %s"
                params.append(article_type)
            
            if source:
                query += " AND source = %s"
                params.append(source)
            
            if search_text:
                query += " AND (title ILIKE %s OR summary ILIKE %s OR content ILIKE %s)"
                search_pattern = f"%{search_text}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += " ORDER BY fetched_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            results = self.client.execute_query(query, tuple(params))
            
            # Note: RealDictCursor already returns TIMESTAMP columns as datetime objects
            # so no conversion is needed. Just ensure timezone awareness if needed.
            for article in results:
                if article.get('published_at') and isinstance(article['published_at'], datetime):
                    if article['published_at'].tzinfo is None:
                        article['published_at'] = article['published_at'].replace(tzinfo=timezone.utc)
                if article.get('fetched_at') and isinstance(article['fetched_at'], datetime):
                    if article['fetched_at'].tzinfo is None:
                        article['fetched_at'] = article['fetched_at'].replace(tzinfo=timezone.utc)
            
            logger.debug(f"Retrieved {len(results)} articles for date range")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting articles by date range: {e}")
            return []
    
    def get_all_articles(
        self,
        article_type: Optional[str] = None,
        source: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all articles without date filtering
        
        Args:
            article_type: Optional filter by article type
            source: Optional filter by source
            search_text: Optional text search in title, summary, content
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of article dictionaries
        """
        try:
            query = """
                SELECT id, ticker, sector, article_type, title, url, summary, content,
                       source, published_at, fetched_at, relevance_score
                FROM research_articles
                WHERE 1=1
            """
            params = []
            
            if article_type:
                query += " AND article_type = %s"
                params.append(article_type)
            
            if source:
                query += " AND source = %s"
                params.append(source)
            
            if search_text:
                query += " AND (title ILIKE %s OR summary ILIKE %s OR content ILIKE %s)"
                search_pattern = f"%{search_text}%"
                params.extend([search_pattern, search_pattern, search_pattern])
            
            query += " ORDER BY fetched_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            results = self.client.execute_query(query, tuple(params))
            
            # Note: RealDictCursor already returns TIMESTAMP columns as datetime objects
            # so no conversion is needed. Just ensure timezone awareness if needed.
            for article in results:
                if article.get('published_at') and isinstance(article['published_at'], datetime):
                    if article['published_at'].tzinfo is None:
                        article['published_at'] = article['published_at'].replace(tzinfo=timezone.utc)
                if article.get('fetched_at') and isinstance(article['fetched_at'], datetime):
                    if article['fetched_at'].tzinfo is None:
                        article['fetched_at'] = article['fetched_at'].replace(tzinfo=timezone.utc)
            
            logger.debug(f"Retrieved {len(results)} articles (all time)")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting all articles: {e}")
            return []
