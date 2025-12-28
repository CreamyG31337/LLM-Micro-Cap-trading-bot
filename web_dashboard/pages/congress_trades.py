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
        position: fixed;
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
    
    /* Tooltip arrow */
    .reasoning-tooltip::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        border: 6px solid transparent;
        border-top-color: #1f1f1f;
    }
    
    /* Show tooltip on hover (desktop) - position dynamically */
    .reasoning-cell:hover .reasoning-tooltip {
        visibility: visible;
        opacity: 1;
    }
    
    /* Show tooltip when active (mobile click) - position dynamically */
    .reasoning-cell.active .reasoning-tooltip {
        visibility: visible;
        opacity: 1;
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
    
    # Table header
    html_parts.append('<thead><tr>')
    columns = ['Ticker', 'Company', 'Politician', 'Chamber', 'Party', 'State', 
               'Transaction Date', 'Type', 'Amount', 'Conflict Score', 'AI Reasoning', 'Owner']
    for col in columns:
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
                # Get full reasoning text for tooltip
                full_reasoning = row.get('_full_reasoning', '')
                
                # Check if we need a tooltip (show tooltip if we have full reasoning and it's longer than displayed)
                if full_reasoning and len(full_reasoning) > len(value_str):
                    # Add tooltip - show full reasoning on hover/click
                    html_parts.append('<td>')
                    html_parts.append('<div class="reasoning-cell">')
                    html_parts.append(f'<span class="reasoning-text">{html.escape(value_str)}</span>')
                    html_parts.append(f'<div class="reasoning-tooltip">{html.escape(full_reasoning)}</div>')
                    html_parts.append('</div>')
                    html_parts.append('</td>')
                else:
                    # Not truncated or no tooltip needed
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
            reasoning_short = reasoning[:80] + '...' if reasoning and len(reasoning) > 80 else reasoning
            
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
        
        # Render custom HTML table with tooltips
        html_table = render_congress_trades_table(df_data)
        st.markdown(html_table, unsafe_allow_html=True)
        
        # Add JavaScript for mobile tooltip support using components.html
        # This ensures the script executes properly in Streamlit
        tooltip_script = """
        <script>
        (function() {
            function positionTooltip(cell, tooltip) {
                const rect = cell.getBoundingClientRect();
                const tooltipRect = tooltip.getBoundingClientRect();
                const viewportHeight = window.innerHeight;
                const viewportWidth = window.innerWidth;
                
                // Try to position above first
                let top = rect.top - tooltipRect.height - 10;
                let left = rect.left + (rect.width / 2) - (tooltipRect.width / 2);
                
                // If not enough space above, position below
                if (top < 10) {
                    top = rect.bottom + 10;
                    tooltip.style.bottom = 'auto';
                    tooltip.style.top = top + 'px';
                    // Change arrow direction
                    tooltip.style.setProperty('--arrow-direction', 'down');
                } else {
                    tooltip.style.top = top + 'px';
                    tooltip.style.bottom = 'auto';
                    tooltip.style.setProperty('--arrow-direction', 'up');
                }
                
                // Keep tooltip within viewport horizontally
                if (left < 10) {
                    left = 10;
                } else if (left + tooltipRect.width > viewportWidth - 10) {
                    left = viewportWidth - tooltipRect.width - 10;
                }
                
                tooltip.style.left = left + 'px';
                tooltip.style.transform = 'translateX(0)';
            }
            
            function initTooltips() {
                // Use event delegation for dynamic content
                document.addEventListener('click', function(e) {
                    const reasoningCell = e.target.closest('.reasoning-cell');
                    
                    if (reasoningCell) {
                        e.stopPropagation();
                        e.preventDefault();
                        
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
                            // Position tooltip
                            positionTooltip(reasoningCell, tooltip);
                        }
                    } else {
                        // Click outside - close all tooltips
                        document.querySelectorAll('.reasoning-cell.active').forEach(function(activeCell) {
                            activeCell.classList.remove('active');
                        });
                    }
                });
                
                // Also handle hover for desktop
                document.querySelectorAll('.reasoning-cell').forEach(function(cell) {
                    const tooltip = cell.querySelector('.reasoning-tooltip');
                    if (tooltip) {
                        cell.addEventListener('mouseenter', function() {
                            positionTooltip(cell, tooltip);
                        });
                    }
                });
            }
            
            // Initialize when DOM is ready
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', initTooltips);
            } else {
                initTooltips();
            }
            
            // Also try after a short delay to catch dynamically added content
            setTimeout(initTooltips, 100);
            setTimeout(initTooltips, 500);
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

