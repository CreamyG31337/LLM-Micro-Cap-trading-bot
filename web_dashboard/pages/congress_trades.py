#!/usr/bin/env python3
"""
Congress Trades Viewer
======================

Streamlit page for viewing congressional stock trading disclosures.
Displays trades with filtering, sorting, and summary statistics.
"""

import streamlit as st
import streamlit.components.v1 as components
import sys
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone, date
import pandas as pd
import logging
import base64

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
from postgres_client import PostgresClient
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

# Initialize PostgreSQL client for AI analysis data
@st.cache_resource
def get_postgres_client():
    """Get PostgreSQL client instance for analysis data"""
    try:
        return PostgresClient()
    except Exception as e:
        logger.warning(f"PostgreSQL not available (AI analysis disabled): {e}")
        return None

postgres_client = get_postgres_client()

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

# Description
st.info("""
**Track the 'Smart Money'** by monitoring stock disclosures from US Congress members. Our proprietary **Conflict Score** highlights suspicious trades where politicians buy stocks regulated by their own committees—often a leading indicator for upcoming government contracts or legislation.

*Note: Data is based on public disclosures which may be delayed by up to 45 days.*
""")

# Add CSS for tooltips
st.markdown("""
<style>
    /* Congress Trades Table Styling */
    .congress-trades-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
        background-color: var(--background-color, #ffffff);
        color: var(--text-color, #262730);
    }
    
    .congress-trades-table th {
        background-color: var(--secondary-background-color, #f0f2f6);
        padding: 0.75rem;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid var(--border-color, rgba(128, 128, 128, 0.2));
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .congress-trades-table td {
        padding: 0.75rem;
        border-bottom: 1px solid var(--border-color, rgba(128, 128, 128, 0.1));
    }
    
    .congress-trades-table tr:hover {
        background-color: var(--secondary-background-color, #f0f2f6);
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .congress-trades-table {
            background-color: var(--background-color, #0e1117);
            color: var(--text-color, #fafafa);
        }
        
        .congress-trades-table th {
            background-color: var(--secondary-background-color, #262730);
            border-bottom-color: rgba(255, 255, 255, 0.1);
        }
        
        .congress-trades-table td {
            border-bottom-color: rgba(255, 255, 255, 0.1);
        }
        
        .congress-trades-table tr:hover {
            background-color: var(--secondary-background-color, #262730);
        }
    }
    
    /* Tooltip container for AI Reasoning column */
    .reasoning-cell {
        position: relative;
        cursor: pointer;
        max-width: 300px;
        overflow: visible !important;
        display: inline-block;
        -webkit-tap-highlight-color: rgba(0, 0, 0, 0.1);
        touch-action: manipulation;
        user-select: none;
    }

    /* Special styling for reasoning cells with copy functionality */
    .reasoning-cell[data-full-reasoning-b64],
    .reasoning-cell[data-full-reasoning] {
        cursor: copy;
    }

    .reasoning-cell[data-full-reasoning-b64]:hover,
    .reasoning-cell[data-full-reasoning]:hover {
        background-color: rgba(16, 185, 129, 0.1);
        border-radius: 4px;
    }
    
    /* Make sure touch targets are large enough on mobile */
    @media (max-width: 768px) {
        .reasoning-cell {
            min-height: 44px;
            display: flex;
            align-items: center;
            padding: 0.25rem 0;
        }
    }
    
    .reasoning-text {
        display: inline-block;
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    
    .reasoning-tooltip {
        visibility: hidden;
        opacity: 0;
        position: absolute;
        z-index: 999999 !important;
        background-color: #1f1f1f;
        color: #ffffff;
        padding: 0.75rem 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        max-width: 400px;
        min-width: 200px;
        width: max-content;
        font-size: 0.85rem;
        line-height: 1.5;
        word-wrap: break-word;
        white-space: normal;
        pointer-events: none;
        transition: opacity 0.2s ease-in-out, visibility 0.2s ease-in-out;
    }
    
    /* Tooltip arrow - positioned above by default */
    .reasoning-tooltip::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 6px solid transparent;
        border-top-color: #1f1f1f;
    }
    
    /* Tooltip arrow when positioned below */
    .reasoning-tooltip[data-placement="below"]::after {
        top: auto;
        bottom: 100%;
        border-top-color: transparent;
        border-bottom-color: #1f1f1f;
    }
    
    /* Dark mode arrow adjustments */
    @media (prefers-color-scheme: dark) {
        .reasoning-tooltip::after {
            border-top-color: #2d2d2d;
        }
        
        .reasoning-tooltip[data-placement="below"]::after {
            border-top-color: transparent;
            border-bottom-color: #2d2d2d;
        }
    }
    
    /* Show tooltip on hover (desktop) - JavaScript will handle visibility */
    /* Show tooltip on hover (desktop) - JavaScript will position it */
    .reasoning-cell:hover .reasoning-tooltip {
        visibility: visible;
        opacity: 1;
        display: block;
    }
    
    /* Show tooltip when active (mobile click) */
    .reasoning-cell.active .reasoning-tooltip {
        visibility: visible;
        opacity: 1;
        display: block;
    }
    
    /* Dark mode tooltip styling */
    @media (prefers-color-scheme: dark) {
        .reasoning-tooltip {
            background-color: #2d2d2d;
            color: #fafafa;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
        }
        
        .reasoning-tooltip::after {
            border-top-color: #2d2d2d;
        }
    }
    
    /* Table container for scrolling */
    .table-container {
        overflow-x: auto;
        width: 100%;
        margin: 1rem 0;
    }

    /* Ensure tooltip doesn't get cut off */
    .table-container {
        overflow: visible;
    }

    .congress-trades-table {
        overflow: visible;
    }

    /* Column sorting styles */
    .congress-trades-table th {
        cursor: pointer;
        user-select: none;
        position: relative;
        transition: background-color 0.2s ease;
    }

    .congress-trades-table th:hover {
        background-color: var(--secondary-background-color, #e6f3ff) !important;
    }

    .congress-trades-table th.sortable {
        padding-right: 1.5rem; /* Space for sort indicator */
    }

    .sort-indicator {
        position: absolute;
        right: 0.25rem;
        top: 50%;
        transform: translateY(-50%);
        font-size: 0.75rem;
        opacity: 0.6;
        transition: opacity 0.2s ease;
    }

    .congress-trades-table th.sort-asc .sort-indicator::after {
        content: "▲";
        opacity: 1;
    }

    .congress-trades-table th.sort-desc .sort-indicator::after {
        content: "▼";
        opacity: 1;
    }

    .congress-trades-table th.sort-none .sort-indicator::after {
        content: "⬍";
        opacity: 0.3;
    }

    /* Dark mode sorting styles */
    @media (prefers-color-scheme: dark) {
        .congress-trades-table th:hover {
            background-color: var(--secondary-background-color, #3d3d3d) !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state for refresh
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0

# Initialize pagination state
if 'page_number' not in st.session_state:
    st.session_state.page_number = 0
if 'page_size' not in st.session_state:
    st.session_state.page_size = 100

# Query functions
@st.cache_data(ttl=60, show_spinner=False)
def get_unique_tickers(_supabase_client, _refresh_key: int) -> List[str]:
    """Get all unique tickers from congress_trades table"""
    try:
        if _supabase_client is None:
            return []
        
        # Paginate through all results to get all unique tickers
        all_tickers = set()
        batch_size = 1000  # Supabase default limit
        offset = 0
        
        while True:
            result = _supabase_client.supabase.table("congress_trades")\
                .select("ticker")\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not result.data:
                break
            
            # Add tickers to set (automatically deduplicates)
            for trade in result.data:
                ticker = trade.get('ticker')
                if ticker:
                    all_tickers.add(ticker)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops (max 100k rows = 100 batches)
            if offset > 100000:
                logger.warning("Reached 100,000 row safety limit in get_unique_tickers pagination")
                break
        
        # Return sorted list
        return sorted(list(all_tickers))
    except Exception as e:
        logger.error(f"Error fetching unique tickers: {e}", exc_info=True)
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_unique_politicians(_supabase_client, _refresh_key: int) -> List[str]:
    """Get all unique politicians from congress_trades table"""
    try:
        if _supabase_client is None:
            return []
        
        # Paginate through all results to get all unique politicians
        all_politicians = set()
        batch_size = 1000  # Supabase default limit
        offset = 0
        
        while True:
            result = _supabase_client.supabase.table("congress_trades")\
                .select("politician")\
                .range(offset, offset + batch_size - 1)\
                .execute()
            
            if not result.data:
                break
            
            # Add politicians to set (automatically deduplicates)
            for trade in result.data:
                politician = trade.get('politician')
                if politician:
                    all_politicians.add(politician)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops (max 100k rows = 100 batches)
            if offset > 100000:
                logger.warning("Reached 100,000 row safety limit in get_unique_politicians pagination")
                break
        
        # Return sorted list
        return sorted(list(all_politicians))
    except Exception as e:
        logger.error(f"Error fetching unique politicians: {e}", exc_info=True)
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_analysis_data(_postgres_client, _refresh_key: int) -> Dict[int, Dict[str, Any]]:
    """Get AI analysis data from PostgreSQL
    
    Returns:
        Dict mapping trade_id to analysis data
    """
    if _postgres_client is None:
        return {}
    
    try:
        result = _postgres_client.execute_query(
            "SELECT trade_id, conflict_score, reasoning, model_used, analyzed_at FROM congress_trades_analysis ORDER BY analyzed_at DESC"
        )
        
        # Create dict mapping trade_id -> analysis (most recent per trade)
        analysis_map = {}
        for row in result:
            trade_id = row['trade_id']
            if trade_id not in analysis_map:  # Keep only most recent
                analysis_map[trade_id] = row
        
        return analysis_map
    except Exception as e:
        logger.error(f"Error fetching analysis data: {e}")
        return {}

@st.cache_data(ttl=60, show_spinner=False)
def get_congress_trades(
    _supabase_client,
    _refresh_key: int,
    ticker_filter: Optional[str] = None,
    politician_filter: Optional[str] = None,
    chamber_filter: Optional[str] = None,
    type_filter: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    analyzed_only: bool = False,
    min_score: Optional[float] = None
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
        
        # Get analysis data for filtering
        analysis_map = get_analysis_data(postgres_client, _refresh_key) if postgres_client else {}
        
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
        
        # Post-process: filter by analysis status and score
        if analyzed_only or min_score is not None:
            filtered_trades = []
            for trade in all_trades:
                trade_id = trade.get('id')
                
                # Check if analyzed
                if analyzed_only and trade_id not in analysis_map:
                    continue
                
                # Check min score
                if min_score is not None:
                    analysis = analysis_map.get(trade_id)
                    if not analysis or analysis.get('conflict_score') is None:
                        continue
                    if float(analysis['conflict_score']) < min_score:
                        continue
                
                filtered_trades.append(trade)
            
            return filtered_trades
        
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

# Function to render congress trades table with tooltips
def render_congress_trades_table(df_data: List[Dict[str, Any]]) -> str:
    """Render congress trades as HTML table with tooltip support for AI Reasoning column
    
    Args:
        df_data: List of dictionaries with trade data (includes '_full_reasoning' for tooltips)
        
    Returns:
        HTML string for the table
    """
    import html
    
    # Start building HTML table
    html_parts = ['<div class="table-container">']
    html_parts.append('<table class="congress-trades-table">')
    
    # Table header with sorting
    html_parts.append('<thead><tr>')
    columns = ['Ticker', 'Company', 'Politician', 'Chamber', 'Party', 'State',
               'Transaction Date', 'Type', 'Amount', 'Conflict Score', 'AI Reasoning', 'Owner']

    # Define sortable columns (all except AI Reasoning for now due to tooltips)
    sortable_columns = ['Ticker', 'Company', 'Politician', 'Chamber', 'Party', 'State',
                       'Transaction Date', 'Type', 'Amount', 'Conflict Score', 'Owner']

    for col in columns:
        if col in sortable_columns:
            html_parts.append(f'<th class="sortable" data-column="{col}">{html.escape(col)}<span class="sort-indicator"></span></th>')
        else:
            html_parts.append(f'<th>{html.escape(col)}</th>')
    html_parts.append('</tr></thead>')
    
    # Table body
    html_parts.append('<tbody>')
    
    for row in df_data:
        html_parts.append('<tr>')
        
        for col in columns:
            value = row.get(col, 'N/A')
            value_str = str(value) if value is not None else 'N/A'
            
            # Special handling for AI Reasoning column
            if col == 'AI Reasoning':
                # Get full reasoning text for tooltip and copy
                full_reasoning = row.get('_full_reasoning', '')
                
                # Always add reasoning-cell with copy functionality if we have full reasoning
                if full_reasoning:
                    # Use base64 encoding for data attribute to avoid HTML escaping issues
                    full_reasoning_b64 = base64.b64encode(full_reasoning.encode('utf-8')).decode('utf-8')
                    
                    # Check if we need a tooltip (show tooltip if full reasoning is longer than displayed)
                    needs_tooltip = len(full_reasoning) > len(value_str)
                    
                    html_parts.append('<td>')
                    html_parts.append(f'<div class="reasoning-cell" data-full-reasoning-b64="{full_reasoning_b64}">')
                    html_parts.append(f'<span class="reasoning-text">{html.escape(value_str)}</span>')
                    if needs_tooltip:
                        html_parts.append(f'<div class="reasoning-tooltip">{html.escape(full_reasoning)}</div>')
                    html_parts.append('</div>')
                    html_parts.append('</td>')
                else:
                    # No reasoning available
                    html_parts.append(f'<td>{html.escape(value_str)}</td>')
            else:
                # Regular column - escape HTML to prevent XSS
                html_parts.append(f'<td>{html.escape(value_str)}</td>')
        
        html_parts.append('</tr>')
    
    html_parts.append('</tbody>')
    html_parts.append('</table>')
    html_parts.append('</div>')
    
    return ''.join(html_parts)

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
    
    # AI Analysis Filters
    st.subheader("🤖 AI Analysis Filters")
    
    analyzed_only = st.checkbox(
        "Only show analyzed trades",
        value=False,
        help="Show only trades that have been analyzed by AI"
    )
    
    # Score filter
    score_filter_options = ["All Scores", "High Risk (>0.7)", "Medium Risk (0.3-0.7)", "Low Risk (<0.3)"]
    selected_score_filter = st.selectbox(
        "Risk Level",
        score_filter_options,
        help="Filter by AI conflict score risk level"
    )
    
    # Convert score filter to min_score
    min_score = None
    if selected_score_filter == "High Risk (>0.7)":
        min_score = 0.7
    elif selected_score_filter == "Medium Risk (0.3-0.7)":
        min_score = 0.3
    elif selected_score_filter == "Low Risk (<0.3)":
        min_score = 0.0
    
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
    
    st.markdown("---")
    
    # Pagination controls
    st.subheader("📄 Pagination")
    
    page_size_options = [25, 50, 100, 250, 500]
    page_size = st.selectbox(
        "Items per page",
        page_size_options,
        index=page_size_options.index(st.session_state.page_size),
        help="Number of trades to show per page"
    )
    
    # Update page size in session state
    if page_size != st.session_state.page_size:
        st.session_state.page_size = page_size
        st.session_state.page_number = 0  # Reset to first page when changing size

# Main content area
try:
    # Get analysis data
    analysis_map = get_analysis_data(postgres_client, st.session_state.refresh_key) if postgres_client else {}
    
    # Get trades with filters (cached)
    with st.spinner("Loading congress trades..."):
        all_trades = get_congress_trades(
            supabase_client,
            st.session_state.refresh_key,
            ticker_filter=ticker_filter,
            politician_filter=politician_filter,
            chamber_filter=chamber_filter,
            type_filter=type_filter,
            start_date=start_date if use_date_filter else None,
            end_date=end_date if use_date_filter else None,
            analyzed_only=analyzed_only,
            min_score=min_score
        )
    
    # Calculate pagination
    total_trades = len(all_trades)
    total_pages = (total_trades + st.session_state.page_size - 1) // st.session_state.page_size if total_trades > 0 else 0
    
    # Apply pagination to trades
    start_idx = st.session_state.page_number * st.session_state.page_size
    end_idx = start_idx + st.session_state.page_size
    trades = all_trades[start_idx:end_idx]
    
    # Summary statistics
    st.header("📊 Summary Statistics")
    
    if all_trades:  # Use all_trades for stats, not paginated trades
        col1, col2, col3, col4, col5 = st.columns(5)
        
        # Count analyzed trades
        analyzed_count = len([t for t in all_trades if t.get('id') in analysis_map])
        
        with col1:
            st.metric("Total Trades", total_trades)
        
        with col2:
            st.metric("Analyzed", f"{analyzed_count}/{total_trades}")
        
        with col3:
            house_count = len([t for t in all_trades if t.get('chamber') == 'House'])
            st.metric("House", house_count)
        
        with col4:
            senate_count = len([t for t in all_trades if t.get('chamber') == 'Senate'])
            st.metric("Senate", senate_count)
        
        with col5:
            purchase_count = len([t for t in all_trades if t.get('type') == 'Purchase'])
            sale_count = len([t for t in all_trades if t.get('type') == 'Sale'])
            st.metric("Buy/Sell", f"{purchase_count}/{sale_count}")
        
        st.markdown("---")
        
        # Pagination controls at top
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("⬅️ Previous", disabled=(st.session_state.page_number == 0)):
                    st.session_state.page_number -= 1
                    st.rerun()
            
            with col2:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'>Page {st.session_state.page_number + 1} of {total_pages}</div>", unsafe_allow_html=True)
            
            with col3:
                if st.button("Next ➡️", disabled=(st.session_state.page_number >= total_pages - 1)):
                    st.session_state.page_number += 1
                    st.rerun()
        
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
        
        # Prepare DataFrame with analysis data
        df_data = []
        for trade in trades:
            ticker = trade.get('ticker', 'N/A')
            ticker_upper = ticker.upper() if ticker != 'N/A' else 'N/A'
            company_name = company_names_map.get(ticker_upper, 'N/A')
            
            # Get analysis data
            trade_id = trade.get('id')
            analysis = analysis_map.get(trade_id, {})
            conflict_score = analysis.get('conflict_score')
            reasoning = analysis.get('reasoning', '')
            
            # Format conflict score with risk indicator
            if conflict_score is not None:
                score_val = float(conflict_score)
                if score_val >= 0.7:
                    score_display = f"🔴 {score_val:.2f}"
                elif score_val >= 0.3:
                    score_display = f"🟡 {score_val:.2f}"
                else:
                    score_display = f"🟢 {score_val:.2f}"
            else:
                score_display = "⚪ N/A"
            
            # Truncate reasoning for table
            reasoning_short = reasoning[:160] + '...' if reasoning and len(reasoning) > 160 else reasoning
            
            df_data.append({
                'Ticker': ticker,
                'Company': company_name,
                'Politician': trade.get('politician', 'N/A'),
                'Chamber': trade.get('chamber', 'N/A'),
                'Party': trade.get('party', 'N/A'),
                'State': trade.get('state', 'N/A'),
                'Transaction Date': format_date(trade.get('transaction_date')),
                'Type': trade.get('type', 'N/A'),
                'Amount': trade.get('amount', 'N/A'),
                'Conflict Score': score_display,
                'AI Reasoning': reasoning_short if reasoning else '',
                'Owner': trade.get('owner', 'N/A'),
                '_full_reasoning': reasoning if reasoning else ''  # Store full reasoning for tooltip
            })
        
        # Render custom HTML table with tooltips and sorting
        html_table = render_congress_trades_table(df_data)
        st.markdown(html_table, unsafe_allow_html=True)

        # Add JavaScript for mobile tooltip support and column sorting using components.html
        # This ensures the script executes properly in Streamlit
        tooltip_script = """
        <script>
        (function() {
            let touchStartTime = 0;
            let touchStartTarget = null;

            // Table sorting functionality
            let currentSortColumn = null;
            let currentSortDirection = 'asc'; // 'asc', 'desc', or null

            function sortTable(columnName, direction) {
                const table = document.querySelector('.congress-trades-table');
                if (!table) return;

                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));

                // Clear previous sort indicators
                table.querySelectorAll('th').forEach(th => {
                    th.classList.remove('sort-asc', 'sort-desc', 'sort-none');
                });

                if (direction === null) {
                    // Reset to original order - for now, just clear indicators
                    currentSortColumn = null;
                    currentSortDirection = null;
                    return;
                }

                // Sort rows
                rows.sort((a, b) => {
                    const aCell = getCellValue(a, columnName);
                    const bCell = getCellValue(b, columnName);

                    let result = 0;

                    // Handle different data types
                    if (columnName === 'Conflict Score') {
                        // Extract numeric value from score (e.g., "🔴 0.85" -> 0.85, "⚪ N/A" -> -1)
                        const aVal = extractScoreValue(aCell);
                        const bVal = extractScoreValue(bCell);
                        result = aVal - bVal;
                    } else if (columnName === 'Transaction Date') {
                        // Parse dates
                        const aDate = parseDate(aCell);
                        const bDate = parseDate(bCell);
                        result = aDate - bDate;
                    } else if (columnName === 'Amount') {
                        // Parse amounts (remove $ and commas)
                        const aVal = parseFloat(aCell.replace(/[$,]/g, '')) || 0;
                        const bVal = parseFloat(bCell.replace(/[$,]/g, '')) || 0;
                        result = aVal - bVal;
                    } else {
                        // String comparison (case-insensitive)
                        result = aCell.toLowerCase().localeCompare(bCell.toLowerCase());
                    }

                    return direction === 'asc' ? result : -result;
                });

                // Re-append sorted rows
                rows.forEach(row => tbody.appendChild(row));

                // Update sort indicators
                const headerCell = table.querySelector(`th[data-column="${columnName}"]`);
                if (headerCell) {
                    headerCell.classList.add(`sort-${direction}`);
                }

                currentSortColumn = columnName;
                currentSortDirection = direction;
            }

            function getCellValue(row, columnName) {
                const columns = ['Ticker', 'Company', 'Politician', 'Chamber', 'Party', 'State',
                               'Transaction Date', 'Type', 'Amount', 'Conflict Score', 'AI Reasoning', 'Owner'];
                const colIndex = columns.indexOf(columnName);
                const cell = row.cells[colIndex];
                return cell ? cell.textContent.trim() : '';
            }

            function extractScoreValue(scoreText) {
                // Extract numeric value from conflict score (e.g., "🔴 0.85" -> 0.85)
                const match = scoreText.match(/(\d+\.\d+)/);
                return match ? parseFloat(match[1]) : -1; // N/A scores get -1 (sort last)
            }

            function parseDate(dateText) {
                // Parse date in YYYY-MM-DD format
                if (!dateText || dateText === 'N/A') return new Date(0);
                return new Date(dateText);
            }

            function cycleSort(columnName) {
                if (currentSortColumn === columnName) {
                    // Cycle through: asc -> desc -> none
                    if (currentSortDirection === 'asc') {
                        sortTable(columnName, 'desc');
                    } else if (currentSortDirection === 'desc') {
                        sortTable(columnName, null); // Reset to original order
                    } else {
                        sortTable(columnName, 'asc');
                    }
                } else {
                    // New column - start with ascending
                    sortTable(columnName, 'asc');
                }
            }
            
            function positionTooltip(cell, tooltip) {
                // Make tooltip temporarily visible to measure it
                tooltip.style.visibility = 'hidden';
                tooltip.style.opacity = '1';
                tooltip.style.display = 'block';
                
                const cellRect = cell.getBoundingClientRect();
                const viewportHeight = window.innerHeight;
                const viewportWidth = window.innerWidth;
                
                // Force a reflow to get accurate measurements
                void tooltip.offsetWidth;
                
                const tooltipRect = tooltip.getBoundingClientRect();
                const tooltipHeight = tooltipRect.height;
                const tooltipWidth = tooltipRect.width;
                
                // Calculate space above and below the cell in viewport
                const spaceAbove = cellRect.top;
                const spaceBelow = viewportHeight - cellRect.bottom;
                const padding = 10;
                
                let top, left;
                let positionAbove = true;
                
                // Decide whether to position above or below
                if (spaceAbove >= tooltipHeight + padding) {
                    // Enough space above - position above
                    top = -tooltipHeight - padding;
                    positionAbove = true;
                } else if (spaceBelow >= tooltipHeight + padding) {
                    // Not enough space above, but enough below - position below
                    top = cellRect.height + padding;
                    positionAbove = false;
                } else {
                    // Not enough space either way - choose the side with more space
                    if (spaceAbove > spaceBelow) {
                        // Position above, but adjust to fit in viewport
                        const maxTop = -(cellRect.top - padding);
                        top = Math.max(-tooltipHeight - padding, maxTop);
                        positionAbove = true;
                    } else {
                        // Position below, but adjust to fit in viewport
                        const maxBottom = viewportHeight - cellRect.bottom - padding;
                        top = Math.min(cellRect.height + padding, maxBottom);
                        positionAbove = false;
                    }
                }
                
                // Center horizontally relative to cell
                left = (cellRect.width / 2) - (tooltipWidth / 2);
                
                // Adjust horizontal position to keep tooltip within viewport
                const cellLeft = cellRect.left;
                if (cellLeft + left < padding) {
                    // Tooltip would go off left edge
                    left = padding - cellLeft;
                } else if (cellLeft + left + tooltipWidth > viewportWidth - padding) {
                    // Tooltip would go off right edge
                    left = viewportWidth - padding - cellLeft - tooltipWidth;
                }
                
                // Apply positioning (relative to cell since cell has position: relative)
                tooltip.style.top = top + 'px';
                tooltip.style.left = left + 'px';
                tooltip.style.bottom = 'auto';
                tooltip.style.right = 'auto';
                tooltip.style.transform = 'none';
                
                // Update arrow position based on placement
                if (positionAbove) {
                    tooltip.setAttribute('data-placement', 'above');
                } else {
                    tooltip.setAttribute('data-placement', 'below');
                }
                
                // Restore visibility - let CSS handle it
                tooltip.style.visibility = '';
                tooltip.style.opacity = '';
                tooltip.style.display = '';
            }
            
            // Copy AI reasoning text to clipboard
            function copyReasoningToClipboard(reasoningCell) {
                // Try base64 encoded attribute first, then fallback to regular attribute
                let fullReasoning = reasoningCell.getAttribute('data-full-reasoning-b64');
                let decodedText;
                
                if (fullReasoning) {
                    // Decode from base64
                    try {
                        decodedText = atob(fullReasoning);
                    } catch (e) {
                        console.error('Failed to decode base64 reasoning:', e);
                        return false;
                    }
                } else {
                    // Fallback to regular attribute (for backwards compatibility)
                    fullReasoning = reasoningCell.getAttribute('data-full-reasoning');
                    if (!fullReasoning) {
                        console.warn('No data-full-reasoning attribute found');
                        return false;
                    }
                    // Decode HTML entities
                    const textarea = document.createElement('textarea');
                    textarea.innerHTML = fullReasoning;
                    decodedText = textarea.value || fullReasoning;
                }

                // Try modern clipboard API first
                if (navigator.clipboard && window.isSecureContext) {
                    navigator.clipboard.writeText(decodedText).then(function() {
                        showCopyFeedback(reasoningCell);
                    }).catch(function(err) {
                        console.warn('Failed to copy text: ', err);
                        fallbackCopyTextToClipboard(decodedText);
                        showCopyFeedback(reasoningCell);
                    });
                } else {
                    // Fallback for older browsers or non-secure contexts
                    fallbackCopyTextToClipboard(decodedText);
                    showCopyFeedback(reasoningCell);
                }
                return true;
            }

            function fallbackCopyTextToClipboard(text) {
                const textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.left = "-999999px";
                textArea.style.top = "-999999px";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {
                    document.execCommand('copy');
                } catch (err) {
                    console.error('Fallback: Oops, unable to copy', err);
                }
                textArea.remove();
            }

            function showCopyFeedback(reasoningCell) {
                // Add temporary visual feedback
                const originalText = reasoningCell.querySelector('.reasoning-text');
                if (originalText) {
                    const originalContent = originalText.innerHTML;
                    originalText.innerHTML = '<span style="color: #10b981; font-weight: bold;">✓ Copied!</span>';
                    setTimeout(function() {
                        originalText.innerHTML = originalContent;
                    }, 1500);
                }
            }

            function handleTooltipToggle(e, reasoningCell) {
                if (!reasoningCell) return;

                // If this is a reasoning cell and has full reasoning data, copy on click
                const hasFullReasoning = reasoningCell.hasAttribute('data-full-reasoning');
                if (hasFullReasoning) {
                    const copied = copyReasoningToClipboard(reasoningCell);
                    if (copied) {
                        // Don't show tooltip if we copied text (single click = copy)
                        return;
                    }
                }

                // Close other tooltips
                document.querySelectorAll('.reasoning-cell.active').forEach(function(activeCell) {
                    if (activeCell !== reasoningCell) {
                        activeCell.classList.remove('active');
                    }
                });

                // Toggle this tooltip
                const isActive = reasoningCell.classList.toggle('active');
                const tooltip = reasoningCell.querySelector('.reasoning-tooltip');

                if (isActive && tooltip) {
                    // Position tooltip, then CSS will show it via .active class
                    setTimeout(function() {
                        positionTooltip(reasoningCell, tooltip);
                        // Also set up continuous repositioning for active tooltips
                        if (reasoningCell._repositionInterval) {
                            clearInterval(reasoningCell._repositionInterval);
                        }
                        reasoningCell._repositionInterval = setInterval(function() {
                            if (reasoningCell.classList.contains('active') && window.getComputedStyle(tooltip).visibility === 'visible') {
                                positionTooltip(reasoningCell, tooltip);
                            } else {
                                clearInterval(reasoningCell._repositionInterval);
                                reasoningCell._repositionInterval = null;
                            }
                        }, 50);
                    }, 10);
                } else if (tooltip && reasoningCell._repositionInterval) {
                    // Clear interval when tooltip is closed
                    clearInterval(reasoningCell._repositionInterval);
                    reasoningCell._repositionInterval = null;
                }
            }
            
            // Handle hover for desktop - position tooltip on hover
            function setupHoverHandlers() {
                document.querySelectorAll('.reasoning-cell').forEach(function(cell) {
                    const tooltip = cell.querySelector('.reasoning-tooltip');
                    if (tooltip && !cell.hasAttribute('data-hover-setup')) {
                        cell.setAttribute('data-hover-setup', 'true');
                        
                        // Store reference for scroll updates
                        cell._tooltip = tooltip;
                        
                        cell.addEventListener('mouseenter', function() {
                            // Position tooltip when hovering - use requestAnimationFrame to ensure CSS has applied
                            requestAnimationFrame(function() {
                                positionTooltip(cell, tooltip);
                            });
                            
                            // Set up continuous repositioning while hovering
                            if (cell._hoverRepositionInterval) {
                                clearInterval(cell._hoverRepositionInterval);
                            }
                            cell._hoverRepositionInterval = setInterval(function() {
                                if (cell.matches(':hover') && window.getComputedStyle(tooltip).visibility === 'visible') {
                                    positionTooltip(cell, tooltip);
                                } else {
                                    clearInterval(cell._hoverRepositionInterval);
                                    cell._hoverRepositionInterval = null;
                                }
                            }, 50);
                        });
                        
                        cell.addEventListener('mouseleave', function() {
                            if (cell._hoverRepositionInterval) {
                                clearInterval(cell._hoverRepositionInterval);
                                cell._hoverRepositionInterval = null;
                            }
                        });
                    }
                });
            }

            // Set up column sorting
            function setupColumnSorting() {
                document.querySelectorAll('th.sortable').forEach(function(header) {
                    header.addEventListener('click', function() {
                        const columnName = this.getAttribute('data-column');
                        if (columnName) {
                            cycleSort(columnName);
                        }
                    });
                });
            }

            // Reposition tooltips on scroll/resize (simpler now with absolute positioning)
            function repositionVisibleTooltips() {
                document.querySelectorAll('.reasoning-cell').forEach(function(cell) {
                    const tooltip = cell.querySelector('.reasoning-tooltip');
                    if (tooltip) {
                        const computedStyle = window.getComputedStyle(tooltip);
                        if (computedStyle.visibility === 'visible' || cell.classList.contains('active') || cell.matches(':hover')) {
                            positionTooltip(cell, tooltip);
                        }
                    }
                });
            }
            
            // Listen to scroll and resize for repositioning
            let scrollTimeout;
            window.addEventListener('scroll', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(repositionVisibleTooltips, 10);
            }, { passive: true });
            
            window.addEventListener('resize', function() {
                clearTimeout(scrollTimeout);
                scrollTimeout = setTimeout(repositionVisibleTooltips, 10);
            }, { passive: true });
            
            function initTooltips() {
                // Handle touch events for mobile
                document.addEventListener('touchstart', function(e) {
                    const reasoningCell = e.target.closest('.reasoning-cell');
                    if (reasoningCell) {
                        touchStartTime = Date.now();
                        touchStartTarget = reasoningCell;
                    }
                }, { passive: true });
                
                document.addEventListener('touchend', function(e) {
                    const reasoningCell = e.target.closest('.reasoning-cell') || touchStartTarget;
                    if (reasoningCell && (Date.now() - touchStartTime) < 300) {
                        e.preventDefault();
                        e.stopPropagation();

                        // For reasoning cells, copy text instead of showing tooltip
                        const hasFullReasoning = reasoningCell.hasAttribute('data-full-reasoning-b64') || 
                                                 reasoningCell.hasAttribute('data-full-reasoning');
                        if (hasFullReasoning) {
                            copyReasoningToClipboard(reasoningCell);
                        } else {
                            handleTooltipToggle(e, reasoningCell);
                        }
                    }
                    touchStartTarget = null;
                });
                
                // Handle click events (desktop and mobile fallback)
                document.addEventListener('click', function(e) {
                    const reasoningCell = e.target.closest('.reasoning-cell');

                    if (reasoningCell) {
                        e.stopPropagation();

                        // For reasoning cells, copy text instead of showing tooltip
                        const hasFullReasoning = reasoningCell.hasAttribute('data-full-reasoning-b64') || 
                                                 reasoningCell.hasAttribute('data-full-reasoning');
                        if (hasFullReasoning) {
                            copyReasoningToClipboard(reasoningCell);
                        } else {
                            handleTooltipToggle(e, reasoningCell);
                        }
                    } else {
                        // Click outside - close all tooltips
                        document.querySelectorAll('.reasoning-cell.active').forEach(function(activeCell) {
                            activeCell.classList.remove('active');
                        });
                    }
                });

                setupHoverHandlers();
                setupColumnSorting();
            }
            
            // Initialize when DOM is ready
            function startInit() {
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', initTooltips);
                } else {
                    initTooltips();
                }
            }
            
            startInit();
            
            // Also try after delays to catch dynamically added content
            setTimeout(initTooltips, 100);
            setTimeout(initTooltips, 500);
            setTimeout(initTooltips, 1000);
            
            // Re-initialize when new content is added (for Streamlit's dynamic updates)
            const observer = new MutationObserver(function(mutations) {
                let shouldReinit = false;
                mutations.forEach(function(mutation) {
                    if (mutation.addedNodes.length > 0) {
                        shouldReinit = true;
                    }
                });
                if (shouldReinit) {
                    setTimeout(function() {
                        initTooltips();
                        setupHoverHandlers();
                        setupColumnSorting();
                    }, 100);
                }
            });
            
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        })();
        </script>
        """
        components.html(tooltip_script, height=0)
        
        # Pagination controls at bottom
        if total_pages > 1:
            col1, col2, col3 = st.columns([1, 2, 1])
            
            with col1:
                if st.button("⬅️ Prev", key="prev_bottom", disabled=(st.session_state.page_number == 0)):
                    st.session_state.page_number -= 1
                    st.rerun()
            
            with col2:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'>Page {st.session_state.page_number + 1} of {total_pages} | Showing {start_idx + 1}-{min(end_idx, total_trades)} of {total_trades}</div>", unsafe_allow_html=True)
            
            with col3:
                if st.button("Next ➡️", key="next_bottom", disabled=(st.session_state.page_number >= total_pages - 1)):
                    st.session_state.page_number += 1
                    st.rerun()
        else:
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

