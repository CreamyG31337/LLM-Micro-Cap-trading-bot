"""
Flask Data Utilities
====================

Flask-compatible data access functions that do NOT import Streamlit.
These mirror the functionality in streamlit_utils.py but work in Flask context.
"""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from supabase_client import SupabaseClient
from flask_auth_utils import get_user_id_flask
from flask_cache_utils import cache_data

logger = logging.getLogger(__name__)


def get_supabase_client_flask() -> Optional[SupabaseClient]:
    """Get Supabase client for Flask context WITH user token for RLS
    
    This passes the user's JWT from the auth_token cookie to SupabaseClient,
    which sets the Authorization header so RLS policies work correctly.
    """
    try:
        from flask_auth_utils import get_auth_token, get_refresh_token
        
        # Get the user's JWT token from cookies
        user_token = get_auth_token()
        refresh_token = get_refresh_token()
        
        if not user_token:
            logger.warning("[get_supabase_client_flask] No auth_token cookie found - RLS queries will fail!")
            # Return client anyway, but queries on RLS tables will return empty
            return SupabaseClient()
        
        logger.debug(f"[get_supabase_client_flask] Creating client with user token (length: {len(user_token)})")
        return SupabaseClient(user_token=user_token, refresh_token=refresh_token)
        
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}", exc_info=True)
        return None


@cache_data(ttl=300)
def get_available_funds_flask() -> List[str]:
    """Get list of available funds for current Flask user (cached 5min)"""
    try:
        user_id = get_user_id_flask()
        if not user_id:
            logger.warning("[get_available_funds_flask] No user_id in Flask session/cookie")
            return []
        
        logger.info(f"[get_available_funds_flask] Looking up funds for user_id: {user_id[:8]}...")
            
        client = get_supabase_client_flask()
        if not client:
            logger.error("[get_available_funds_flask] Failed to create Supabase client")
            return []
            
        result = client.supabase.table("user_funds").select("fund_name").eq("user_id", user_id).execute()
        
        if result and result.data:
            funds = [row.get('fund_name') for row in result.data if row.get('fund_name')]
            logger.info(f"[get_available_funds_flask] Found {len(funds)} funds: {funds}")
            return sorted(funds)
        
        logger.warning(f"[get_available_funds_flask] No funds found for user_id: {user_id[:8]}...")
        return []
    except Exception as e:
        logger.error(f"[get_available_funds_flask] Exception: {e}", exc_info=True)
        return []


@cache_data(ttl=300)
def get_current_positions_flask(fund: Optional[str] = None, _cache_version: Optional[str] = None) -> pd.DataFrame:
    """Get current positions for Flask (cached 5min, with cache_version support)"""
    if _cache_version is None:
        try:
            from cache_version import get_cache_version
            _cache_version = get_cache_version()
        except ImportError:
            _cache_version = ""
    client = get_supabase_client_flask()
    if not client:
        return pd.DataFrame()
        
    try:
        logger.info(f"Loading current positions (Flask) for fund: {fund}")
        
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            # Join with securities table to get sector, industry, market_cap, country for filtering
            query = client.supabase.table("latest_positions").select(
                "*, securities(company_name, sector, industry, market_cap, country)"
            )
            if fund:
                query = query.eq("fund", fund)
                
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
                
            all_rows.extend(result.data)
            
            if len(result.data) < batch_size:
                break
                
            offset += batch_size
            if offset > 50000:
                logger.warning("Position fetch limit reached")
                break
                
        if all_rows:
            df = pd.DataFrame(all_rows)
            
            # Flatten nested securities data (same as streamlit_utils.py)
            if 'securities' in df.columns:
                securities_df = pd.json_normalize(df['securities'])
                if not securities_df.empty:
                    # Merge sector and industry from securities, prefer securities currency if available
                    for col in ['sector', 'industry', 'market_cap', 'country', 'company_name']:
                        if col in securities_df.columns:
                            df[col] = securities_df[col]
                    
                    if 'currency' in securities_df.columns:
                        # Use securities currency if available, otherwise use position currency
                        df['currency'] = securities_df['currency'].fillna(df.get('currency', 'USD'))
                df = df.drop(columns=['securities'], errors='ignore')
            
            return df
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting positions (Flask): {e}", exc_info=True)
        return pd.DataFrame()


@cache_data(ttl=None)  # Cache forever - historical trades don't change
def get_trade_log_flask(limit: int = 1000, fund: Optional[str] = None, _cache_version: Optional[str] = None) -> pd.DataFrame:
    """Get trade log for Flask (cached forever, with cache_version support)"""
    if _cache_version is None:
        try:
            from cache_version import get_cache_version
            _cache_version = get_cache_version()
        except ImportError:
            _cache_version = ""
    client = get_supabase_client_flask()
    if not client:
        return pd.DataFrame()
        
    try:
        if fund:
            logger.info(f"Loading trade log (Flask) for fund: {fund}")
            
        result = client.get_trade_log(limit=limit, fund=fund)
        
        if result:
            df = pd.DataFrame(result)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            return df
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Error getting trade log (Flask): {e}", exc_info=True)
        return pd.DataFrame()


