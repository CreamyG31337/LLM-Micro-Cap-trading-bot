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
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode


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

# Function to render congress trades table with tooltips
def render_congress_trades_table(df_data: List[Dict[str, Any]]) -> str:
    """Render congress trades as complete HTML document with tooltip support and sorting
    
    Args:
        df_data: List of dictionaries with trade data (includes '_full_reasoning' for tooltips)
        
    Returns:
        Complete HTML document string for rendering in iframe
    """
    import html
    
    # Start building complete HTML document
    html_parts = ['<!DOCTYPE html>']
    html_parts.append('<html>')
    html_parts.append('<head>')
    html_parts.append('<meta charset="UTF-8">')
    html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    html_parts.append('<style>')
    
    # Embedded CSS
    html_parts.append("""
    body {
        margin: 0;
        padding: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background-color: transparent;
    }
    
    /* Congress Trades Table Styling */
    .congress-trades-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.9rem;
        background-color: #ffffff;
        color: #262730;
    }
    
    .congress-trades-table th {
        background-color: #f0f2f6;
        padding: 0.75rem;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid rgba(128, 128, 128, 0.2);
        position: sticky;
        top: 0;
        z-index: 10;
    }
    
    .congress-trades-table td {
        padding: 0.75rem;
        border-bottom: 1px solid rgba(128, 128, 128, 0.1);
    }
    
    .congress-trades-table tr:hover {
        background-color: #f0f2f6;
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .congress-trades-table {
            background-color: #0e1117;
            color: #fafafa;
        }
        
        .congress-trades-table th {
            background-color: #262730;
            border-bottom-color: rgba(255, 255, 255, 0.1);
        }
        
        .congress-trades-table td {
            border-bottom-color: rgba(255, 255, 255, 0.1);
        }
        
        .congress-trades-table tr:hover {
            background-color: #262730;
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
    
    /* Show tooltip on hover (desktop) */
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
        margin: 0;
    }

    /* Column sorting styles */
    .congress-trades-table th {
        cursor: pointer;
        user-select: none;
        position: relative;
        transition: background-color 0.2s ease;
    }

    .congress-trades-table th:hover {
        background-color: #e6f3ff !important;
    }

    .congress-trades-table th.sortable {
        padding-right: 1.5rem;
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
            background-color: #3d3d3d !important;
        }
    }
    """)
    
    html_parts.append('</style>')
    html_parts.append('</head>')
    html_parts.append('<body>')
    html_parts.append('<div class="table-container">')
    html_parts.append('<table class="congress-trades-table">')
    
    # Table header with sorting
    html_parts.append('<thead><tr>')
    columns = ['Ticker', 'Company', 'Politician', 'Chamber', 'Party', 'State',
               'Transaction Date', 'Type', 'Amount', 'Conflict Score', 'AI Reasoning', 'Owner']

    # Define sortable columns
    sortable_columns = ['Ticker', 'Company', 'Politician', 'Chamber', 'Party', 'State',
                       'Transaction Date', 'Type', 'Amount', 'Conflict Score', 'Owner']

    for col in columns:
        if col in sortable_columns:
            html_parts.append(f'<th class="sortable" data-column="{html.escape(col)}">{html.escape(col)}<span class="sort-indicator"></span></th>')
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
    
    # Embedded JavaScript
    html_parts.append('<script>')
    html_parts.append("""
    (function() {
        let touchStartTime = 0;
        let touchStartTarget = null;

        // Table sorting functionality
        let currentSortColumn = null;
        let currentSortDirection = 'asc';

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
                currentSortColumn = null;
                currentSortDirection = null;
                return;
            }

            // Sort rows
            rows.sort((a, b) => {
                const aCell = getCellValue(a, columnName);
                const bCell = getCellValue(b, columnName);

                let result = 0;

                if (columnName === 'Conflict Score') {
                    const aVal = extractScoreValue(aCell);
                    const bVal = extractScoreValue(bCell);
                    result = aVal - bVal;
                } else if (columnName === 'Transaction Date') {
                    const aDate = parseDate(aCell);
                    const bDate = parseDate(bCell);
                    result = aDate - bDate;
                } else if (columnName === 'Amount') {
                    const aVal = parseFloat(aCell.replace(/[$,]/g, '')) || 0;
                    const bVal = parseFloat(bCell.replace(/[$,]/g, '')) || 0;
                    result = aVal - bVal;
                } else {
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
            const match = scoreText.match(/(\\d+\\.\\d+)/);
            return match ? parseFloat(match[1]) : -1;
        }

        function parseDate(dateText) {
            if (!dateText || dateText === 'N/A') return new Date(0);
            return new Date(dateText);
        }

        function cycleSort(columnName) {
            if (currentSortColumn === columnName) {
                if (currentSortDirection === 'asc') {
                    sortTable(columnName, 'desc');
                } else if (currentSortDirection === 'desc') {
                    sortTable(columnName, null);
                } else {
                    sortTable(columnName, 'asc');
                }
            } else {
                sortTable(columnName, 'asc');
            }
        }
        
        function positionTooltip(cell, tooltip) {
            tooltip.style.visibility = 'hidden';
            tooltip.style.opacity = '1';
            tooltip.style.display = 'block';
            
            const cellRect = cell.getBoundingClientRect();
            const viewportHeight = window.innerHeight;
            const viewportWidth = window.innerWidth;
            
            void tooltip.offsetWidth;
            
            const tooltipRect = tooltip.getBoundingClientRect();
            const tooltipHeight = tooltipRect.height;
            const tooltipWidth = tooltipRect.width;
            
            const spaceAbove = cellRect.top;
            const spaceBelow = viewportHeight - cellRect.bottom;
            const padding = 10;
            
            let top, left;
            let positionAbove = true;
            
            if (spaceAbove >= tooltipHeight + padding) {
                top = -tooltipHeight - padding;
                positionAbove = true;
            } else if (spaceBelow >= tooltipHeight + padding) {
                top = cellRect.height + padding;
                positionAbove = false;
            } else {
                if (spaceAbove > spaceBelow) {
                    const maxTop = -(cellRect.top - padding);
                    top = Math.max(-tooltipHeight - padding, maxTop);
                    positionAbove = true;
                } else {
                    const maxBottom = viewportHeight - cellRect.bottom - padding;
                    top = Math.min(cellRect.height + padding, maxBottom);
                    positionAbove = false;
                }
            }
            
            left = (cellRect.width / 2) - (tooltipWidth / 2);
            
            const cellLeft = cellRect.left;
            if (cellLeft + left < padding) {
                left = padding - cellLeft;
            } else if (cellLeft + left + tooltipWidth > viewportWidth - padding) {
                left = viewportWidth - padding - cellLeft - tooltipWidth;
            }
            
            tooltip.style.top = top + 'px';
            tooltip.style.left = left + 'px';
            tooltip.style.bottom = 'auto';
            tooltip.style.right = 'auto';
            tooltip.style.transform = 'none';
            
            if (positionAbove) {
                tooltip.setAttribute('data-placement', 'above');
            } else {
                tooltip.setAttribute('data-placement', 'below');
            }
            
            tooltip.style.visibility = '';
            tooltip.style.opacity = '';
            tooltip.style.display = '';
        }
        
        function copyReasoningToClipboard(reasoningCell) {
            let fullReasoning = reasoningCell.getAttribute('data-full-reasoning-b64');
            let decodedText;
            
            if (fullReasoning) {
                try {
                    decodedText = atob(fullReasoning);
                } catch (e) {
                    console.error('Failed to decode base64 reasoning:', e);
                    return false;
                }
            } else {
                fullReasoning = reasoningCell.getAttribute('data-full-reasoning');
                if (!fullReasoning) {
                    console.warn('No data-full-reasoning attribute found');
                    return false;
                }
                const textarea = document.createElement('textarea');
                textarea.innerHTML = fullReasoning;
                decodedText = textarea.value || fullReasoning;
            }

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(decodedText).then(function() {
                    showCopyFeedback(reasoningCell);
                }).catch(function(err) {
                    console.warn('Failed to copy text: ', err);
                    fallbackCopyTextToClipboard(decodedText);
                    showCopyFeedback(reasoningCell);
                });
            } else {
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

            const hasFullReasoning = reasoningCell.hasAttribute('data-full-reasoning-b64') || 
                                     reasoningCell.hasAttribute('data-full-reasoning');
            if (hasFullReasoning) {
                const copied = copyReasoningToClipboard(reasoningCell);
                if (copied) {
                    return;
                }
            }

            document.querySelectorAll('.reasoning-cell.active').forEach(function(activeCell) {
                if (activeCell !== reasoningCell) {
                    activeCell.classList.remove('active');
                }
            });

            const isActive = reasoningCell.classList.toggle('active');
            const tooltip = reasoningCell.querySelector('.reasoning-tooltip');

            if (isActive && tooltip) {
                setTimeout(function() {
                    positionTooltip(reasoningCell, tooltip);
                }, 10);
            }
        }
        
        function setupHoverHandlers() {
            document.querySelectorAll('.reasoning-cell').forEach(function(cell) {
                const tooltip = cell.querySelector('.reasoning-tooltip');
                if (tooltip && !cell.hasAttribute('data-hover-setup')) {
                    cell.setAttribute('data-hover-setup', 'true');
                    
                    cell.addEventListener('mouseenter', function() {
                        requestAnimationFrame(function() {
                            positionTooltip(cell, tooltip);
                        });
                    });
                }
            });
        }

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
            
            document.addEventListener('click', function(e) {
                const reasoningCell = e.target.closest('.reasoning-cell');

                if (reasoningCell) {
                    e.stopPropagation();

                    const hasFullReasoning = reasoningCell.hasAttribute('data-full-reasoning-b64') || 
                                             reasoningCell.hasAttribute('data-full-reasoning');
                    if (hasFullReasoning) {
                        copyReasoningToClipboard(reasoningCell);
                    } else {
                        handleTooltipToggle(e, reasoningCell);
                    }
                } else {
                    document.querySelectorAll('.reasoning-cell.active').forEach(function(activeCell) {
                        activeCell.classList.remove('active');
                    });
                }
            });

            setupHoverHandlers();
            setupColumnSorting();
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initTooltips);
        } else {
            initTooltips();
        }
    })();
    """)
    html_parts.append('</script>')
    html_parts.append('</body>')
    html_parts.append('</html>')
    
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
        
        # Convert to pandas DataFrame (keep _tooltip column for AgGrid)
        df = pd.DataFrame([{k: v for k, v in row.items() if k != '_trade_label' and k != '_full_reasoning'} for row in df_data])
        
        # Configure AgGrid
        gb = GridOptionsBuilder.from_dataframe(df)
        
        # Configure columns
        gb.configure_column("Ticker", width=80, pinned='left')
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
            paginationPageSize=100
        )
        
        gridOptions = gb.build()
        
        # Set page size selector options directly (not supported by configure_grid_options)
        gridOptions['paginationPageSizeSelector'] = [100, 250, 500, 1000]

        
        # Display AgGrid
        grid_response = AgGrid(
            df,
            gridOptions=gridOptions,
            update_mode=GridUpdateMode.SELECTION_CHANGED,
            fit_columns_on_grid_load=False,
            height=600,  # Increased height since we removed pagination controls
            theme='streamlit',
            allow_unsafe_jscode=False,
            enable_enterprise_modules=False
        )
        
        # Handle ticker navigation from selection
        try:
            selected_data = grid_response.get('selected_rows', pd.DataFrame())
            if not selected_data.empty:
                # Get first selected row
                selected_row = selected_data.iloc[0].to_dict()
                ticker = selected_row.get('Ticker')
                
                # If ticker exists and user wants to navigate, show button
                if ticker and ticker != 'N/A':
                    st.info(f"💡 **Tip**: To view details for **{ticker}**, click the button below")
                    if st.button(f"📊 View {ticker} Details", key="nav_ticker", type="primary"):
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

