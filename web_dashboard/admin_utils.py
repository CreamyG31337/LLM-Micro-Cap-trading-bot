#!/usr/bin/env python3
"""
Shared Admin Utilities
=====================

Common functions and utilities used across admin pages.
Extracted from admin.py to enable code reuse and maintainability.
"""

import streamlit as st
import sys
import time
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from typing import Dict, List, Optional
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from streamlit_utils import get_supabase_client, CACHE_VERSION

# Import log_handler to register PERF logging level
try:
    import log_handler  # noqa: F401 - Import to register PERF level
except ImportError:
    pass

# Performance logging setup
logger = logging.getLogger(__name__)


@contextmanager
def perf_timer(operation_name: str, log_to_console: bool = True):
    """Context manager for timing operations."""
    # Initialize performance tracking in session state if needed
    if 'perf_log' not in st.session_state:
        st.session_state.perf_log = []
    
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        entry = {
            'operation': operation_name,
            'time_ms': round(elapsed * 1000, 2),
            'timestamp': datetime.now().isoformat()
        }
        st.session_state.perf_log.append(entry)
        if log_to_console:
            logger.perf(f"⏱️ {operation_name}: {entry['time_ms']}ms")


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_funds():
    """Get all funds from database with caching."""
    with perf_timer("get_cached_funds"):
        client = get_supabase_client()
        if not client:
            return []
        try:
            with perf_timer("DB: funds.select", log_to_console=False):
                funds_result = client.supabase.table("funds").select("*").order("name").execute()
            return funds_result.data if funds_result.data else []
        except Exception as e:
            logger.error(f"Error loading funds: {e}")
            return []


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_fund_names():
    """Get fund names only (lighter query)."""
    funds = get_cached_funds()
    return [f['name'] for f in funds]


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_users():
    """Get all users with their fund assignments."""
    with perf_timer("get_cached_users"):
        client = get_supabase_client()
        if not client:
            return []
        try:
            with perf_timer("DB: list_users_with_funds RPC", log_to_console=False):
                result = client.supabase.rpc('list_users_with_funds').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            return []


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_cached_contributors():
    """Get all contributors from database."""
    with perf_timer("get_cached_contributors"):
        client = get_supabase_client()
        if not client:
            return []
        try:
            with perf_timer("DB: contributors.select", log_to_console=False):
                result = client.supabase.table("contributors").select("id, name, email").order("name").execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error loading contributors: {e}")
            return []


