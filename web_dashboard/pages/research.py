#!/usr/bin/env python3
"""
Research Articles Viewer
========================

Streamlit page for viewing research articles collected by automated jobs.
Provides statistics, filtering, and detailed article views.
"""

import streamlit as st
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, date, timezone
import pandas as pd
import logging

# Try to import zoneinfo for timezone conversion (Python 3.9+)
try:
    from zoneinfo import ZoneInfo
    HAS_ZONEINFO = True
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
        HAS_ZONEINFO = True
    except ImportError:
        HAS_ZONEINFO = False

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, get_user_email
from navigation import render_navigation
from research_repository import ResearchRepository
from postgres_client import PostgresClient

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Research Articles",
    page_icon="📰",
    layout="wide"
)

# Hide Streamlit's default page navigation
st.markdown("""
    <style>
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# Check authentication
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Render navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Initialize repository (with error handling)
@st.cache_resource
def get_research_repository():
    """Get research repository instance, handling errors gracefully"""
    try:
        return ResearchRepository()
    except Exception as e:
        logger.error(f"Failed to initialize ResearchRepository: {e}")
        return None

repo = get_research_repository()

# Check if PostgreSQL is available
if repo is None:
    st.error("⚠️ Research Articles Database Unavailable")
    st.info("""
    The research articles database is not available. This could be because:
    - PostgreSQL is not running
    - RESEARCH_DATABASE_URL is not configured
    - Database connection failed
    
    Check the logs or contact an administrator for assistance.
    """)
    st.stop()

# Header
st.title("📰 Research Articles")
st.caption(f"Logged in as: {get_user_email()}")

# Initialize session state for filters
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

# Helper function to convert UTC to local timezone
def to_local_time(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to local timezone"""
    if utc_dt is None:
        return None
    if isinstance(utc_dt, str):
        utc_dt = datetime.fromisoformat(utc_dt.replace('Z', '+00:00'))
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
    
    # Convert to local timezone (user's system timezone)
    if HAS_ZONEINFO:
        try:
            # Get system timezone
            import time
            local_tz = ZoneInfo(time.tzname[0] if time.daylight == 0 else time.tzname[1])
            return utc_dt.astimezone(local_tz)
        except Exception:
            # Fallback to UTC if timezone detection fails
            return utc_dt
    else:
        # Fallback: just return UTC if zoneinfo not available
        return utc_dt

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")
    
    # Date range filter
    date_range_option = st.selectbox(
        "Date Range",
        ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=1
    )
    
    start_date = None
    end_date = None
    
    if date_range_option == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=date.today())
    else:
        days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[date_range_option]
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
    
    # Convert to datetime for query
    start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=None)
    end_datetime = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=None)
    
    # Article type filter
    article_type = st.selectbox(
        "Article Type",
        ["All", "market_news", "ticker_news", "earnings"],
        index=0
    )
    article_type_filter = None if article_type == "All" else article_type
    
    # Source filter
    selected_source = "All"
    try:
        sources = repo.get_unique_sources()
        source_options = ["All"] + sources
        selected_source = st.selectbox("Source", source_options, index=0)
        source_filter = None if selected_source == "All" else selected_source
    except Exception as e:
        logger.error(f"Error getting sources: {e}")
        source_filter = None
    
    # Search text filter
    search_text = st.text_input("🔍 Search", placeholder="Search in title, summary, content...")
    search_filter = search_text.strip() if search_text else None
    
    # Results per page
    results_per_page = st.selectbox("Results per page", [10, 20, 50, 100], index=1)
    
    st.markdown("---")
    
    # Reset pagination when filters change
    filter_key = f"{date_range_option}_{article_type}_{selected_source}_{search_filter or ''}"
    if 'last_filter_key' not in st.session_state or st.session_state.last_filter_key != filter_key:
        st.session_state.current_page = 1
        st.session_state.last_filter_key = filter_key
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.refresh_key += 1
        st.session_state.current_page = 1  # Reset to first page
        st.rerun()

