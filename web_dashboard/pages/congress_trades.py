#!/usr/bin/env python3
"""
Congress Trades Viewer
======================

Streamlit page for viewing congressional stock trading disclosures.
Displays trades with filtering, sorting, and summary statistics.
"""

import streamlit as st
import sys
import base64
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta, timezone, date
import pandas as pd
import logging
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode


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

from auth_utils import is_authenticated, get_user_email, is_admin, get_user_token
from navigation import render_navigation
from supabase_client import SupabaseClient
from postgres_client import PostgresClient
from user_preferences import get_user_timezone
from aggrid_utils import TICKER_CELL_RENDERER_JS, GLOBAL_CLICK_HANDLER_JS
from streamlit_utils import CACHE_VERSION

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
    """Get Supabase client instance with role-based access"""
    try:
        # Admins use service_role to see all funds
        if is_admin():
            return SupabaseClient(use_service_role=True)
        
        # Regular users use their token to respect RLS
        user_token = get_user_token()
        if user_token:
            return SupabaseClient(user_token=user_token)
        else:
            logger.error("No user token available for non-admin user")
            return None
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



# Initialize session state for refresh
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0

# Initialize pagination state
if 'page_number' not in st.session_state:
    st.session_state.page_number = 0
if 'page_size' not in st.session_state:
    st.session_state.page_size = 100

# Query functions
@st.cache_data(ttl=3600, show_spinner=False)
def get_unique_tickers(_supabase_client, _refresh_key: int, _cache_version: str = "") -> List[str]:
    """Get all unique tickers from congress_trades table
    
    Cached for 1 hour since tickers don't change frequently.
    Auto-invalidates on deployment via _cache_version.
    """
    try:
        if _supabase_client is None:
            return []
        
        # Paginate through all results to get all unique tickers
        all_tickers = set()
        batch_size = 1000  # Supabase default limit
        offset = 0
        
        while True:
            result = _supabase_client.supabase.table("congress_trades_enriched")\
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