@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_fund_statistics_batched(fund_names: List[str], _cache_version: str = CACHE_VERSION):
    """Get position and trade counts for multiple funds in batched queries.
    
    Args:
        fund_names: List of fund names to get statistics for
        _cache_version: Cache key version (auto-set from CACHE_VERSION constant)
        
    Returns:
        Dict mapping fund_name to {"positions": int, "trades": int}
    """
    if not fund_names:
        return {}
    
    client = get_supabase_client()
    if not client:
        return {fund: {"positions": 0, "trades": 0} for fund in fund_names}
    
    stats = {fund: {"positions": 0, "trades": 0} for fund in fund_names}
    
    try:
        # Batch query 1: Get all position counts (with pagination support)
        with perf_timer("DB: portfolio_positions.count(batched)", log_to_console=False):
            # Fetch all positions for all funds, then group in Python
            # Use .in_() to filter by multiple funds
            # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
            all_positions = []
            batch_size = 1000
            offset = 0
            
            while True:
                result = client.supabase.table("portfolio_positions")\
                    .select("fund")\
                    .in_("fund", fund_names)\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not result.data:
                    break
                
                all_positions.extend(result.data)
                
                # If we got fewer rows than batch_size, we're done
                if len(result.data) < batch_size:
                    break
                
                offset += batch_size
                
                # Safety break to prevent infinite loops (e.g. max 50k rows = 50 batches)
                if offset > 50000:
                    logger.warning("Reached 50,000 row safety limit in get_fund_statistics_batched positions pagination")
                    break
            
            # Group by fund
            if all_positions:
                from collections import Counter
                position_counts = Counter(pos['fund'] for pos in all_positions)
                for fund, count in position_counts.items():
                    if fund in stats:
                        stats[fund]["positions"] = count
        
        # Batch query 2: Get all trade counts (with pagination support)
        with perf_timer("DB: trade_log.count(batched)", log_to_console=False):
            all_trades = []
            batch_size = 1000
            offset = 0
            
            while True:
                result = client.supabase.table("trade_log")\
                    .select("fund")\
                    .in_("fund", fund_names)\
                    .range(offset, offset + batch_size - 1)\
                    .execute()
                
                if not result.data:
                    break
                
                all_trades.extend(result.data)
                
                # If we got fewer rows than batch_size, we're done
                if len(result.data) < batch_size:
                    break
                
                offset += batch_size
                
                # Safety break to prevent infinite loops (e.g. max 50k rows = 50 batches)
                if offset > 50000:
                    logger.warning("Reached 50,000 row safety limit in get_fund_statistics_batched trades pagination")
                    break
            
            # Group by fund
            if all_trades:
                from collections import Counter
                trade_counts = Counter(trade['fund'] for trade in all_trades)
                for fund, count in trade_counts.items():
                    if fund in stats:
                        stats[fund]["trades"] = count
                        
    except Exception as e:
        logger.error(f"Error getting batched fund statistics: {e}", exc_info=True)
    
    return stats


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_postgres_status_cached(_cache_version: str = CACHE_VERSION):
    """Get Postgres connection status and stats.
    
    Args:
        _cache_version: Cache key version (auto-set from CACHE_VERSION constant)
        
    Returns:
        Tuple of (connected: bool, stats: dict or None)
    """
    try:
        from postgres_client import PostgresClient
        
        pg_client = PostgresClient()
        if not pg_client.test_connection():
            return False, None
        
        stats_result = pg_client.execute_query("SELECT COUNT(*) as count FROM research_articles")
        recent_result = pg_client.execute_query("""
            SELECT COUNT(*) as count 
            FROM research_articles 
            WHERE fetched_at >= NOW() - INTERVAL '7 days'
        """)
        
        stats = {
            "total": stats_result[0]['count'] if stats_result else 0,
            "recent_7d": recent_result[0]['count'] if recent_result else 0
        }
        return True, stats
    except ImportError:
        return False, None
    except Exception as e:
        logger.error(f"Error getting Postgres status: {e}", exc_info=True)
        return False, None


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_system_status_cached(_cache_version: str = CACHE_VERSION):
    """Get system status information with caching.
    
    Args:
        _cache_version: Cache key version (auto-set from CACHE_VERSION constant)
    
    Returns:
        Dict with status information for database, exchange rates, metrics, postgres
    """
    client = get_supabase_client()
    status = {
        "supabase_connected": False,
        "exchange_rates": None,
        "postgres_connected": False,
        "postgres_stats": None,
        "errors": []
    }
    
    if not client:
        status["errors"].append("Supabase client not available")
        return status
    
    # Test Supabase connection
    try:
        with perf_timer("DB: user_profiles connection test (cached)", log_to_console=False):
            test_result = client.supabase.table("user_profiles").select("user_id").limit(1).execute()
        status["supabase_connected"] = True
    except Exception as e:
        status["errors"].append(f"Supabase connection error: {e}")
    
    # Check exchange rates
    try:
        with perf_timer("DB: exchange_rates.select (cached)", log_to_console=False):
            rates_result = client.supabase.table("exchange_rates").select("timestamp")\
                .order("timestamp", desc=True).limit(1).execute()
        if rates_result.data:
            status["exchange_rates"] = rates_result.data[0]['timestamp']
    except Exception as e:
        status["errors"].append(f"Exchange rates error: {e}")
    
    # Check Postgres (separate cache with shorter TTL)
    status["postgres_connected"], status["postgres_stats"] = get_postgres_status_cached()
    
    return status
