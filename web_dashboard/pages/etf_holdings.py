#!/usr/bin/env python3
"""
ETF Holdings Watchtower
=======================

Streamlit page for viewing ETF holdings tracking data.
Displays daily snapshots, calculates changes between dates, and shows institutional accumulation/distribution signals.
"""

import streamlit as st
import sys
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

from auth_utils import is_authenticated, get_user_email
from navigation import render_navigation
from postgres_client import PostgresClient
from user_preferences import get_user_timezone
from aggrid_utils import TICKER_CELL_RENDERER_JS

logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="ETF Holdings Watchtower",
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

# Initialize PostgreSQL client
@st.cache_resource
def get_postgres_client():
    """Get PostgreSQL client instance"""
    try:
        return PostgresClient()
    except Exception as e:
        logger.warning(f"PostgreSQL not available: {e}")
        return None

postgres_client = get_postgres_client()

# Check if PostgreSQL is available
if postgres_client is None:
    st.error("⚠️ ETF Holdings Database Unavailable")
    st.info("""
    The ETF holdings database is not available. This could be because:
    - PostgreSQL is not configured
    - Database connection failed
    
    Check the logs or contact an administrator for assistance.
    """)
    st.stop()

# Header
st.title("🏛️ ETF Holdings Watchtower")
st.caption(f"Logged in as: {get_user_email()}")

# Description
st.info("""
**Track Institutional Activity** by monitoring daily changes in ETF holdings. The **Diff Engine** detects when ETFs accumulate or distribute positions—signals that often precede significant price movements.

*Increases in shares held are bullish signals, decreases are bearish signals.*
""")

# Initialize session state for refresh
if 'refresh_key' not in st.session_state:
    st.session_state.refresh_key = 0

# Query functions
@st.cache_data(ttl=60, show_spinner=False)
def get_latest_date(_postgres_client, _refresh_key: int) -> Optional[date]:
    """Get latest available date from etf_holdings_log"""
    if _postgres_client is None:
        return None
    try:
        result = _postgres_client.execute_query("SELECT MAX(date) as max_date FROM etf_holdings_log")
        if result and result[0] and result[0].get('max_date'):
            return result[0]['max_date']
        return None
    except Exception as e:
        logger.error(f"Error fetching latest date: {e}")
        return None

@st.cache_data(ttl=60, show_spinner=False)
def get_available_etfs(_postgres_client, _refresh_key: int) -> List[Dict[str, str]]:
    """Get all available ETF tickers with names"""
    if _postgres_client is None:
        return []
    try:
        # Join with securities to get names
        query = """
            SELECT DISTINCT t.etf_ticker, s.name 
            FROM etf_holdings_log t
            LEFT JOIN securities s ON t.etf_ticker = s.ticker
            ORDER BY t.etf_ticker
        """
        result = _postgres_client.execute_query(query)
        if result:
            return [{'ticker': row['etf_ticker'], 'name': row['name'] or row['etf_ticker']} for row in result]
        return []
    except Exception as e:
        logger.error(f"Error fetching available ETFs: {e}")
        return []

@st.cache_data(ttl=60, show_spinner=False)
def get_etf_info(_postgres_client, etf_ticker: str, _refresh_key: int) -> Optional[Dict[str, Any]]:
    """Get ETF information from securities table"""
    if _postgres_client is None or not etf_ticker:
        return None
    try:
        # Match columns to securities table schema
        # Match columns to securities table schema
        result = _postgres_client.execute_query(
            "SELECT ticker, name as company_name, sector, industry, exchange, asset_class, currency, last_updated FROM securities WHERE ticker = %s",
            (etf_ticker,)
        )
        if result and result[0]:
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Error fetching ETF info for {etf_ticker}: {e}")
        return None

