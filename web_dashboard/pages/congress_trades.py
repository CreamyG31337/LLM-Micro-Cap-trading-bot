#!/usr/bin/env python3
"""
Congress Trades Viewer
======================

Streamlit page for viewing congressional stock trading disclosures.
Displays trades with filtering, sorting, and summary statistics.
"""

import streamlit as st
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone, date
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
from supabase_client import SupabaseClient
from user_preferences import get_user_timezone

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Congress Trades",
    page_icon="🏛️",
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

# Initialize Supabase client (with error handling)
@st.cache_resource
def get_supabase_client():
    """Get Supabase client instance, handling errors gracefully"""
    try:
        return SupabaseClient(use_service_role=True)
    except Exception as e:
        logger.error(f"Failed to initialize SupabaseClient: {e}")
        return None

supabase_client = get_supabase_client()

# Check if Supabase is available
if supabase_client is None:
    st.error("⚠️ Congress Trades Database Unavailable")
    st.info("""
    The congress trades database is not available. This could be because:
    - Supabase is not configured
    - SUPABASE_URL or SUPABASE_SECRET_KEY is not set
    - Database connection failed
    
    Check the logs or contact an administrator for assistance.
    """)
    st.stop()

# Header
st.title("🏛️ Congress Trades")
st.caption(f"Logged in as: {get_user_email()}")

# Initialize session state for refresh
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0

# Query functions
@st.cache_data(ttl=60, show_spinner=False)
def get_unique_tickers(_supabase_client, _refresh_key: int) -> List[str]:
    """Get all unique tickers from congress_trades table"""
    try:
        if _supabase_client is None:
            return []
        # Use a simple query to get distinct tickers
        # Supabase doesn't support DISTINCT directly, so we'll fetch all and deduplicate
        result = _supabase_client.supabase.table("congress_trades")\
            .select("ticker")\
            .limit(10000)\
            .execute()
        
        if result.data:
            tickers = sorted(set([t.get('ticker') for t in result.data if t.get('ticker')]))
            return tickers
        return []
    except Exception as e:
        logger.error(f"Error fetching unique tickers: {e}", exc_info=True)
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_unique_politicians(_supabase_client, _refresh_key: int) -> List[str]:
    """Get all unique politicians from congress_trades table"""
    try:
        if _supabase_client is None:
            return []
        result = _supabase_client.supabase.table("congress_trades")\
            .select("politician")\
            .limit(10000)\
            .execute()
        
        if result.data:
            politicians = sorted(set([p.get('politician') for p in result.data if p.get('politician')]))
            return politicians
        return []
    except Exception as e:
        logger.error(f"Error fetching unique politicians: {e}", exc_info=True)
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_congress_trades(
    _supabase_client,
    _refresh_key: int,
    ticker_filter: Optional[str] = None,
    politician_filter: Optional[str] = None,
    chamber_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[Dict[str, Any]]:
    """Get congress trades with filters
    
    Returns:
        List of dictionaries with trade data
    """
    try:
        if _supabase_client is None:
            return []
        
        # Build query with filters
        query = _supabase_client.supabase.table("congress_trades").select("*")
        
        # Apply filters
        if ticker_filter:
            query = query.eq("ticker", ticker_filter)
        if politician_filter:
            query = query.eq("politician", politician_filter)
        if chamber_filter:
            query = query.eq("chamber", chamber_filter)
        if type_filter:
            query = query.eq("type", type_filter)
        if start_date:
            query = query.gte("transaction_date", start_date.isoformat())
        if end_date:
            query = query.lte("transaction_date", end_date.isoformat())
        
        # Order by transaction_date DESC (most recent first)
        query = query.order("transaction_date", desc=True)
        
        # Paginate to handle large datasets (Supabase limit is 1000 per request)
        all_trades = []
        batch_size = 1000
        offset = 0
        
        while True:
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            all_trades.extend(result.data)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops (max 50k rows = 50 batches)
            if offset > 50000:
                logger.warning("Reached 50,000 row safety limit in get_congress_trades pagination")
                break
        
        return all_trades
    except Exception as e:
        logger.error(f"Error fetching congress trades: {e}", exc_info=True)
        return []

# Helper function to format date for display
def format_date(d) -> str:
    """Format date for display"""
    if d is None:
        return "N/A"
    
    if isinstance(d, str):
        try:
            # Try parsing ISO format date string
            d = datetime.fromisoformat(d.split('T')[0]).date()
        except (ValueError, AttributeError, TypeError):
            return d
    
    if isinstance(d, date):
        return d.strftime("%Y-%m-%d")
    
    return str(d)

# Helper function to format price
def format_price(price) -> str:
    """Format price as currency"""
    if price is None:
        return "N/A"
    try:
        return f"${float(price):,.2f}"
    except (ValueError, TypeError):
        return str(price)

# Sidebar filters
with st.sidebar:
    st.header("🔍 Filters")
    
    # Refresh button
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.session_state.refresh_key += 1
        st.rerun()
    
    st.markdown("---")
    
    # Basic filters - make these prominent
    st.subheader("Basic Filters")
    
    # Chamber filter (House/Senate)
    chamber_options = ["All", "House", "Senate"]
    selected_chamber = st.radio(
        "🏛️ Chamber",
        chamber_options,
        index=0,
        help="Filter by congressional chamber"
    )
    chamber_filter = None if selected_chamber == "All" else selected_chamber
    
    # Transaction type filter (Purchase/Sale)
    type_options = ["All", "Purchase", "Sale"]
    selected_type = st.radio(
        "📊 Transaction Type",
        type_options,
        index=0,
        help="Filter by transaction type (Purchase = Bought, Sale = Sold)"
    )
    type_filter = None if selected_type == "All" else selected_type
    
    st.markdown("---")
    
    # Advanced filters
    st.subheader("Advanced Filters")
    
    # Get unique values for filters
    with st.spinner("Loading filter options..."):
        unique_tickers = get_unique_tickers(supabase_client, st.session_state.refresh_key)
        unique_politicians = get_unique_politicians(supabase_client, st.session_state.refresh_key)
    
    # Ticker filter
    ticker_options = ["All"] + unique_tickers
    selected_ticker = st.selectbox(
        "🏷️ Ticker",
        ticker_options,
        index=0,
        help="Filter by stock ticker symbol"
    )
    ticker_filter = None if selected_ticker == "All" else selected_ticker
    
    # Politician filter
    politician_options = ["All"] + unique_politicians
    selected_politician = st.selectbox(
        "👤 Politician",
        politician_options,
        index=0,
        help="Filter by politician name"
    )
    politician_filter = None if selected_politician == "All" else selected_politician
    
    st.markdown("---")
    
    # Date range filter
    st.subheader("📅 Date Range")
    use_date_filter = st.checkbox("Filter by transaction date", value=False)
    
    start_date = None
    end_date = None
    
    if use_date_filter:
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=date.today() - timedelta(days=90),
                help="Start date for transaction date filter"
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=date.today(),
                help="End date for transaction date filter"
            )

