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
import time

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

from auth_utils import is_authenticated, get_user_email, is_admin
from navigation import render_navigation
from research_repository import ResearchRepository
from postgres_client import PostgresClient
from ollama_client import get_ollama_client, check_ollama_health
from settings import get_summarizing_model

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

# Initialize reanalysis model (default to current summarizing model)
if 'reanalysis_model' not in st.session_state:
    st.session_state.reanalysis_model = get_summarizing_model()

# Re-analysis function
def reanalyze_article(article_id: str, model_name: str) -> tuple[bool, str]:
    """Re-analyze an article with a specified AI model.
    
    Args:
        article_id: UUID of the article to re-analyze
        model_name: Name of the Ollama model to use
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Check repository is available
        if repo is None:
            return False, "Research repository is not available"
        
        # Check Ollama availability
        if not check_ollama_health():
            return False, "Ollama is not available. Please check the connection."
        
        # Get article from repository
        query = """
            SELECT id, title, content, ticker, sector
            FROM research_articles
            WHERE id = %s
        """
        articles = repo.client.execute_query(query, (article_id,))
        
        if not articles:
            return False, "Article not found"
        
        article = articles[0]
        content = article.get('content', '')
        
        if not content:
            return False, "Article has no content to analyze"
        
        # Initialize Ollama client
        ollama_client = get_ollama_client()
        if not ollama_client:
            return False, "Failed to initialize Ollama client"
        
        # Generate summary with specified model
        summary_data = ollama_client.generate_summary(content, model=model_name)
        
        if not summary_data:
            return False, "Failed to generate summary"
        
        # Extract summary text
        extracted_tickers = []
        extracted_sector = None
        if isinstance(summary_data, str):
            summary = summary_data
        elif isinstance(summary_data, dict):
            summary = summary_data.get("summary", "")
            tickers = summary_data.get("tickers", [])
            sectors = summary_data.get("sectors", [])
            
            # Extract all validated tickers
            extracted_tickers = []
            if tickers:
                from research_utils import validate_ticker_in_content
                for ticker in tickers:
                    if validate_ticker_in_content(ticker, content):
                        extracted_tickers.append(ticker)
                    else:
                        logger.warning(f"Extracted ticker {ticker} not found in article content - skipping ticker assignment")
            
            extracted_sector = sectors[0] if sectors else None
        else:
            return False, "Invalid summary data format"
        
        if not summary:
            return False, "Generated summary is empty"
        
        # Get owned tickers for relevance scoring
        owned_tickers = []
        try:
            from supabase_client import SupabaseClient
            client = SupabaseClient(use_service_role=True)
            from settings import get_production_funds
            prod_funds = get_production_funds()
            positions_result = client.supabase.table("latest_positions")\
                .select("ticker")\
                .in_("fund", prod_funds)\
                .execute()
            if positions_result.data:
                owned_tickers = [pos['ticker'] for pos in positions_result.data if pos.get('ticker')]
        except Exception as e:
            logger.warning(f"Could not fetch owned tickers for relevance scoring: {e}")
        
        # Calculate relevance_score based on what was extracted
        from scheduler.jobs import calculate_relevance_score
        calculated_relevance = calculate_relevance_score(extracted_tickers, extracted_sector, owned_tickers=owned_tickers)
        
        # Generate embedding
        embedding = ollama_client.generate_embedding(content[:6000])
        if not embedding:
            logger.warning(f"Failed to generate embedding for article {article_id}, continuing without embedding")
            embedding = None
        
        # Update article in database
        success = repo.update_article_analysis(
            article_id=article_id,
            summary=summary,
            tickers=extracted_tickers if extracted_tickers else None,
            sector=extracted_sector,
            embedding=embedding,
            relevance_score=calculated_relevance
        )
        
        if success:
            return True, f"Article re-analyzed successfully with {model_name}"
        else:
            return False, "Failed to update article in database"
            
    except Exception as e:
        logger.error(f"Error re-analyzing article {article_id}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"

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
        ["All time", "Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=0
    )
    
    start_date = None
    end_date = None
    use_date_filter = True
    
    if date_range_option == "All time":
        use_date_filter = False
        # Set wide range for query (but won't be used)
        start_date = date.today() - timedelta(days=3650)  # 10 years ago
        end_date = date.today() + timedelta(days=1)  # Tomorrow
    elif date_range_option == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", value=date.today() - timedelta(days=30))
        with col2:
            end_date = st.date_input("End Date", value=date.today())
    else:
        days = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}[date_range_option]
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
    
    # Convert to datetime for query (use UTC timezone)
    if use_date_filter:
        # Start of day in UTC
        start_datetime = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        # End of day in UTC - use start of next day for inclusive end
        end_datetime = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc)
    else:
        # For "All time", use None to skip date filtering
        start_datetime = None
        end_datetime = None
    
    # Article type filter
    article_type = st.selectbox(
        "Article Type",
        ["All", "market_news", "ticker_news", "earnings", "opportunity_discovery"],
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
    
    # Embedding status filter (for RAG)
    embedding_status = st.selectbox(
        "Embedding Status",
        ["All", "Embedded", "Pending"],
        index=0,
        help="Filter by whether articles have been embedded for AI search (RAG)"
    )
    embedding_filter = None if embedding_status == "All" else (embedding_status == "Embedded")
    
    # Results per page
    results_per_page = st.selectbox("Results per page", [10, 20, 50, 100], index=1)
    
    # Admin-only: Model selector for re-analysis
    if is_admin():
        st.markdown("---")
        st.header("🔧 Admin Tools")
        
        from ollama_client import list_available_models
        
        if check_ollama_health():
            try:
                models = list_available_models()
                if models:
                    # Get current default model
                    default_model = get_summarizing_model()
                    
                    # Ensure default model is in the list
                    if default_model not in models:
                        model_options = [default_model] + models
                        default_index = 0
                    else:
                        model_options = models
                        default_index = model_options.index(default_model) if default_model in model_options else 0
                    
                    selected_model = st.selectbox(
                        "Re-Analysis Model",
                        options=model_options,
                        index=default_index,
                        help="Select AI model to use when re-analyzing articles (default: current summarizing model)",
                        key="admin_reanalysis_model"
                    )
                    st.session_state.reanalysis_model = selected_model
                else:
                    st.warning("No models available. Pull a model first (e.g., `ollama pull llama3`)")
                    st.session_state.reanalysis_model = get_summarizing_model()
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                st.error(f"Error loading models: {e}")
                st.session_state.reanalysis_model = get_summarizing_model()
        else:
            st.warning("Ollama not available")
            st.session_state.reanalysis_model = get_summarizing_model()
    
    st.markdown("---")
    
    # Reset pagination when filters change
    filter_key = f"{date_range_option}_{article_type}_{selected_source}_{search_filter or ''}_{embedding_status}"
    if 'last_filter_key' not in st.session_state or st.session_state.last_filter_key != filter_key:
        st.session_state.current_page = 1
        st.session_state.last_filter_key = filter_key
    
    # Refresh button
    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.refresh_key += 1
        st.session_state.current_page = 1  # Reset to first page
        st.rerun()

# Cached data fetching functions
@st.cache_data(ttl=60, show_spinner=False)
def get_cached_statistics(_repo, refresh_key: int):
    """Get article statistics with caching (60s TTL)"""
    return _repo.get_article_statistics(days=90)

@st.cache_data(ttl=60, show_spinner=False)
def get_cached_embedding_stats(_repo, refresh_key: int):
    """Get embedding statistics with caching (60s TTL)"""
    try:
        embedding_stats_query = "SELECT COUNT(*) as total, COUNT(embedding) as embedded FROM research_articles"
        result = _repo.client.execute_query(embedding_stats_query)
        if result:
            return result[0]['total'], result[0]['embedded']
        return 0, 0
    except Exception:
        return 0, 0

@st.cache_data(ttl=30, show_spinner=False)
def get_cached_articles(
    _repo,
    refresh_key: int,
    use_date_filter: bool,
    start_datetime_str: str,
    end_datetime_str: str,
    article_type_filter: str,
    source_filter: str,
    search_filter: str,
    embedding_filter: bool,
    results_per_page: int,
    offset: int
):
    """Get articles with caching (30s TTL for fresher data during active use)"""
    try:
        if use_date_filter and start_datetime_str and end_datetime_str:
            start_dt = datetime.fromisoformat(start_datetime_str)
            end_dt = datetime.fromisoformat(end_datetime_str)
            articles = _repo.get_articles_by_date_range(
                start_date=start_dt,
                end_date=end_dt,
                article_type=article_type_filter if article_type_filter else None,
                source=source_filter if source_filter else None,
                search_text=search_filter if search_filter else None,
                embedding_filter=embedding_filter,
                limit=results_per_page,
                offset=offset
            )
        else:
            articles = _repo.get_all_articles(
                article_type=article_type_filter if article_type_filter else None,
                source=source_filter if source_filter else None,
                search_text=search_filter if search_filter else None,
                embedding_filter=embedding_filter,
                limit=results_per_page,
                offset=offset
            )
        return articles
    except Exception as e:
        logger.error(f"Error fetching articles: {e}", exc_info=True)
        return []

# Main content area
try:
    # Get statistics (cached)
    with st.spinner("Loading statistics..."):
        stats = get_cached_statistics(repo, st.session_state.refresh_key)
    
    # Statistics dashboard
    st.header("📊 Statistics")
    
    # Get embedding statistics (cached)
    total_articles, embedded_articles = get_cached_embedding_stats(repo, st.session_state.refresh_key)
    embedding_pct = (embedded_articles / total_articles * 100) if total_articles > 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Articles", total_articles)
    
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
    
    with col5:
        st.metric("Embedded (RAG)", f"{embedded_articles}", delta=f"{embedding_pct:.0f}%")
    
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
    
    # Get filtered articles (cached)
    with st.spinner("Loading articles..."):
        # Calculate pagination
        page = st.session_state.get('current_page', 1)
        offset = (page - 1) * results_per_page
        
        # Convert datetime to ISO string for cache key (or empty string if None)
        start_dt_str = start_datetime.isoformat() if start_datetime else ""
        end_dt_str = end_datetime.isoformat() if end_datetime else ""
        
        articles = get_cached_articles(
            repo,
            st.session_state.refresh_key,
            use_date_filter,
            start_dt_str,
            end_dt_str,
            article_type_filter or "",
            source_filter or "",
            search_filter or "",
            embedding_filter,
            results_per_page,
            offset
        )
        
        # Get total count for pagination (simplified - get one more to check if there are more)
        article_count = len(articles)
        has_more = article_count == results_per_page
    
    # Results header
    st.header("📄 Articles")
    
    if not articles:
        st.info("No articles found matching your filters. Try adjusting your search criteria.")
    else:
        # Initialize selected articles in session state
        if 'selected_articles' not in st.session_state:
            st.session_state.selected_articles = set()
        
        # Admin batch actions section
        if is_admin():
            st.markdown("### Batch Actions")
            col_batch1, col_batch2, col_batch3 = st.columns([1, 1, 2])
            
            with col_batch1:
                # Select All checkbox
                select_all = st.checkbox("Select All", key="select_all_checkbox")
                if select_all:
                    # Select all articles on current page
                    st.session_state.selected_articles.update([article['id'] for article in articles])
                else:
                    # Deselect all articles on current page
                    current_page_ids = {article['id'] for article in articles}
                    st.session_state.selected_articles = st.session_state.selected_articles - current_page_ids
            
            with col_batch2:
                selected_count = len([aid for aid in st.session_state.selected_articles if any(a['id'] == aid for a in articles)])
                st.caption(f"Selected: {selected_count} on this page")
            
            with col_batch3:
                # Batch re-analyze button
                if st.button("🔄 Re-Analyze Selected", key="batch_reanalyze", type="primary", use_container_width=True):
                    # Get model from session state
                    model = st.session_state.get('reanalysis_model', get_summarizing_model())
                    
                    # Get all selected article IDs that are in current articles
                    selected_ids = [aid for aid in st.session_state.selected_articles if any(a['id'] == aid for a in articles)]
                    
                    if not selected_ids:
                        st.warning("No articles selected. Please select articles using the checkboxes.")
                    else:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        success_count = 0
                        error_count = 0
                        
                        for idx, article_id in enumerate(selected_ids):
                            # Find article title for status
                            article_title = next((a.get('title', 'Article') for a in articles if a['id'] == article_id), 'Article')
                            status_text.text(f"Re-analyzing: {article_title[:50]}... ({idx + 1}/{len(selected_ids)})")
                            
                            success, message = reanalyze_article(article_id, model)
                            
                            if success:
                                success_count += 1
                            else:
                                error_count += 1
                                logger.error(f"Failed to re-analyze {article_id}: {message}")
                            
                            # Update progress
                            progress_bar.progress((idx + 1) / len(selected_ids))
                            time.sleep(0.1)  # Small delay to show progress
                        
                        # Clear progress and show results
                        progress_bar.empty()
                        status_text.empty()
                        
                        if success_count > 0:
                            st.success(f"✅ Successfully re-analyzed {success_count} article(s)")
                            # Increment refresh key to invalidate cache
                            st.session_state.refresh_key += 1
                            # Clear selection
                            st.session_state.selected_articles = set()
                        
                        if error_count > 0:
                            st.error(f"❌ Failed to re-analyze {error_count} article(s)")
            
            st.markdown("---")
        
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
                        'Tickers': ', '.join(article.get('tickers', [])) if isinstance(article.get('tickers'), list) else (article.get('ticker', '') or ''),
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
            # Build title with embedding badge
            has_embedding = article.get('has_embedding', False)
            embedding_badge = "🧠 " if has_embedding else "⏳ "
            
            # Checkbox for selection (admin only)
            col_check, col_expander = st.columns([0.05, 0.95]) if is_admin() else (None, None)
            
            if is_admin():
                with col_check:
                    article_id = article['id']
                    is_selected = article_id in st.session_state.selected_articles
                    selected = st.checkbox(
                        "",
                        value=is_selected,
                        key=f"select_{article_id}",
                        label_visibility="collapsed"
                    )
                    if selected and not is_selected:
                        st.session_state.selected_articles.add(article_id)
                    elif not selected and is_selected:
                        st.session_state.selected_articles.discard(article_id)
                
                with col_expander:
                    expander_key = f"expander_{article_id}"
            else:
                expander_key = f"expander_{idx}"
            
            # Create expander with appropriate key
            expander_container = col_expander if is_admin() else st
            with expander_container.expander(
                f"{embedding_badge}**{article.get('title', 'Untitled')}** | {article.get('source', 'Unknown')} | {article.get('article_type', 'N/A')}",
                expanded=False,
                key=expander_key
            ):
                col_info1, col_info2 = st.columns(2)
                
                with col_info1:
                    st.write("**Source:**", article.get('source', 'N/A'))
                    st.write("**Type:**", article.get('article_type', 'N/A'))
                    # Handle both old ticker format and new tickers array format
                    tickers = article.get('tickers')
                    if tickers:
                        if isinstance(tickers, list):
                            st.write("**Tickers:**", ", ".join(tickers))
                        else:
                            st.write("**Tickers:**", str(tickers))
                    elif article.get('ticker'):  # Fallback for old format
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
                
                # Admin actions - wrapped in fragment for partial re-render
                if is_admin():
                    # Create a fragment for admin actions to avoid full page refresh
                    @st.fragment
                    def render_admin_actions(article_id: str, article_title: str, article_idx: int):
                        """Fragment for admin actions - only this section re-renders on button click"""
                        col_admin1, col_admin2 = st.columns(2)
                        
                        with col_admin1:
                            if st.button("🔄 Re-Analyze", key=f"reanalyze_{article_id}", type="primary", use_container_width=True):
                                # Get model from session state (default to current summarizing model if not set)
                                model = st.session_state.get('reanalysis_model', get_summarizing_model())
                                
                                with st.spinner(f"Re-analyzing with {model}..."):
                                    success, message = reanalyze_article(article_id, model)
                                    
                                    if success:
                                        st.success(f"✅ {message}")
                                        # Increment refresh key to invalidate article cache on next full page load
                                        st.session_state.refresh_key += 1
                                    else:
                                        st.error(f"❌ {message}")
                        
                        with col_admin2:
                            if st.button("🗑️ Delete", key=f"del_{article_id}", type="secondary", use_container_width=True):
                                if repo.delete_article(article_id):
                                    st.success(f"✅ Deleted: {article_title}")
                                    # Increment refresh key to invalidate article cache
                                    st.session_state.refresh_key += 1
                                else:
                                    st.error("❌ Failed to delete article")
                    
                    # Render the fragment for this article
                    render_admin_actions(article['id'], article.get('title', 'Article'), idx)
                
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