@st.cache_data(ttl=60, show_spinner=False)
def get_holdings_changes(
    _postgres_client,
    target_date: date,
    etf_ticker: Optional[str] = None,
    _refresh_key: int = 0
) -> pd.DataFrame:
    """Calculate holdings changes for a specific date compared to previous date"""
    if _postgres_client is None:
        return pd.DataFrame()
    
    try:
        # Build query with optional ETF filter
        query = """
        WITH prev_dates AS (
            SELECT etf_ticker, MAX(date) as prev_date
            FROM etf_holdings_log
            WHERE date < %s
            GROUP BY etf_ticker
        )
        SELECT 
            t1.date as date,
            t1.etf_ticker,
            t1.holding_ticker,
            t1.holding_name,
            COALESCE(t1.shares_held, 0) as current_shares,
            COALESCE(t0.shares_held, 0) as previous_shares,
            CASE 
                WHEN pd.prev_date IS NULL THEN 0 
                ELSE COALESCE(t1.shares_held, 0) - COALESCE(t0.shares_held, 0) 
            END as share_change,
            CASE 
                WHEN pd.prev_date IS NULL THEN NULL
                WHEN COALESCE(t0.shares_held, 0) > 0 
                THEN ((COALESCE(t1.shares_held, 0) - COALESCE(t0.shares_held, 0)) / t0.shares_held * 100)
                ELSE NULL 
            END as percent_change,
            CASE 
                WHEN pd.prev_date IS NULL THEN 'HOLD' -- First snapshot is not a BUY
                WHEN COALESCE(t1.shares_held, 0) > COALESCE(t0.shares_held, 0) THEN 'BUY'
                WHEN COALESCE(t1.shares_held, 0) < COALESCE(t0.shares_held, 0) THEN 'SELL'
                ELSE 'HOLD'
            END as action
        FROM etf_holdings_log t1
        LEFT JOIN prev_dates pd ON t1.etf_ticker = pd.etf_ticker
        LEFT JOIN etf_holdings_log t0 
            ON t1.etf_ticker = t0.etf_ticker 
            AND t1.holding_ticker = t0.holding_ticker
            AND t0.date = pd.prev_date
        WHERE t1.date = %s
          AND (COALESCE(t1.shares_held, 0) > 0 OR COALESCE(t0.shares_held, 0) > 0) -- Hide 0->0 noise
        """
        
        params = [target_date, target_date]
        
        if etf_ticker:
            query += " AND t1.etf_ticker = %s"
            params.append(etf_ticker)
        
        query += " ORDER BY ABS(CASE WHEN pd.prev_date IS NULL THEN 0 ELSE COALESCE(t1.shares_held, 0) - COALESCE(t0.shares_held, 0) END) DESC"
        
        result = _postgres_client.execute_query(query, tuple(params))
        
        if result:
            df = pd.DataFrame(result)
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error fetching holdings changes: {e}", exc_info=True)
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def get_summary_stats(
    _postgres_client,
    target_date: date,
    etf_ticker: Optional[str] = None,
    _refresh_key: int = 0
) -> Dict[str, Any]:
    """Get summary statistics for a specific date"""
    if _postgres_client is None:
        return {}
    
    try:
        changes_df = get_holdings_changes(_postgres_client, target_date, etf_ticker, _refresh_key)
        
        if changes_df.empty:
            return {
                'total_changes': 0,
                'bullish_count': 0,
                'bearish_count': 0,
                'largest_buy': None,
                'largest_sell': None,
                'total_etfs': 0
            }
        
        # Filter out HOLD actions for change counts
        significant_changes = changes_df[changes_df['action'] != 'HOLD'].copy()
        
        bullish = significant_changes[significant_changes['action'] == 'BUY']
        bearish = significant_changes[significant_changes['action'] == 'SELL']
        
        # Find largest buy and sell
        largest_buy = None
        largest_sell = None
        
        if not bullish.empty:
            largest_buy_row = bullish.loc[bullish['share_change'].idxmax()]
            largest_buy = {
                'etf': largest_buy_row['etf_ticker'],
                'ticker': largest_buy_row['holding_ticker'],
                'change': largest_buy_row['share_change']
            }
        
        if not bearish.empty:
            largest_sell_row = bearish.loc[bearish['share_change'].idxmin()]
            largest_sell = {
                'etf': largest_sell_row['etf_ticker'],
                'ticker': largest_sell_row['holding_ticker'],
                'change': largest_sell_row['share_change']
            }
        
        # Count unique ETFs
        total_etfs = changes_df['etf_ticker'].nunique() if 'etf_ticker' in changes_df.columns else 0
        
        return {
            'total_changes': len(significant_changes),
            'bullish_count': len(bullish),
            'bearish_count': len(bearish),
            'largest_buy': largest_buy,
            'largest_sell': largest_sell,
            'total_etfs': total_etfs
        }
    except Exception as e:
        logger.error(f"Error calculating summary stats: {e}", exc_info=True)
        return {}

# Get available data
latest_date = get_latest_date(postgres_client, st.session_state.refresh_key)
available_etf_data = get_available_etfs(postgres_client, st.session_state.refresh_key)
available_tickers = [item['ticker'] for item in available_etf_data]

# Create display mapping
etf_display_map = {item['ticker']: f"{item['ticker']} - {item['name']}" for item in available_etf_data}
etf_display_map["All ETFs"] = "All ETFs"

if not available_etf_data:
    st.warning("⚠️ No ETF holdings data available. Run the ETF Watchtower job to collect data.")
    st.stop()

# Filters Section
st.subheader("Filters")

col1, col2, col3, col4 = st.columns(4)