# Main content area
try:
    # Get trades with filters (cached)
    with st.spinner("Loading congress trades..."):
        trades = get_congress_trades(
            supabase_client,
            st.session_state.refresh_key,
            ticker_filter=ticker_filter,
            politician_filter=politician_filter,
            chamber_filter=chamber_filter,
            type_filter=type_filter,
            start_date=start_date if use_date_filter else None,
            end_date=end_date if use_date_filter else None
        )
    
    # Summary statistics
    st.header("📊 Summary Statistics")
    
    if trades:
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Total Trades", len(trades))
        
        with col2:
            house_count = len([t for t in trades if t.get('chamber') == 'House'])
            st.metric("House Trades", house_count)
        
        with col3:
            senate_count = len([t for t in trades if t.get('chamber') == 'Senate'])
            st.metric("Senate Trades", senate_count)
        
        with col4:
            purchase_count = len([t for t in trades if t.get('type') == 'Purchase'])
            st.metric("Purchases", purchase_count)
        
        with col5:
            sale_count = len([t for t in trades if t.get('type') == 'Sale'])
            st.metric("Sales", sale_count)
        
        st.markdown("---")
        
        # Display data table
        st.header("📋 Congress Trades")
        
        # Batch fetch company names for all unique tickers
        unique_tickers = list(set([t.get('ticker') for t in trades if t.get('ticker')]))
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
        for trade in trades:
            ticker = trade.get('ticker', 'N/A')
            ticker_upper = ticker.upper() if ticker != 'N/A' else 'N/A'
            company_name = company_names_map.get(ticker_upper, 'N/A')
            
            df_data.append({
                'ID': trade.get('id'),
                'Ticker': ticker,
                'Company': company_name,
                'Politician': trade.get('politician', 'N/A'),
                'Chamber': trade.get('chamber', 'N/A'),
                'Transaction Date': format_date(trade.get('transaction_date')),
                'Disclosure Date': format_date(trade.get('disclosure_date')),
                'Type': trade.get('type', 'N/A'),
                'Amount': trade.get('amount', 'N/A'),
                'Price': format_price(trade.get('price')),
                'Asset Type': trade.get('asset_type', 'N/A'),
                'Conflict Score': trade.get('conflict_score') if trade.get('conflict_score') is not None else 'N/A',
                'Notes': trade.get('notes', '')[:100] + '...' if trade.get('notes') and len(trade.get('notes', '')) > 100 else (trade.get('notes') or ''),
                'Created At': format_date(trade.get('created_at'))
            })
        
        df = pd.DataFrame(df_data)
        
        # Display dataframe with built-in sorting and pagination
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )
        
        # Show record count
        st.caption(f"Showing {len(trades)} trade(s)")
        
    else:
        st.info("""
        📭 No congress trades found matching the current filters.
        
        Try adjusting your filter criteria or check back later when more data is available.
        """)

except Exception as e:
    logger.error(f"Error in congress trades page: {e}", exc_info=True)
    st.error(f"❌ An error occurred: {str(e)}")
    st.info("Please check the logs or contact an administrator.")

