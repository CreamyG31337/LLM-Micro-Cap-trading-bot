#!/usr/bin/env python3
"""
Social Sentiment Dashboard
===========================

Streamlit page for viewing social sentiment data from StockTwits and Reddit.
Displays latest sentiment per ticker and alerts for extreme sentiment.
"""

import streamlit as st
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone
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

from auth_utils import is_authenticated, get_user_email, is_admin
from navigation import render_navigation
from postgres_client import PostgresClient
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Social Sentiment",
    page_icon="💬",
    layout="wide"
)

# Check authentication
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Refresh token if needed (auto-refresh before expiry)
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    # Token refresh failed - session is invalid, redirect to login
    from auth_utils import logout_user
    logout_user()
    st.error("Your session has expired. Please log in again.")
    st.switch_page("streamlit_app.py")
    st.stop()

# Render navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Initialize Postgres client (with error handling)
@st.cache_resource
def get_postgres_client():
    """Get Postgres client instance, handling errors gracefully"""
    try:
        return PostgresClient()
    except Exception as e:
        logger.error(f"Failed to initialize PostgresClient: {e}")
        return None

# Initialize Supabase client (with error handling)
@st.cache_resource
def get_supabase_client():
    """Get Supabase client instance, handling errors gracefully"""
    try:
        return SupabaseClient(use_service_role=True)
    except Exception as e:
        logger.error(f"Failed to initialize SupabaseClient: {e}")
        return None

postgres_client = get_postgres_client()
supabase_client = get_supabase_client()

# Check if PostgreSQL is available
if postgres_client is None:
    st.error("⚠️ Social Sentiment Database Unavailable")
    st.info("""
    The social sentiment database is not available. This could be because:
    - PostgreSQL is not running
    - RESEARCH_DATABASE_URL is not configured
    - Database connection failed
    
    Check the logs or contact an administrator for assistance.
    """)
    st.stop()

# Header
st.title("💬 Social Sentiment")
st.caption(f"Logged in as: {get_user_email()}")

# Initialize session state for refresh
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0

# Query functions
@st.cache_data(ttl=60, show_spinner=False)
def get_watchlist_tickers(_supabase_client, _refresh_key: int) -> List[Dict[str, Any]]:
    """Get all active tickers from watched_tickers table
    
    Returns:
        List of dictionaries with ticker, priority_tier, source, etc.
    """
    try:
        if _supabase_client is None:
            return []
        result = _supabase_client.supabase.table("watched_tickers")\
            .select("ticker, priority_tier, is_active, source, created_at")\
            .eq("is_active", True)\
            .order("priority_tier, ticker")\
            .execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"Error fetching watchlist: {e}", exc_info=True)
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_latest_sentiment_per_ticker(_client, _refresh_key: int) -> List[Dict[str, Any]]:
    """Get the most recent sentiment metric for each ticker/platform combination
    
    Returns:
        List of dictionaries with sentiment data
    """
    try:
        query = """
            SELECT DISTINCT ON (ticker, platform)
                ticker, platform, volume, sentiment_label, sentiment_score, 
                bull_bear_ratio, created_at
            FROM social_metrics
            ORDER BY ticker, platform, created_at DESC
        """
        results = _client.execute_query(query)
        return results
    except Exception as e:
        logger.error(f"Error fetching latest sentiment: {e}", exc_info=True)
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_extreme_sentiment_alerts(_client, _refresh_key: int) -> List[Dict[str, Any]]:
    """Get EUPHORIC or FEARFUL sentiment alerts from last 24 hours
    
    Returns:
        List of dictionaries with extreme sentiment data
    """
    try:
        query = """
            SELECT ticker, platform, sentiment_label, sentiment_score, created_at
            FROM social_metrics
            WHERE sentiment_label IN ('EUPHORIC', 'FEARFUL')
              AND created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC
        """
        results = _client.execute_query(query)
        return results
    except Exception as e:
        logger.error(f"Error fetching extreme sentiment alerts: {e}", exc_info=True)
        return []

# Helper function to format datetime for display
def format_datetime(dt) -> str:
    """Format datetime for display in local timezone"""
    if dt is None:
        return "N/A"
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except (ValueError, AttributeError, TypeError):
            return dt
    
    if not isinstance(dt, datetime):
        return str(dt)
    
    # Convert to local timezone if available
    if HAS_ZONEINFO:
        try:
            local_tz = ZoneInfo("America/Los_Angeles")  # Adjust to your timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            local_dt = dt.astimezone(local_tz)
            return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
        except (ValueError, AttributeError, TypeError):
            pass
    
    return dt.strftime("%Y-%m-%d %H:%M:%S")