with col1:
    etf_filter = st.selectbox(
        "ETF Ticker",
        options=["All ETFs"] + available_tickers,
        format_func=lambda x: etf_display_map.get(x, x),
        index=0
    )

with col2:
    holding_ticker_filter = st.text_input(
        "Holding Ticker",
        value="",
        placeholder="Filter by holding ticker..."
    )

with col3:
    if latest_date:
        selected_date = st.date_input(
            "Date",
            value=latest_date,
            max_value=date.today()
        )
    else:
        selected_date = st.date_input(
            "Date",
            value=date.today(),
            max_value=date.today()
        )

with col4:
    action_filter = st.selectbox(
        "Action",
        options=["All", "BUY", "SELL"],
        index=0
    )

# ETF Information Card
if etf_filter != "All ETFs":
    etf_info = get_etf_info(postgres_client, etf_filter, st.session_state.refresh_key)
    if etf_info:
        with st.expander(f"📊 ETF Information: {etf_filter}", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Company Name", etf_info.get('company_name', 'N/A'))
                st.metric("Sector", etf_info.get('sector', 'N/A'))
            with col2:
                st.metric("Industry", etf_info.get('industry', 'N/A'))
                st.metric("Exchange", etf_info.get('exchange', 'N/A'))
            with col3:
                st.metric("Asset Class", etf_info.get('asset_class', 'N/A'))
                st.metric("Currency", etf_info.get('currency', 'N/A'))
            if etf_info.get('last_updated'):
                st.caption(f"Last Updated: {etf_info['last_updated']}")

# Get data for selected filters
selected_etf = None if etf_filter == "All ETFs" else etf_filter
changes_df = get_holdings_changes(postgres_client, selected_date, selected_etf, st.session_state.refresh_key)

# Apply filters
if not changes_df.empty:
    if holding_ticker_filter:
        changes_df = changes_df[changes_df['holding_ticker'].str.contains(holding_ticker_filter.upper(), case=False, na=False)]
    
    if action_filter != "All":
        changes_df = changes_df[changes_df['action'] == action_filter]

# Summary Statistics
st.subheader("Summary Statistics")

if not changes_df.empty:
    # Calculate stats from filtered dataframe
    significant_changes = changes_df[changes_df['action'] != 'HOLD'].copy()
    bullish = significant_changes[significant_changes['action'] == 'BUY']
    bearish = significant_changes[significant_changes['action'] == 'SELL']
    
    # Find largest buy and sell from filtered data
    largest_buy = None
    largest_sell = None
    
    if not bullish.empty:
        largest_buy_idx = bullish['share_change'].idxmax()
        largest_buy_row = bullish.loc[largest_buy_idx]
        largest_buy = {
            'etf': largest_buy_row['etf_ticker'],
            'ticker': largest_buy_row['holding_ticker'],
            'change': largest_buy_row['share_change']
        }
    
    if not bearish.empty:
        largest_sell_idx = bearish['share_change'].idxmin()
        largest_sell_row = bearish.loc[largest_sell_idx]
        largest_sell = {
            'etf': largest_sell_row['etf_ticker'],
            'ticker': largest_sell_row['holding_ticker'],
            'change': largest_sell_row['share_change']
        }
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Latest Update", selected_date.strftime("%Y-%m-%d") if selected_date else "N/A")
    
    with col2:
        st.metric("Total Changes", len(significant_changes))
    
    with col3:
        st.metric("🟢 Bullish (BUY)", len(bullish), delta=None)
    
    with col4:
        st.metric("🔴 Bearish (SELL)", len(bearish), delta=None)
    
    with col5:
        total_etfs = changes_df['etf_ticker'].nunique() if 'etf_ticker' in changes_df.columns else 0
        st.metric("ETFs Tracked", total_etfs)
    
    # Largest moves
    if largest_buy or largest_sell:
        st.caption("**Largest Moves:**")
        col1, col2 = st.columns(2)
        with col1:
            if largest_buy:
                st.success(f"🟢 Largest Buy: {largest_buy['ticker']} ({largest_buy['etf']}) - {largest_buy['change']:+,.0f} shares")
        with col2:
            if largest_sell:
                st.error(f"🔴 Largest Sell: {largest_sell['ticker']} ({largest_sell['etf']}) - {largest_sell['change']:+,.0f} shares")
else:
    st.info("No changes data available for the selected date and filters.")

# Main Data Display - Latest Changes Table
st.subheader("Latest Changes")

if not changes_df.empty:
    # Prepare DataFrame for display - keep numeric columns for sorting, add formatted columns
    display_df = changes_df.copy()
    
    # Format date
    if 'date' in display_df.columns:
        display_df['date'] = pd.to_datetime(display_df['date']).dt.strftime('%Y-%m-%d')
    
    # Keep numeric values for sorting, but format for display
    # Create formatted string columns while keeping numeric originals
    if 'share_change' in display_df.columns:
        display_df['share_change_formatted'] = display_df['share_change'].apply(
            lambda x: f"{x:+,.0f}" if pd.notna(x) and x != 0 else "0"
        )
    
    if 'percent_change' in display_df.columns:
        display_df['percent_change_formatted'] = display_df['percent_change'].apply(
            lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
        )
    
    if 'current_shares' in display_df.columns:
        display_df['current_shares_formatted'] = display_df['current_shares'].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A"
        )
    
    if 'previous_shares' in display_df.columns:
        display_df['previous_shares_formatted'] = display_df['previous_shares'].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else "N/A"
        )
    
    # Rename columns for display
    display_df = display_df.rename(columns={
        'date': 'Date',
        'etf_ticker': 'ETF',
        'holding_ticker': 'Holding Ticker',
        'holding_name': 'Holding Name',
        'action': 'Action',
        'share_change_formatted': 'Share Change',
        'percent_change_formatted': '% Change',
        'previous_shares_formatted': 'Previous Shares',
        'current_shares_formatted': 'Current Shares'
    })
    
    # Reorder columns - only include columns that exist
    column_order = ['Date', 'ETF', 'Holding Ticker', 'Holding Name', 'Action', 'Share Change', '% Change', 'Previous Shares', 'Current Shares']
    available_columns = [col for col in column_order if col in display_df.columns]
    display_df = display_df[available_columns]
    
    # Build AgGrid with color coding
    gb = GridOptionsBuilder.from_dataframe(display_df)
    gb.configure_pagination(paginationPageSize=50)
    gb.configure_side_bar()
    gb.configure_default_column(groupable=True, value=True, enableRowGroup=True, aggFunc='sum', editable=False)
    
    # Configure Share Change column with color coding
    if 'Share Change' in display_df.columns:
        gb.configure_column(
            'Share Change',
            cellStyle=JsCode("""
            function(params) {
                if (params.value && params.value !== 'N/A' && params.value !== '0') {
                    // Parse the formatted value (e.g., "+1,000" or "-500")
                    const cleanValue = params.value.replace(/,/g, '').replace('+', '');
                    const numValue = parseFloat(cleanValue);
                    if (numValue > 0) {
                        return {backgroundColor: '#d4edda', color: '#155724', fontWeight: 'bold'};
                    } else if (numValue < 0) {
                        return {backgroundColor: '#f8d7da', color: '#721c24', fontWeight: 'bold'};
                    }
                }
                return null;
            }
            """)
        )
    
    # Configure Action column with icons
    if 'Action' in display_df.columns:
        gb.configure_column(
            'Action',
            cellStyle=JsCode("""
            function(params) {
                if (params.value === 'BUY') {
                    return {backgroundColor: '#d4edda', color: '#155724', fontWeight: 'bold'};
                } else if (params.value === 'SELL') {
                    return {backgroundColor: '#f8d7da', color: '#721c24', fontWeight: 'bold'};
                }
                return null;
            }
            """)
        )
    
    # Configure Holding Ticker column with clickable cells
    if 'Holding Ticker' in display_df.columns:
        gb.configure_column(
            'Holding Ticker',
            cellRenderer=JsCode(TICKER_CELL_RENDERER_JS)
        )
    
    grid_options = gb.build()
    
    # Display grid
    grid_response = AgGrid(
        display_df,
        gridOptions=grid_options,
        height=600,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        allow_unsafe_jscode=True,
        theme='streamlit'
    )
    
    # Handle ticker navigation
    selected_rows = grid_response.get('selected_rows')
    if selected_rows is not None and len(selected_rows) > 0:
        if isinstance(selected_rows, pd.DataFrame):
            if 'Holding Ticker' in selected_rows.columns:
                ticker = str(selected_rows.iloc[0]['Holding Ticker'])
                if ticker and ticker != 'N/A':
                    st.query_params["ticker"] = ticker
                    st.switch_page("pages/ticker_details.py")
        elif isinstance(selected_rows, list) and len(selected_rows) > 0:
            selected_row = selected_rows[0]
            if isinstance(selected_row, dict) and 'Holding Ticker' in selected_row:
                ticker = str(selected_row['Holding Ticker'])
                if ticker and ticker != 'N/A':
                    st.query_params["ticker"] = ticker
                    st.switch_page("pages/ticker_details.py")
    
    # Export button
    st.download_button(
        label="📥 Download CSV",
        data=changes_df.to_csv(index=False),
        file_name=f"etf_holdings_changes_{selected_date.strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
else:
    st.info("No changes data available for the selected date and filters.")

# Refresh button
if st.button("🔄 Refresh Data"):
    st.session_state.refresh_key += 1
    st.rerun()