@st.cache_data(ttl=3600, show_spinner=False)
def get_unique_politicians(_supabase_client, _refresh_key: int, _cache_version: str = "") -> List[str]:
    """Get all unique politicians from congress_trades table
    
    Cached for 1 hour since politicians don't change frequently.
    Auto-invalidates on deployment via _cache_version.
    """
    try:
        if _supabase_client is None:
            return []
        
        # Paginate through all results to get all unique politicians
        all_politicians = set()
        batch_size = 1000  # Supabase default limit
        offset = 0
        
        while True:
            result = _supabase_client.supabase.table("congress_trades_enriched")\
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
            "SELECT trade_id, conflict_score, reasoning, model_used, analyzed_at FROM congress_trades_analysis WHERE conflict_score IS NOT NULL ORDER BY analyzed_at DESC"
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
        query = _supabase_client.supabase.table("congress_trades_enriched").select("*")
        
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
        unique_tickers = get_unique_tickers(supabase_client, st.session_state.refresh_key, CACHE_VERSION)
        unique_politicians = get_unique_politicians(supabase_client, st.session_state.refresh_key, CACHE_VERSION)
    
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
    
    # Don't paginate here - let AgGrid handle it with all data
    total_trades = len(all_trades)
    trades = all_trades  # Pass all trades to AgGrid
    
    # Summary statistics
    st.header("📊 Summary Statistics")
    
    if all_trades:  # Use all_trades for stats, not paginated trades
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
        
        # Count analyzed trades
        analyzed_count = len([t for t in all_trades if t.get('id') in analysis_map])
        
        # Count unique tickers
        unique_tickers = len(set([t.get('ticker') for t in all_trades if t.get('ticker')]))
        
        # Calculate High Risk Trades (conflict_score >= 0.7)
        high_risk_count = 0
        for trade in all_trades:
            trade_id = trade.get('id')
            analysis = analysis_map.get(trade_id, {})
            conflict_score = analysis.get('conflict_score')
            if conflict_score is not None:
                try:
                    score_val = float(conflict_score)
                    if score_val >= 0.7:
                        high_risk_count += 1
                except (ValueError, TypeError):
                    pass
        
        # Calculate Most Active Politician (last 31 days, excluding child and spouse owners)
        thirty_one_days_ago = date.today() - timedelta(days=31)
        politician_counts = {}
        for trade in all_trades:
            # Filter by date - only count trades from last 31 days
            transaction_date_str = trade.get('transaction_date')
            if transaction_date_str:
                try:
                    # Parse ISO format date string
                    if isinstance(transaction_date_str, str):
                        # Handle ISO format: "2024-01-15" or "2024-01-15T00:00:00"
                        transaction_date = datetime.fromisoformat(transaction_date_str.split('T')[0]).date()
                    elif isinstance(transaction_date_str, date):
                        transaction_date = transaction_date_str
                    else:
                        continue
                    
                    # Skip if trade is older than 31 days
                    if transaction_date < thirty_one_days_ago:
                        continue
                except (ValueError, AttributeError, TypeError):
                    # If we can't parse the date, skip this trade
                    continue
            
            owner = trade.get('owner')
            # Skip trades where owner is Child or Spouse
            if owner and owner.lower() in ('child', 'spouse'):
                continue
            politician = trade.get('politician')
            if politician:
                politician_counts[politician] = politician_counts.get(politician, 0) + 1
        
        if politician_counts:
            most_active_politician = max(politician_counts.items(), key=lambda x: x[1])
            most_active_name = most_active_politician[0]
            most_active_count = most_active_politician[1]
            most_active_display = f"{most_active_name} ({most_active_count})"
        else:
            most_active_display = "N/A"
        
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
        
        with col6:
            st.metric("Unique Tickers", unique_tickers)
        
        with col7:
            st.metric("High Risk Trades", high_risk_count)
        
        with col8:
            st.metric("Most Active Politician (Last 31 Days)", most_active_display)
        
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
            reasoning_short = reasoning[:80] + '...' if reasoning and len(reasoning) > 80 else (reasoning or '')
            
            # Create unique identifier for this trade
            trade_label = f"{ticker} | {trade.get('politician', 'Unknown')} | {format_date(trade.get('transaction_date'))}"
            
            df_data.append({
                'Ticker': ticker,
                'Company': company_name,
                'Politician': trade.get('politician', 'N/A'),
                'Chamber': trade.get('chamber', 'N/A'),
                'Party': trade.get('party', 'N/A'),
                'State': trade.get('state', 'N/A'),
                'Date': format_date(trade.get('transaction_date')),
                'Type': trade.get('type', 'N/A'),
                'Amount': trade.get('amount', 'N/A'),
                'Score': score_display,
                'AI Reasoning': reasoning_short,
                'Owner': trade.get('owner', 'N/A'),
                '_trade_label': trade_label,
                '_full_reasoning': reasoning if reasoning else ''
            })
        
        # Add full reasoning as hidden column for tooltips
        for row in df_data:
            row['_tooltip'] = row['_full_reasoning'] if row['_full_reasoning'] else row['AI Reasoning']
            row['_click_action'] = 'details'  # Default action is showing details
        
        # Convert to pandas DataFrame (keep _tooltip column for AgGrid)
        df = pd.DataFrame([{k: v for k, v in row.items() if k != '_trade_label' and k != '_full_reasoning'} for row in df_data])
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(df)
        
        # Configure columns
        # Make Ticker column clickable with custom cell renderer
        # Use class-based renderer from aggrid_utils to avoid HTML string escaping issues
        gb.configure_column(
            "Ticker", 
            width=80, 
            pinned='left',
            cellRenderer=JsCode(TICKER_CELL_RENDERER_JS)
        )
        gb.configure_column("Company", width=200)
        gb.configure_column("Politician", width=180)
        gb.configure_column("Chamber", width=90)
        gb.configure_column("Party", width=80)
        gb.configure_column("State", width=70)
        gb.configure_column("Date", width=110)
        gb.configure_column("Type", width=90)
        gb.configure_column("Amount", width=120)
        gb.configure_column("Score", width=100)
        gb.configure_column("Owner", width=100)
        
        # Hide the tooltip column
        gb.configure_column("_tooltip", hide=True)
        gb.configure_column("_click_action", hide=True)
        
        # Configure AI Reasoning column - single line with tooltip
        gb.configure_column(
            "AI Reasoning",
            width=400,
            wrapText=False,  # No wrapping - single line only
            autoHeight=False,  # Fixed height rows
            tooltipField="_tooltip",  # Show full text from hidden column in tooltip
            cellStyle={
                'white-space': 'nowrap',  # Single line
                'overflow': 'hidden',  # Hide overflow
                'text-overflow': 'ellipsis'  # Show ... for truncated text
            }
        )
        
        # Grid options
        gb.configure_default_column(editable=False, groupable=False)
        gb.configure_selection(selection_mode="multiple", use_checkbox=False)
        gb.configure_grid_options(
            enableRangeSelection=True,
            enableCellTextSelection=True,
            ensureDomOrder=True,
            domLayout='normal',
            pagination=True,
            paginationPageSize=100,
            suppressRowClickSelection=True
        )
        
        gridOptions = gb.build()
        
        gridOptions['paginationPageSizeSelector'] = [100, 250, 500, 1000]
        
        # Add global click handler to manage navigation vs selection
        # This will set _click_action in the row data before selection
        gridOptions['onCellClicked'] = JsCode(GLOBAL_CLICK_HANDLER_JS)

        
        # Display AgGrid
        AgGrid(
            df,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.SELECTION_CHANGED | GridUpdateMode.VALUE_CHANGED,
            fit_columns_on_grid_load=False,
            height=600,  # Increased height since we removed pagination controls
            theme='streamlit',
            allow_unsafe_jscode=True,  # Enable for custom cell renderer
            enable_enterprise_modules=False
        )
        
        
        # Handle ticker navigation from selection (automatic, no button needed)
        try:
            selected_data = grid_response.get('selected_rows', pd.DataFrame())
            if not selected_data.empty:
                # Get first selected row
                selected_row = selected_data.iloc[0].to_dict()
                ticker = selected_row.get('Ticker')
                click_action = selected_row.get('_click_action', 'details')
                
                # Only navigate if action is 'navigate' (clicked Ticker)
                if click_action == 'navigate' and ticker and ticker != 'N/A':
                    st.session_state['selected_ticker'] = ticker
                    st.switch_page("pages/ticker_details.py")
        except Exception as nav_error:
            pass  # Silently ignore navigation errors
        
        # Show full AI reasoning for selected row
        try:
            selected_data = grid_response.get('selected_rows', pd.DataFrame())
            if not selected_data.empty:
                # Convert DataFrame to dict for first selected row
                selected_row = selected_data.iloc[0].to_dict()
                full_reasoning = selected_row.get('_tooltip', '')
                
                if full_reasoning:
                    st.markdown("---")
                    st.subheader("📋 Full AI Reasoning (Click to Copy)")
                    
                    # Display trade details
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.markdown(f"**Ticker:** {selected_row.get('Ticker', 'N/A')}")
                        st.markdown(f"**Company:** {selected_row.get('Company', 'N/A')}")
                    with col2:
                        st.markdown(f"**Politician:** {selected_row.get('Politician', 'N/A')}")
                        st.markdown(f"**Date:** {selected_row.get('Date', 'N/A')}")
                    with col3:
                        st.markdown(f"**Type:** {selected_row.get('Type', 'N/A')}")
                        st.markdown(f"**Score:** {selected_row.get('Score', 'N/A')}")
                    
                    # Display full reasoning in code block (easy to select and copy)
                    st.code(full_reasoning, language=None)
        except Exception as e:
            # Silently ignore selection errors - just don't show the section
            pass

        
        st.markdown("---")
        

        
    else:
        st.info("""
        📭 No congress trades found matching the current filters.
        
        Try adjusting your filter criteria or check back later when more data is available.
        """)

except Exception as e:
    logger.error(f"Error in congress trades page: {e}", exc_info=True)
    st.error(f"❌ An error occurred: {str(e)}")
    st.info("Please check the logs or contact an administrator.")