# Helper function to get sentiment color
def get_sentiment_color(label: Optional[str]) -> str:
    """Get color for sentiment label"""
    if not label:
        return "gray"
    
    label_upper = label.upper()
    color_map = {
        'EUPHORIC': 'green',
        'BULLISH': 'lightgreen',
        'NEUTRAL': 'gray',
        'BEARISH': 'lightcoral',
        'FEARFUL': 'red'
    }
    return color_map.get(label_upper, "gray")

# Main content area
try:
    # Refresh button
    col_refresh, col_spacer = st.columns([0.1, 0.9])
    with col_refresh:
        if st.button("🔄 Refresh", key="refresh_sentiment"):
            st.session_state.refresh_key += 1
            st.rerun()
    
    # Get watchlist (cached)
    watchlist_tickers = []
    if supabase_client:
        with st.spinner("Loading watchlist..."):
            watchlist_tickers = get_watchlist_tickers(supabase_client, st.session_state.refresh_key)
    
    # Get alerts (cached)
    with st.spinner("Loading alerts..."):
        alerts = get_extreme_sentiment_alerts(postgres_client, st.session_state.refresh_key)
    
    # Display Watchlist Section
    st.header("📋 Watchlist")
    
    if watchlist_tickers:
        watchlist_df = pd.DataFrame(watchlist_tickers)
        
        # Show watchlist summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Watchlist Tickers", len(watchlist_tickers))
        with col2:
            tier_a = len([t for t in watchlist_tickers if t.get('priority_tier') == 'A'])
            st.metric("Priority A", tier_a)
        with col3:
            tier_b = len([t for t in watchlist_tickers if t.get('priority_tier') == 'B'])
            st.metric("Priority B", tier_b)
        
        # Show watchlist table
        watchlist_display = pd.DataFrame([
            {
                'Ticker': t.get('ticker', 'N/A'),
                'Priority': t.get('priority_tier', 'B'),
                'Source': t.get('source', 'N/A')
            }
            for t in watchlist_tickers
        ])
        st.dataframe(watchlist_display, use_container_width=True, hide_index=True)
    else:
        if supabase_client is None:
            st.warning("⚠️ Supabase connection unavailable - cannot load watchlist")
        else:
            st.info("📭 No active tickers in watchlist. Run the migration `19_create_watchlist.sql` in Supabase to populate from trade_log.")
    
    st.markdown("---")
    
    # Display Alerts Section
    st.header("🚨 Extreme Sentiment Alerts")
    
    if alerts:
        for alert in alerts:
            ticker = alert.get('ticker', 'N/A')
            platform = alert.get('platform', 'N/A')
            sentiment_label = alert.get('sentiment_label', 'N/A')
            sentiment_score = alert.get('sentiment_score', 0.0)
            created_at = alert.get('created_at')
            time_str = format_datetime(created_at)
            
            if sentiment_label == 'EUPHORIC':
                st.success(
                    f"**{ticker}** ({platform.upper()}) - {sentiment_label} "
                    f"(Score: {sentiment_score:.1f}) - {time_str}"
                )
            elif sentiment_label == 'FEARFUL':
                st.error(
                    f"**{ticker}** ({platform.upper()}) - {sentiment_label} "
                    f"(Score: {sentiment_score:.1f}) - {time_str}"
                )
    else:
        st.info("✅ No extreme sentiment alerts in the last 24 hours")
    
    st.markdown("---")
    
    # Get latest sentiment data (cached)
    with st.spinner("Loading sentiment data..."):
        latest_sentiment = get_latest_sentiment_per_ticker(postgres_client, st.session_state.refresh_key)
    
    # Display Latest Sentiment Table
    st.header("📊 Latest Sentiment by Ticker")
    
    # Show last refresh timestamp
    if latest_sentiment:
        newest_timestamp = max((row.get('created_at') for row in latest_sentiment), default=None)
        if newest_timestamp:
            st.caption(f"📅 Data last updated: {format_datetime(newest_timestamp)}")
    
    if not latest_sentiment:
        st.info("""
        📭 No social sentiment data available yet.
        
        Data is collected every 30 minutes by the automated scheduler. 
        Check back soon or ensure the `social_sentiment` job is running.
        """)
        st.stop()
    
    # Create watchlist ticker set for filtering
    watchlist_ticker_set = set([t.get('ticker') for t in watchlist_tickers]) if watchlist_tickers else set()
    
    # Filter option
    show_only_watchlist = st.checkbox("Show only watchlist tickers", value=True)
    
    # Batch fetch company names for all unique tickers
    unique_tickers = list(set([row.get('ticker') for row in latest_sentiment if row.get('ticker')]))
    company_names_map = {}
    
    if supabase_client and unique_tickers:
        try:
            # Batch query company names from securities table
            # Query in chunks of 50 (Supabase limit)
            for i in range(0, len(unique_tickers), 50):
                ticker_batch = unique_tickers[i:i+50]
                result = supabase_client.supabase.table("securities")\
                    .select("ticker, company_name")\
                    .in_("ticker", ticker_batch)\
                    .execute()
                
                if result.data:
                    for item in result.data:
                        ticker = item.get('ticker', '').upper()
                        company_name = item.get('company_name', '')
                        if company_name and company_name.strip() and company_name != 'Unknown':
                            company_names_map[ticker] = company_name.strip()
        except Exception as e:
            logger.warning(f"Error fetching company names: {e}")
    
    # Prepare DataFrame
    df_data = []
    for row in latest_sentiment:
        ticker = row.get('ticker', 'N/A')
        platform = row.get('platform', 'N/A')
        volume = row.get('volume', 0)
        sentiment_label = row.get('sentiment_label', 'N/A')
        sentiment_score = row.get('sentiment_score')
        bull_bear_ratio = row.get('bull_bear_ratio')
        created_at = row.get('created_at')
        
        # Check if ticker is in watchlist
        in_watchlist = ticker in watchlist_ticker_set
        
        # Filter if requested
        if show_only_watchlist and not in_watchlist:
            continue
        
        # Get company name
        ticker_upper = ticker.upper()
        company_name = company_names_map.get(ticker_upper, 'N/A')
        
        # Platform icons
        platform_icons = {'stocktwits': '📊', 'reddit': '🤖'}
        platform_display = f"{platform_icons.get(platform, '❓')} {platform.upper()}"
        
        df_data.append({
            'Ticker': ticker,
            'Company': company_name,
            'In Watchlist': '✅' if in_watchlist else '❌',
            'Platform': platform_display,
            'Volume': volume,
            'Sentiment': sentiment_label if sentiment_label else 'N/A',
            'Score': f"{sentiment_score:.1f}" if sentiment_score is not None else "N/A",
            'Bull/Bear Ratio': f"{bull_bear_ratio:.2f}" if bull_bear_ratio is not None and platform == 'stocktwits' else "N/A",
            'Last Updated': format_datetime(created_at)
        })
    
    df = pd.DataFrame(df_data)
    
    if df.empty:
        if show_only_watchlist:
            st.info("📭 No sentiment data available for watchlist tickers yet. The scheduler will collect data for these tickers every 30 minutes.")
        else:
            st.info("📭 No sentiment data available.")
        st.stop()
    
    # Sort by ticker and platform
    df = df.sort_values(['Ticker', 'Platform'])
    
    # Define sentiment color styling function
    def style_sentiment(val):
        """Apply background color based on sentiment"""
        if val in ['EUPHORIC', 'BULLISH', 'NEUTRAL', 'BEARISH', 'FEARFUL']:
            color = get_sentiment_color(val)
            # Use white text for better contrast
            return f'background-color: {color}; color: white; font-weight: bold;'
        return ''
    
    # Display dataframe with styling
    st.dataframe(
        df.style.applymap(style_sentiment, subset=['Sentiment']),
        use_container_width=True,
        hide_index=True
    )
    
    # Show summary statistics
    st.markdown("---")
    st.subheader("📈 Summary Statistics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_tickers = len(set(df['Ticker'].unique()))
        st.metric("Unique Tickers", total_tickers)
    
    with col2:
        total_metrics = len(df)
        st.metric("Total Metrics", total_metrics)
    
    with col3:
        euphoric_count = len(df[df['Sentiment'] == 'EUPHORIC'])
        st.metric("Euphoric", euphoric_count)
    
    with col4:
        fearful_count = len(df[df['Sentiment'] == 'FEARFUL'])
        st.metric("Fearful", fearful_count)

except Exception as e:
    logger.error(f"Error in social sentiment page: {e}", exc_info=True)
    st.error(f"❌ An error occurred: {str(e)}")
    st.info("Please check the logs or contact an administrator.")

