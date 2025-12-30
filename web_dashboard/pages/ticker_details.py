#!/usr/bin/env python3
"""
Ticker Details Page
===================

Comprehensive ticker information page that aggregates data from all databases
and provides external links to financial websites.
"""

import streamlit as st
import sys
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime, timezone
import pandas as pd
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth_utils import is_authenticated, get_user_email
from navigation import render_navigation
from postgres_client import PostgresClient
from supabase_client import SupabaseClient
from ticker_utils import get_ticker_info, get_ticker_external_links

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Ticker Details",
    page_icon="📊",
    layout="wide"
)

# Check authentication
if not is_authenticated():
    st.switch_page("streamlit_app.py")
    st.stop()

# Refresh token if needed
from auth_utils import refresh_token_if_needed
if not refresh_token_if_needed():
    from auth_utils import logout_user
    logout_user()
    st.error("Your session has expired. Please log in again.")
    st.switch_page("streamlit_app.py")
    st.stop()

# Render navigation
render_navigation(show_ai_assistant=True, show_settings=True)

# Initialize clients
@st.cache_resource
def get_postgres_client():
    """Get Postgres client instance"""
    try:
        return PostgresClient()
    except Exception as e:
        logger.error(f"Failed to initialize PostgresClient: {e}")
        return None

@st.cache_resource
def get_supabase_client():
    """Get Supabase client instance"""
    try:
        return SupabaseClient(use_service_role=True)
    except Exception as e:
        logger.error(f"Failed to initialize SupabaseClient: {e}")
        return None

postgres_client = get_postgres_client()
supabase_client = get_supabase_client()

# Get ticker from query parameters
query_params = st.query_params
ticker = query_params.get("ticker", "")

# Ticker search box
col_search, col_spacer = st.columns([0.3, 0.7])
with col_search:
    search_ticker = st.text_input(
        "Search Ticker",
        value=ticker.upper() if ticker else "",
        placeholder="Enter ticker symbol (e.g., AAPL)",
        key="ticker_search"
    ).upper().strip()

# If user entered a new ticker, update query params
if search_ticker and search_ticker != ticker:
    st.query_params["ticker"] = search_ticker
    st.rerun()

# Use the ticker from query params or search
current_ticker = ticker.upper().strip() if ticker else search_ticker

if not current_ticker:
    st.title("📊 Ticker Details")
    st.info("Enter a ticker symbol above to view detailed information.")
    st.stop()

# Fetch ticker information
@st.cache_data(ttl=60)
def fetch_ticker_data(_ticker: str):
    """Fetch ticker data with caching"""
    # Get clients inside the cached function
    pg_client = get_postgres_client()
    sb_client = get_supabase_client()
    return get_ticker_info(_ticker, sb_client, pg_client)

# Check if clients are available
if not postgres_client and not supabase_client:
    st.error("⚠️ Unable to connect to databases. Please check your configuration.")
    st.stop()

# Helper function to format dates safely
def format_date_safe(date_val):
    """Safely format a date value that might be string or datetime"""
    if not date_val:
        return 'N/A'
    if isinstance(date_val, str):
        return date_val[:10]  # Return first 10 chars (YYYY-MM-DD)
    try:
        return date_val.strftime('%Y-%m-%d')  # Format datetime object
    except (AttributeError, ValueError):
        return str(date_val)[:10]

try:
    with st.spinner(f"Loading information for {current_ticker}..."):
        ticker_data = fetch_ticker_data(current_ticker)
except Exception as e:
    logger.error(f"Error fetching ticker data for {current_ticker}: {e}", exc_info=True)
    st.error(f"❌ Error loading ticker data: {str(e)}")
    st.info("Please try again or contact support if the problem persists.")
    st.stop()

# Header
st.title(f"📊 {current_ticker}")

# Wrap main content in try-except for better error handling
try:
    # Basic Info Section
    basic_info = ticker_data.get('basic_info')