# Main content area
try:
    # Get statistics
    with st.spinner("Loading statistics..."):
        stats = repo.get_article_statistics(days=90)
    
    # Statistics dashboard
    st.header("📊 Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Articles", stats.get('total_count', 0))
    
    with col2:
        type_counts = stats.get('by_type', {})
        market_news = type_counts.get('market_news', 0)
        st.metric("Market News", market_news)
    
    with col3:
        ticker_news = type_counts.get('ticker_news', 0)
        st.metric("Ticker News", ticker_news)
    
    with col4:
        earnings = type_counts.get('earnings', 0)
        st.metric("Earnings", earnings)
    
    # Charts
    col_chart1, col_chart2 = st.columns(2)
    
    with col_chart1:
        if stats.get('by_source'):
            source_data = stats['by_source']
            if source_data:
                source_df = pd.DataFrame(list(source_data.items()), columns=['Source', 'Count'])
                source_df = source_df.sort_values('Count', ascending=False).head(10)
                st.bar_chart(source_df.set_index('Source'))
                st.caption("Top 10 Sources")
    
    with col_chart2:
        if stats.get('by_day'):
            day_data = stats['by_day']
            if day_data:
                day_df = pd.DataFrame(list(day_data.items()), columns=['Date', 'Count'])
                day_df['Date'] = pd.to_datetime(day_df['Date'])
                day_df = day_df.sort_values('Date')
                st.line_chart(day_df.set_index('Date'))
                st.caption("Articles by Day (Last 90 days)")
    
    st.markdown("---")
    
    # Get filtered articles
    with st.spinner("Loading articles..."):
        # Calculate pagination
        page = st.session_state.get('current_page', 1)
        offset = (page - 1) * results_per_page
        
        articles = repo.get_articles_by_date_range(
            start_date=start_datetime,
            end_date=end_datetime,
            article_type=article_type_filter,
            source=source_filter,
            search_text=search_filter,
            limit=results_per_page,
            offset=offset
        )
        
        # Get total count for pagination (simplified - get one more to check if there are more)
        total_articles = len(articles)
        has_more = total_articles == results_per_page
    
    # Results header
    st.header("📄 Articles")
    
    if not articles:
        st.info("No articles found matching your filters. Try adjusting your search criteria.")
    else:
        # Pagination controls
        col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
        with col_pag1:
            if page > 1:
                if st.button("◀ Previous"):
                    st.session_state.current_page = page - 1
                    st.rerun()
        with col_pag2:
            st.caption(f"Page {page} - Showing {len(articles)} articles")
        with col_pag3:
            if has_more:
                if st.button("Next ▶"):
                    st.session_state.current_page = page + 1
                    st.rerun()
        
        # Export button
        if st.button("📥 Export to CSV", use_container_width=False):
            # Get all matching articles (without pagination) for export
            export_articles = repo.get_articles_by_date_range(
                start_date=start_datetime,
                end_date=end_datetime,
                article_type=article_type_filter,
                source=source_filter,
                search_text=search_filter,
                limit=10000,  # Large limit for export
                offset=0
            )
            
            if export_articles:
                # Prepare DataFrame
                export_data = []
                for article in export_articles:
                    export_data.append({
                        'Title': article.get('title', ''),
                        'Source': article.get('source', ''),
                        'Type': article.get('article_type', ''),
                        'Published': article.get('published_at', ''),
                        'Fetched': article.get('fetched_at', ''),
                        'URL': article.get('url', ''),
                        'Summary': article.get('summary', '')[:500] if article.get('summary') else '',
                        'Ticker': article.get('ticker', ''),
                        'Sector': article.get('sector', ''),
                        'Relevance Score': article.get('relevance_score', '')
                    })
                
                df_export = pd.DataFrame(export_data)
                csv = df_export.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"research_articles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("No articles to export")
        
        st.markdown("---")
        
        # Display articles
        for idx, article in enumerate(articles):
            with st.expander(
                f"**{article.get('title', 'Untitled')}** | {article.get('source', 'Unknown')} | {article.get('article_type', 'N/A')}",
                expanded=False
            ):
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write("**Source:**", article.get('source', 'N/A'))
                    st.write("**Type:**", article.get('article_type', 'N/A'))
                    if article.get('ticker'):
                        st.write("**Ticker:**", article.get('ticker'))
                    if article.get('sector'):
                        st.write("**Sector:**", article.get('sector'))
                
                with col_info2:
                    if article.get('published_at'):
                        pub_date = article['published_at']
                        if isinstance(pub_date, str):
                            pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        pub_date_local = to_local_time(pub_date)
                        st.write("**Published:**", pub_date_local.strftime('%Y-%m-%d %H:%M:%S'))
                    
                    if article.get('fetched_at'):
                        fetch_date = article['fetched_at']
                        if isinstance(fetch_date, str):
                            fetch_date = datetime.fromisoformat(fetch_date.replace('Z', '+00:00'))
                        fetch_date_local = to_local_time(fetch_date)
                        st.write("**Fetched:**", fetch_date_local.strftime('%Y-%m-%d %H:%M:%S'))
                    
                    if article.get('relevance_score'):
                        st.write("**Relevance:**", f"{article['relevance_score']:.2f}")
                
                # URL link
                if article.get('url'):
                    st.link_button("🔗 Open Original Article", article['url'], use_container_width=True)
                
                st.markdown("---")
                
                # Summary
                if article.get('summary'):
                    st.subheader("Summary")
                    st.write(article['summary'])
                
                # Content (if available and different from summary)
                if article.get('content') and article.get('content') != article.get('summary'):
                    with st.expander("📄 Full Content", expanded=False):
                        st.write(article['content'])
                
                if idx < len(articles) - 1:
                    st.markdown("---")

except Exception as e:
    logger.error(f"Error loading research articles: {e}", exc_info=True)
    st.error(f"❌ Error loading articles: {e}")
    st.info("Please try refreshing the page or contact an administrator if the problem persists.")

