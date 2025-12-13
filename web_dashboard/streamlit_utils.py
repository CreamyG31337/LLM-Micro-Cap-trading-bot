#!/usr/bin/env python3
"""
Streamlit utilities for fetching data from Supabase
"""

import os
from typing import Dict, List, Optional, Any
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    from supabase_client import SupabaseClient
    from auth_utils import get_user_token
except ImportError:
    # Fallback if supabase_client not available
    SupabaseClient = None
    get_user_token = None


def get_supabase_client(user_token: Optional[str] = None) -> Optional[SupabaseClient]:
    """Get Supabase client instance with user authentication
    
    Args:
        user_token: Optional JWT token from authenticated user. If None, tries to get from session.
                   Uses publishable key as fallback (may not work with RLS enabled).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Check if SupabaseClient class is available
    if SupabaseClient is None:
        logger.error("SupabaseClient class is not available - import failed")
        print("ERROR: SupabaseClient import failed. Check that supabase_client.py exists and dependencies are installed.")
        return None
    
    try:
        # Get user token from session if not provided
        if user_token is None and get_user_token:
            user_token = get_user_token()
            if user_token:
                logger.debug("Using user token from session for Supabase client")
            else:
                logger.debug("No user token available, using publishable key fallback")
        
        # Use user token if available (respects RLS)
        client = SupabaseClient(user_token=user_token)
        
        # Validate client was created successfully
        if client is None:
            logger.error("SupabaseClient() returned None")
            print("ERROR: SupabaseClient initialization returned None")
            return None
        
        # Validate required attributes
        if not hasattr(client, 'supabase') or client.supabase is None:
            logger.error("SupabaseClient created but 'supabase' attribute is None")
            print("ERROR: SupabaseClient.supabase is None after initialization")
            return None
        
        logger.debug("Supabase client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Exception initializing Supabase client: {e}", exc_info=True)
        print(f"ERROR: Failed to initialize Supabase client: {e}")
        print("Check that SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY environment variables are set.")
        return None


def get_available_funds() -> List[str]:
    """Get list of available funds from Supabase
    
    Queries user_funds table to get funds assigned to the authenticated user.
    Returns a sorted list of unique fund names.
    """
    print("DEBUG: get_available_funds() called - checking console output")
    
    client = get_supabase_client()
    if not client:
        print("DEBUG: Failed to initialize Supabase client")
        return []
    
    # Get user ID for querying user_funds table
    try:
        from auth_utils import get_user_id
        user_id = get_user_id()
        if not user_id:
            print("DEBUG: No user_id available in session")
            return []
    except Exception as e:
        print(f"DEBUG: Could not get user ID: {e}")
        return []
    
    try:
        result = client.supabase.table("user_funds").select("fund_name").eq("user_id", user_id).execute()
        
        if not result or not result.data:
            print(f"DEBUG: Query returned no data for user_id: {user_id}")
            return []
        
        funds = [row.get('fund_name') for row in result.data if row.get('fund_name')]
        sorted_funds = sorted(funds)
        print(f"DEBUG: Found {len(sorted_funds)} funds: {sorted_funds}")
        return sorted_funds
    except Exception as e:
        print(f"DEBUG: Error querying user_funds: {e}")
        return []


def get_current_positions(fund: Optional[str] = None) -> pd.DataFrame:
    """Get current portfolio positions as DataFrame"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        query = client.supabase.table("latest_positions").select("*")
        if fund:
            query = query.eq("fund", fund)
        result = query.execute()
        
        if result.data:
            return pd.DataFrame(result.data)
        return pd.DataFrame()
    except Exception as e:
        print(f"Error getting positions: {e}")
        return pd.DataFrame()