if basic_info:
    company_name = basic_info.get('company_name', 'N/A')
    sector = basic_info.get('sector', 'N/A')
    industry = basic_info.get('industry', 'N/A')
    currency = basic_info.get('currency', 'USD')
    exchange = basic_info.get('exchange', 'N/A')
    
    st.header(f"{company_name}")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Sector", sector)
    with col2:
        st.metric("Industry", industry)
    with col3:
        st.metric("Currency", currency)
    
    if exchange != 'N/A':
        st.caption(f"Exchange: {exchange}")
else:
    st.info(f"Basic information not found for {current_ticker} in database.")

# External Links Section
st.header("🔗 External Links")
external_links = get_ticker_external_links(
    current_ticker,
    exchange=basic_info.get('exchange') if basic_info else None
)

# Display links in columns
cols = st.columns(4)
link_items = list(external_links.items())
for i, (name, url) in enumerate(link_items):
    with cols[i % 4]:
        st.markdown(f"[{name}]({url})")

st.markdown("---")

# Portfolio Data Section
portfolio_data = ticker_data.get('portfolio_data')
if portfolio_data and (portfolio_data.get('has_positions') or portfolio_data.get('has_trades')):
    st.header("💼 Portfolio Data")
    
    # Current Positions
    if portfolio_data.get('has_positions'):
        positions = portfolio_data.get('positions', [])
        if positions:
            st.subheader("Current Positions")
            # Get latest position for each fund
            latest_positions = {}
            for pos in positions:
                fund = pos.get('fund', 'Unknown')
                if fund not in latest_positions:
                    latest_positions[fund] = pos
                else:
                    # Keep the most recent
                    if pos.get('date', '') > latest_positions[fund].get('date', ''):
                        latest_positions[fund] = pos
            
            pos_df = pd.DataFrame([
                {
                    'Fund': pos.get('fund', 'N/A'),
                    'Shares': f"{pos.get('shares', 0):,.2f}",
                    'Price': f"${pos.get('price', 0):.2f}",
                    'Cost Basis': f"${pos.get('cost_basis', 0):.2f}",
                    'P&L': f"${pos.get('pnl', 0):.2f}",
                    'Date': pos.get('date', 'N/A')[:10] if pos.get('date') else 'N/A'
                }
                for pos in latest_positions.values()
            ])
            st.dataframe(pos_df, use_container_width=True, hide_index=True)
    
    # Trade History
    if portfolio_data.get('has_trades'):
        trades = portfolio_data.get('trades', [])
        if trades:
            st.subheader("Recent Trade History")
            trade_df = pd.DataFrame([
                {
                    'Date': trade.get('date', 'N/A')[:10] if trade.get('date') else 'N/A',
                    'Action': trade.get('action', 'N/A'),
                    'Shares': f"{trade.get('shares', 0):,.2f}",
                    'Price': f"${trade.get('price', 0):.2f}",
                    'Fund': trade.get('fund', 'N/A'),
                    'Reason': trade.get('reason', 'N/A')[:50] if trade.get('reason') else 'N/A'
                }
                for trade in trades[:20]  # Show last 20 trades
            ])
            st.dataframe(trade_df, use_container_width=True, hide_index=True)
else:
    st.info(f"No portfolio data found for {current_ticker}.")

st.markdown("---")

# Research Articles Section
research_articles = ticker_data.get('research_articles', [])
if research_articles:
    st.header("📚 Research Articles")
    st.caption(f"Found {len(research_articles)} articles mentioning {current_ticker} (last 30 days)")
    
    for article in research_articles[:10]:  # Show top 10
        with st.expander(f"{article.get('title', 'Untitled')[:80]}..."):
            col1, col2 = st.columns([3, 1])
            with col1:
                if article.get('summary'):
                    st.write(article.get('summary', '')[:500] + '...' if len(article.get('summary', '')) > 500 else article.get('summary', ''))
                if article.get('url'):
                    st.markdown(f"[Read Full Article]({article.get('url')})")
            with col2:
                st.caption(f"Source: {article.get('source', 'Unknown')}")
                if article.get('published_at'):
                    published_date = format_date_safe(article.get('published_at'))
                    st.caption(f"Published: {published_date}")
                if article.get('sentiment'):
                    st.caption(f"Sentiment: {article.get('sentiment', 'N/A')}")