@cache_data(ttl=300)
def get_cash_balances_flask(fund: Optional[str] = None, _cache_version: Optional[str] = None) -> Dict[str, float]:
    """Get cash balances by currency for Flask (cached 5min, with cache_version support)"""
    if _cache_version is None:
        try:
            from cache_version import get_cache_version
            _cache_version = get_cache_version()
        except ImportError:
            _cache_version = ""
    client = get_supabase_client_flask()
    if not client:
        return {"CAD": 0.0, "USD": 0.0}
    
    try:
        if fund:
            logger.info(f"Loading cash balances (Flask) for fund: {fund}")
        
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("cash_balances").select("*")
            if fund:
                query = query.eq("fund", fund)
            
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            all_rows.extend(result.data)
            
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            if offset > 50000:
                logger.warning("Cash balances fetch limit reached")
                break
        
        balances = {"CAD": 0.0, "USD": 0.0}
        if all_rows:
            for row in all_rows:
                currency = row.get('currency', 'CAD')
                amount = float(row.get('balance', 0))
                balances[currency] = balances.get(currency, 0) + amount
        
        return balances
    except Exception as e:
        logger.error(f"Error getting cash balances (Flask): {e}", exc_info=True)
        return {"CAD": 0.0, "USD": 0.0}


@cache_data(ttl=3600)  # Cache for 1 hour - thesis changes infrequently
def get_fund_thesis_data_flask(fund_name: str) -> Optional[Dict[str, Any]]:
    """Get thesis data for a fund from the database view (Flask version, cached 1hr)"""
    client = get_supabase_client_flask()
    if not client:
        return None
    
    try:
        result = client.supabase.table("fund_thesis_with_pillars")\
            .select("*")\
            .eq("fund", fund_name)\
            .execute()
        
        if not result.data:
            return None
        
        first_row = result.data[0]
        
        pillars = []
        for row in result.data:
            if row.get('pillar_id') is not None:
                pillars.append({
                    'name': row.get('pillar_name', ''),
                    'allocation': row.get('allocation', ''),
                    'thesis': row.get('pillar_thesis', ''),
                    'pillar_order': row.get('pillar_order', 0)
                })
        
        pillars.sort(key=lambda x: x.get('pillar_order', 0))
        
        return {
            'fund': first_row.get('fund', fund_name),
            'title': first_row.get('title', ''),
            'overview': first_row.get('overview', ''),
            'pillars': pillars
        }
        
    except Exception as e:
        logger.error(f"Error getting thesis data for {fund_name}: {e}", exc_info=True)
        return None


def calculate_performance_metrics_flask(fund: Optional[str] = None) -> Dict[str, Any]:
    """Calculate key performance metrics (Flask version - simplified)
    
    Returns dict with basic performance metrics.
    Note: This is a simplified version that doesn't do full portfolio value calculation.
    """
    # For now, return empty metrics. Full implementation would require porting
    # calculate_portfolio_value_over_time which is complex.
    return {
        'peak_date': None,
        'peak_gain_pct': 0.0,
        'max_drawdown_pct': 0.0,
        'max_drawdown_date': None,
        'total_return_pct': 0.0,
        'current_value': 0.0,
        'total_invested': 0.0
    }


@cache_data(ttl=300)
def calculate_portfolio_value_over_time_flask(fund: str, days: Optional[int] = None, _cache_version: Optional[str] = None) -> pd.DataFrame:
    """Calculate portfolio value over time (Flask version - simplified, cached 5min)
    
    This is a simplified version that returns basic data.
    The full implementation with currency conversion would need more work.
    """
    if _cache_version is None:
        try:
            from cache_version import get_cache_version
            _cache_version = get_cache_version()
        except ImportError:
            _cache_version = ""
    client = get_supabase_client_flask()
    if not client:
        return pd.DataFrame()
    
    try:
        # Basic query to get portfolio positions over time
        query = client.supabase.table("portfolio_positions").select(
            "date, total_value, cost_basis, pnl"
        )
        
        if fund:
            query = query.eq("fund", fund)
        
        if days:
            from datetime import timedelta
            cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            query = query.gte("date", cutoff)
        
        result = query.order("date").execute()
        
        if not result.data:
            return pd.DataFrame()
        
        df = pd.DataFrame(result.data)
        df['date'] = pd.to_datetime(df['date'])
        
        # Aggregate by date
        daily_totals = df.groupby(df['date'].dt.date).agg({
            'total_value': 'sum',
            'cost_basis': 'sum',
            'pnl': 'sum'
        }).reset_index()
        
        daily_totals.columns = ['date', 'value', 'cost_basis', 'pnl']
        daily_totals['date'] = pd.to_datetime(daily_totals['date'])
        
        # Calculate performance percentage
        daily_totals['performance_pct'] = daily_totals.apply(
            lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0,
            axis=1
        )
        
        daily_totals['performance_index'] = 100 + daily_totals['performance_pct']
        
        return daily_totals.sort_values('date').reset_index(drop=True)
        
    except Exception as e:
        logger.error(f"Error calculating portfolio value over time: {e}", exc_info=True)
        return pd.DataFrame()