def get_trade_log(limit: int = 1000, fund: Optional[str] = None) -> pd.DataFrame:
    """Get trade log entries as DataFrame"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        query = client.supabase.table("trade_log").select("*").order("date", desc=True).limit(limit)
        if fund:
            query = query.eq("fund", fund)
        result = query.execute()
        
        if result.data:
            df = pd.DataFrame(result.data)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            return df
        return pd.DataFrame()
    except Exception as e:
        print(f"Error getting trade log: {e}")
        return pd.DataFrame()


def get_cash_balances(fund: Optional[str] = None) -> Dict[str, float]:
    """Get cash balances by currency"""
    client = get_supabase_client()
    if not client:
        return {"CAD": 0.0, "USD": 0.0}
    
    try:
        query = client.supabase.table("cash_balances").select("*")
        if fund:
            query = query.eq("fund", fund)
        result = query.execute()
        
        balances = {"CAD": 0.0, "USD": 0.0}
        if result.data:
            for row in result.data:
                currency = row.get('currency', 'CAD')
                amount = float(row.get('balance', 0))
                balances[currency] = balances.get(currency, 0) + amount
        
        return balances
    except Exception as e:
        print(f"Error getting cash balances: {e}")
        return {"CAD": 0.0, "USD": 0.0}


def calculate_portfolio_value_over_time(fund: str) -> pd.DataFrame:
    """Calculate portfolio value over time from portfolio_positions table.
    
    This queries the portfolio_positions table to get daily snapshots of
    actual market values (shares * price), with proper normalization,
    currency conversion (USD→CAD), and continuous timeline handling.
    
    Args:
        fund: Fund name (REQUIRED - we always filter by fund for performance)
    
    Returns DataFrame with columns:
    - date: datetime
    - value: total market value (in CAD)
    - cost_basis: total cost basis (in CAD)
    - pnl: unrealized P&L (in CAD)
    - performance_pct: P&L as percentage of cost basis
    - performance_index: Normalized to start at 100 (for charting)
    """
    from decimal import Decimal
    
    # Fund is required - fail fast if not provided
    if not fund:
        raise ValueError("Fund name is required - cannot load all funds' data")
    
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        # Query portfolio_positions to get daily snapshots with actual market values
        # Include currency for proper USD→CAD conversion
        
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            # Build query for this batch
            query = client.supabase.table("portfolio_positions").select(
                "date, total_value, cost_basis, pnl, fund, currency"
            )
            
            if fund:
                query = query.eq("fund", fund)
            
            # Order by date to ensure consistent pagination
            # Use range() for pagination
            # Note: range is 0-indexed and inclusive for start, inclusive for end in PostgREST logic usually,
            # but supabase-py .range(start, end) handles it.
            result = query.order("date").range(offset, offset + batch_size - 1).execute()
            
            rows = result.data
            if not rows:
                break
                
            all_rows.extend(rows)
            
            # If we got fewer rows than batch_size, we're done
            if len(rows) < batch_size:
                break
                
            offset += batch_size
            
            # Safety break to prevent infinite loops (e.g. max 50k rows = 50 batches)
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in pagination")
                break
        
        if not all_rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_rows)
        print(f"[DEBUG] Loaded {len(df)} total portfolio position rows from Supabase (paginated)")
        
        # Normalize to date-only (midnight) for consistent charting with benchmarks
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        
        # Log date range for debugging
        if not df.empty:
            min_date = df['date'].min()
            max_date = df['date'].max()
            print(f"[DEBUG] Date range: {min_date.date()} to {max_date.date()}")
        
        # Load exchange rates for currency conversion - NO FALLBACKS, errors are preferred
        from exchange_rates_utils import get_exchange_rate_for_date_from_db, reload_exchange_rate_for_date
        
        # Check if we have any USD positions that need conversion
        has_usd = False
        if 'currency' in df.columns:
            has_usd = df['currency'].str.upper().eq('USD').any()
        
        if has_usd:
            # Get unique dates for exchange rate lookup
            unique_dates = df['date'].dt.date.unique()
            
            # Build exchange rate cache for all dates
            rate_cache = {}
            missing_dates = []
            
            for date_val in unique_dates:
                from datetime import datetime
                dt = datetime.combine(date_val, datetime.min.time())
                rate = get_exchange_rate_for_date_from_db(dt, 'USD', 'CAD')
                
                if rate is None:
                    missing_dates.append(date_val)
                else:
                    rate_cache[date_val] = float(rate)
            
            # If we have missing rates, try to fetch them
            if missing_dates:
                print(f"Missing exchange rates for {len(missing_dates)} dates, attempting to fetch...")
                for date_val in missing_dates:
                    from datetime import datetime, timezone
                    dt = datetime.combine(date_val, datetime.min.time(), tzinfo=timezone.utc)
                    fetched_rate = reload_exchange_rate_for_date(dt, 'USD', 'CAD')
                    
                    if fetched_rate is not None:
                        rate_cache[date_val] = float(fetched_rate)
                        print(f"  ✅ Fetched rate for {date_val}: {fetched_rate}")
                    else:
                        raise ValueError(
                            f"Missing exchange rate for {date_val} and could not fetch from API. "
                            f"Please add exchange rate data for this date."
                        )
            
            # Apply currency conversion to USD positions
            def convert_to_cad(row, column):
                currency = str(row.get('currency', 'CAD')).upper() if pd.notna(row.get('currency')) else 'CAD'
                value = float(row.get(column, 0) or 0)
                
                if currency == 'USD':
                    date_key = row['date'].date() if hasattr(row['date'], 'date') else row['date']
                    rate = rate_cache.get(date_key)
                    if rate is None:
                        raise ValueError(f"No exchange rate found for {date_key}")
                    return value * rate
                return value
            
            df['total_value_cad'] = df.apply(lambda r: convert_to_cad(r, 'total_value'), axis=1)
            df['cost_basis_cad'] = df.apply(lambda r: convert_to_cad(r, 'cost_basis'), axis=1)
            df['pnl_cad'] = df.apply(lambda r: convert_to_cad(r, 'pnl'), axis=1)
            
            value_col = 'total_value_cad'
            cost_col = 'cost_basis_cad'
            pnl_col = 'pnl_cad'
        else:
            # No USD positions, use values as-is (already in CAD)
            value_col = 'total_value'
            cost_col = 'cost_basis'
            pnl_col = 'pnl'
        
        # Aggregate by date to get daily portfolio totals
        # Sum all positions' values for each day
        daily_totals = df.groupby(df['date'].dt.date).agg({
            value_col: 'sum',
            cost_col: 'sum',
            pnl_col: 'sum'
        }).reset_index()
        
        daily_totals.columns = ['date', 'value', 'cost_basis', 'pnl']
        daily_totals['date'] = pd.to_datetime(daily_totals['date'])
        daily_totals = daily_totals.sort_values('date').reset_index(drop=True)
        
        if daily_totals.empty:
            return pd.DataFrame()
        
        # Calculate performance percentage (P&L / cost_basis * 100)
        daily_totals['performance_pct'] = daily_totals.apply(
            lambda row: (row['pnl'] / row['cost_basis'] * 100) if row['cost_basis'] > 0 else 0.0,
            axis=1
        )
        
        # Normalize performance to start at 100 on first trading day
        # This matches the console app's approach for fair benchmark comparison
        first_day_with_investment = daily_totals[daily_totals['cost_basis'] > 0]
        if not first_day_with_investment.empty:
            first_day_performance = first_day_with_investment.iloc[0]['performance_pct']
            # Adjust all performance so first day starts at 0%
            daily_totals['performance_pct'] = daily_totals['performance_pct'] - first_day_performance
        
        # Create Performance Index (baseline 100 + performance %)
        daily_totals['performance_index'] = 100 + daily_totals['performance_pct']
        
        # Create continuous timeline with forward-fill for weekends
        daily_totals = _create_continuous_timeline(daily_totals)
        
        return daily_totals
        
    except Exception as e:
        print(f"Error calculating portfolio value: {e}")
        return pd.DataFrame()


def _create_continuous_timeline(df: pd.DataFrame) -> pd.DataFrame:
    """Create a continuous timeline with forward-fill for weekends/holidays.
    
    This ensures the chart shows a continuous line without gaps, with
    weekend values carried forward from the last trading day.
    """
    if df.empty or 'date' not in df.columns:
        return df
    
    # Get date range
    start_date = df['date'].min()
    end_date = df['date'].max()
    
    # Create complete date range (every day)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Create DataFrame with all dates
    continuous_df = pd.DataFrame({'date': all_dates})
    continuous_df['date_only'] = continuous_df['date'].dt.date
    
    # Prepare original data for merge
    df_for_merge = df.copy()
    df_for_merge['date_only'] = df_for_merge['date'].dt.date
    
    # Merge with all dates
    merged = continuous_df.merge(
        df_for_merge.drop('date', axis=1),
        on='date_only',
        how='left'
    )
    
    # Forward-fill numeric columns (weekend values = last trading day)
    numeric_cols = ['value', 'cost_basis', 'pnl', 'performance_pct', 'performance_index']
    for col in numeric_cols:
        if col in merged.columns:
            merged[col] = merged[col].ffill()
    
    # Drop helper column
    merged = merged.drop('date_only', axis=1)
    
    return merged


def calculate_performance_metrics(fund: Optional[str] = None) -> Dict[str, Any]:
    """Calculate key performance metrics like the console app.
    
    Returns dict with:
    - peak_date: Date of peak performance
    - peak_gain_pct: Peak gain percentage 
    - max_drawdown_pct: Maximum drawdown percentage
    - max_drawdown_date: Date of max drawdown
    - total_return_pct: Current total return
    - current_value: Current portfolio value
    - total_invested: Total cost basis
    """
    df = calculate_portfolio_value_over_time(fund)
    
    if df.empty or 'performance_index' not in df.columns:
        return {
            'peak_date': None,
            'peak_gain_pct': 0.0,
            'max_drawdown_pct': 0.0,
            'max_drawdown_date': None,
            'total_return_pct': 0.0,
            'current_value': 0.0,
            'total_invested': 0.0
        }
    
    try:
        # Peak performance
        peak_idx = df['performance_index'].idxmax()
        peak_date = df.loc[peak_idx, 'date']
        peak_gain_pct = float(df.loc[peak_idx, 'performance_index']) - 100.0
        
        # Max drawdown calculation
        df_sorted = df.sort_values('date').copy()
        df_sorted['running_max'] = df_sorted['performance_index'].cummax()
        df_sorted['drawdown_pct'] = (df_sorted['performance_index'] / df_sorted['running_max'] - 1.0) * 100.0
        
        dd_idx = df_sorted['drawdown_pct'].idxmin()
        max_drawdown_pct = float(df_sorted.loc[dd_idx, 'drawdown_pct'])
        max_drawdown_date = df_sorted.loc[dd_idx, 'date']
        
        # Current stats (last row)
        last_row = df.iloc[-1]
        total_return_pct = float(last_row['performance_pct'])
        current_value = float(last_row['value'])
        total_invested = float(last_row['cost_basis'])
        
        return {
            'peak_date': peak_date,
            'peak_gain_pct': peak_gain_pct,
            'max_drawdown_pct': max_drawdown_pct,
            'max_drawdown_date': max_drawdown_date,
            'total_return_pct': total_return_pct,
            'current_value': current_value,
            'total_invested': total_invested
        }
        
    except Exception as e:
        print(f"Error calculating metrics: {e}")
        return {
            'peak_date': None,
            'peak_gain_pct': 0.0,
            'max_drawdown_pct': 0.0,
            'max_drawdown_date': None,
            'total_return_pct': 0.0,
            'current_value': 0.0,
            'total_invested': 0.0
        }





def get_individual_holdings_performance(fund: str, days: int = 7) -> pd.DataFrame:
    """Get performance data for individual holdings in a fund.
    
    Args:
        fund: Fund name (required)
        days: Number of days to fetch (7, 30, or 0 for all)
        
    Returns:
        DataFrame with columns: ticker, date, shares, price, total_value, performance_index
    """
    from decimal import Decimal
    from datetime import datetime, timedelta, timezone
    
    if not fund:
        raise ValueError("Fund name is required")
    
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        # Calculate date cutoff
        if days > 0:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        else:
            cutoff_str = None  # All time
        
        # Fetch position data with pagination
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("portfolio_positions").select(
                "ticker, date, shares, price, total_value, currency"
            )
            
            query = query.eq("fund", fund)
            
            if cutoff_str:
                query = query.gte("date", f"{cutoff_str}T00:00:00")
            
            result = query.order("date").range(offset, offset + batch_size - 1).execute()
            
            rows = result.data
            if not rows:
                break
            
            all_rows.extend(rows)
            
            if len(rows) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit")
                break
        
        if not all_rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_rows)
        # Normalize to date-only (midnight) for consistent charting
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        
        # Calculate performance index per ticker (baseline 100)
        holdings_performance = []
        
        for ticker in df['ticker'].unique():
            ticker_df = df[df['ticker'] == ticker].copy()
            ticker_df = ticker_df.sort_values('date')
            
            if len(ticker_df) < 1:
                continue
            
            # Use first date's total_value as baseline
            baseline_value = float(ticker_df['total_value'].iloc[0])
            
            if baseline_value == 0:
                continue  # Skip if no valid baseline
            
            # Calculate performance index
            ticker_df['performance_index'] = (ticker_df['total_value'].astype(float) / baseline_value) * 100
            
            holdings_performance.append(ticker_df[['ticker', 'date', 'performance_index']])
        
        if not holdings_performance:
            return pd.DataFrame()
        
        result_df = pd.concat(holdings_performance, ignore_index=True)
        return result_df
        
    except Exception as e:
        print(f"Error fetching individual holdings: {e}")
        return pd.DataFrame()