else:
    st.info(f"No research articles found for {current_ticker} (last 30 days).")

st.markdown("---")

# Social Sentiment Section
social_sentiment = ticker_data.get('social_sentiment')
if social_sentiment:
    st.header("💬 Social Sentiment")
    
    latest_metrics = social_sentiment.get('latest_metrics', [])
    if latest_metrics:
        st.subheader("Latest Metrics")
        metrics_df = pd.DataFrame([
            {
                'Platform': metric.get('platform', 'N/A').title(),
                'Sentiment': metric.get('sentiment_label', 'N/A'),
                'Score': f"{metric.get('sentiment_score', 0):.2f}",
                'Volume': metric.get('volume', 0),
                'Bull/Bear Ratio': f"{metric.get('bull_bear_ratio', 0):.2f}" if metric.get('bull_bear_ratio') else 'N/A',
                'Last Updated': format_date_safe(metric.get('created_at')) if metric.get('created_at') else 'N/A'
            }
            for metric in latest_metrics
        ])
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)
    
    alerts = social_sentiment.get('alerts', [])
    if alerts:
        st.subheader("Recent Alerts (Last 24 Hours)")
        for alert in alerts:
            sentiment_label = alert.get('sentiment_label', 'N/A')
            if sentiment_label == 'EUPHORIC':
                st.success(f"**{alert.get('platform', 'Unknown').title()}** - {sentiment_label} (Score: {alert.get('sentiment_score', 0):.2f})")
            elif sentiment_label == 'FEARFUL':
                st.error(f"**{alert.get('platform', 'Unknown').title()}** - {sentiment_label} (Score: {alert.get('sentiment_score', 0):.2f})")
            elif sentiment_label == 'BULLISH':
                st.info(f"**{alert.get('platform', 'Unknown').title()}** - {sentiment_label} (Score: {alert.get('sentiment_score', 0):.2f})")
else:
    st.info(f"No social sentiment data available for {current_ticker}.")

st.markdown("---")

# Congress Trades Section
congress_trades = ticker_data.get('congress_trades', [])
if congress_trades:
    st.header("🏛️ Congress Trades")
    st.caption(f"Found {len(congress_trades)} recent trades by politicians (last 30 days)")
    
    trades_df = pd.DataFrame([
        {
            'Date': trade.get('transaction_date', 'N/A'),
            'Politician': trade.get('politician', 'N/A'),
            'Chamber': trade.get('chamber', 'N/A'),
            'Type': trade.get('type', 'N/A'),
            'Amount': trade.get('amount', 'N/A'),
            'Party': trade.get('party', 'N/A')
        }
        for trade in congress_trades[:20]  # Show last 20
    ])
    st.dataframe(trades_df, use_container_width=True, hide_index=True)
else:
    st.info(f"No congress trades found for {current_ticker} (last 30 days).")

st.markdown("---")

# Watchlist Status Section
watchlist_status = ticker_data.get('watchlist_status')
if watchlist_status:
    st.header("📋 Watchlist Status")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Status", "✅ In Watchlist" if watchlist_status.get('is_active') else "❌ Not Active")
    with col2:
        st.metric("Priority Tier", watchlist_status.get('priority_tier', 'N/A'))
    with col3:
        st.metric("Source", watchlist_status.get('source', 'N/A'))
else:
    st.info(f"{current_ticker} is not in the watchlist.")

except Exception as e:
    logger.error(f"Error rendering ticker details page for {current_ticker}: {e}", exc_info=True)
    st.error(f"❌ An error occurred while displaying ticker information: {str(e)}")
    st.info("Please try refreshing the page or contact support if the problem persists.")

# Footer
st.markdown("---")
st.caption(f"Data last updated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")

