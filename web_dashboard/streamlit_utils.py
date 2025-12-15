#!/usr/bin/env python3
"""
Streamlit utilities for fetching data from Supabase
"""

import os
from datetime import datetime
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
    import logging
    logger = logging.getLogger(__name__)
    
    client = get_supabase_client()
    if not client:
        logger.warning("get_available_funds(): Failed to initialize Supabase client")
        return []
    
    # Get user ID for querying user_funds table
    try:
        from auth_utils import get_user_id
        user_id = get_user_id()
        if not user_id:
            logger.debug("get_available_funds(): No user_id available in session")
            return []
    except Exception as e:
        logger.warning(f"get_available_funds(): Could not get user ID: {e}")
        return []
    
    try:
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("user_funds").select("fund_name").eq("user_id", user_id)
            
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result or not result.data:
                break
            
            all_rows.extend(result.data)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in get_available_funds pagination")
                break
        
        if not all_rows:
            logger.debug(f"get_available_funds(): Query returned no data for user_id: {user_id}")
            return []
        
        funds = [row.get('fund_name') for row in all_rows if row.get('fund_name')]
        sorted_funds = sorted(funds)
        logger.debug(f"get_available_funds(): Found {len(sorted_funds)} funds for user_id: {user_id}")
        return sorted_funds
    except Exception as e:
        logger.error(f"get_available_funds(): Error querying user_funds: {e}", exc_info=True)
        return []


def get_current_positions(fund: Optional[str] = None) -> pd.DataFrame:
    """Get current portfolio positions as DataFrame"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("latest_positions").select("*")
            if fund:
                query = query.eq("fund", fund)
            
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            all_rows.extend(result.data)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in get_current_positions pagination")
                break
        
        if all_rows:
            return pd.DataFrame(all_rows)
        return pd.DataFrame()
    except Exception as e:
        print(f"Error getting positions: {e}")
        return pd.DataFrame()


def get_trade_log(limit: int = 1000, fund: Optional[str] = None) -> pd.DataFrame:
    """Get trade log entries as DataFrame with company names from securities table"""
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        # Use client.get_trade_log() which joins with securities table for company names
        result = client.get_trade_log(limit=limit, fund=fund)
        
        if result:
            df = pd.DataFrame(result)
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
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
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
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in get_cash_balances pagination")
                break
        
        balances = {"CAD": 0.0, "USD": 0.0}
        if all_rows:
            for row in all_rows:
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
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Loaded {len(df)} total portfolio position rows from Supabase (paginated)")
        
        # Normalize to date-only (midnight) for consistent charting with benchmarks
        df['date'] = pd.to_datetime(df['date']).dt.normalize()
        
        # Log date range for debugging
        if not df.empty:
            min_date = df['date'].min()
            max_date = df['date'].max()
            logger.debug(f"Date range: {min_date.date()} to {max_date.date()}")
        
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
        # Query for more days than requested to account for weekends and missing days
        # This ensures we get enough data points even when weekends/holidays are present
        if days > 0:
            # Query for at least 50% more days, or +3 days minimum (whichever is larger)
            query_days = max(int(days * 1.5), days + 3)
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=query_days)
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
        
        # If days > 0, filter to the last N unique dates (not calendar days)
        # This ensures we get exactly N data points even when weekends/missing days are present
        if days > 0:
            # Get unique dates, sort descending, take first N
            unique_dates = sorted(result_df['date'].unique(), reverse=True)[:days]
            # Filter DataFrame to only include these dates
            result_df = result_df[result_df['date'].isin(unique_dates)]
            # Sort by date ascending for proper chart display
        return result_df
        
    except Exception as e:
        print(f"Error fetching individual holdings: {e}")
        return pd.DataFrame()


def get_investor_count(fund: str) -> int:
    """Get count of contributors/investors for a fund
    
    Args:
        fund: Fund name
    
    Returns:
        Integer count of contributors
    """
    client = get_supabase_client()
    if not client:
        return 0
    
    try:
        # Query fund_contributor_summary view for total contributor count
        result = client.supabase.table("fund_contributor_summary").select(
            "total_contributors"
        ).eq("fund", fund).execute()
        
        if result.data and len(result.data) > 0:
            return int(result.data[0].get('total_contributors', 0))
        return 0
    except Exception as e:
        print(f"Error getting investor count: {e}")
        return 0


def get_investor_allocations(fund: str, user_email: Optional[str] = None, is_admin: bool = False) -> pd.DataFrame:
    """Get investor allocation data with privacy masking
    
    Args:
        fund: Fund name
        user_email: Current user's email (to show their own name)
        is_admin: Whether current user is admin (admins see all names)
    
    Returns:
        DataFrame with columns: contributor_display, net_contribution, ownership_pct
        - If admin: Shows all real contributor names
        - If regular user: Shows only their name, others masked as "Investor 1", "Investor 2", etc.
    """
    client = get_supabase_client()
    if not client:
        return pd.DataFrame()
    
    try:
        # Query contributor_ownership view to get net contributions
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("contributor_ownership").select(
                "contributor, email, net_contribution"
            ).eq("fund", fund)
            
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            all_rows.extend(result.data)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in get_investor_allocations pagination")
                break
        
        if not all_rows:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_rows)
        
        # Convert net_contribution to float
        df['net_contribution'] = df['net_contribution'].astype(float)
        
        # Sort by contribution amount (descending) for consistent masking
        df = df.sort_values('net_contribution', ascending=False).reset_index(drop=True)
        
        # Calculate ownership percentages
        total_contributions = df['net_contribution'].sum()
        if total_contributions > 0:
            df['ownership_pct'] = (df['net_contribution'] / total_contributions) * 100
        else:
            df['ownership_pct'] = 0.0
        
        # Apply privacy masking
        def mask_name(row, idx):
            if is_admin:
                # Admins see all real names
                return row['contributor']
            else:
                # Regular users see only their own name
                contributor_email = row.get('email', '').lower() if pd.notna(row.get('email')) else ''
                user_email_lower = user_email.lower() if user_email else ''
                
                if contributor_email and user_email_lower and contributor_email == user_email_lower:
                    # Show user's own name
                    return row['contributor']
                else:
                    # Mask as "Investor N" (sorted by contribution amount)
                    return f"Investor {idx + 1}"
        
        df['contributor_display'] = df.apply(lambda row: mask_name(row, row.name), axis=1)
        
        # Return only necessary columns
        return df[['contributor_display', 'net_contribution', 'ownership_pct']]
        
    except Exception as e:
        print(f"Error getting investor allocations: {e}")
        return pd.DataFrame()


def get_historical_fund_values(fund: str, dates: List[datetime]) -> Dict[str, float]:
    """Get historical fund values for specific dates.
    
    Queries portfolio_positions to calculate total fund value at each date.
    Returns the closest available date if exact date not found.
    
    Args:
        fund: Fund name
        dates: List of dates to get fund values for
        
    Returns:
        Dict mapping date string (YYYY-MM-DD) to fund value
    """
    from datetime import datetime
    
    client = get_supabase_client()
    if not client or not dates:
        return {}
    
    try:
        # Get all unique dates we need
        date_strs = sorted(set(d.strftime('%Y-%m-%d') for d in dates if d))
        if not date_strs:
            return {}
        
        min_date = min(date_strs)
        
        # Query portfolio_positions for this fund, from earliest contribution date onwards
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("portfolio_positions").select(
                "date, shares, price, currency"
            ).eq("fund", fund).gte("date", min_date).order("date")
            
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            all_rows.extend(result.data)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops (e.g. max 50k rows = 50 batches)
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in get_historical_fund_values pagination")
                break
        
        if not all_rows:
            return {}
        
        # Get exchange rates for each date we need (use historical rates for accuracy)
        # First, get unique dates from portfolio positions
        position_dates = sorted(set(row['date'][:10] for row in all_rows))
        
        # Fetch historical exchange rates for these dates
        exchange_rates_by_date = {}
        fallback_rate = 1.42  # Default fallback
        try:
            # Get latest rate as fallback
            rate_result = client.get_latest_exchange_rate('USD', 'CAD')
            if rate_result:
                fallback_rate = float(rate_result)
            
            # Try to get historical rates for each date
            for date_str in position_dates:
                try:
                    from datetime import datetime as dt
                    date_obj = dt.strptime(date_str, '%Y-%m-%d')
                    hist_rate = client.get_exchange_rate(date_obj, 'USD', 'CAD')
                    if hist_rate:
                        exchange_rates_by_date[date_str] = float(hist_rate)
                    else:
                        exchange_rates_by_date[date_str] = fallback_rate
                except Exception:
                    exchange_rates_by_date[date_str] = fallback_rate
        except Exception:
            # If we can't get any rates, use fallback for all dates
            for date_str in position_dates:
                exchange_rates_by_date[date_str] = fallback_rate
        
        # Calculate total value for each date using date-specific exchange rates
        values_by_date = {}
        for row in all_rows:
            date_str = row['date'][:10]  # Get just YYYY-MM-DD
            shares = float(row.get('shares', 0))
            price = float(row.get('price', 0))
            currency = row.get('currency', 'USD')
            
            # Convert to CAD using date-specific exchange rate
            value = shares * price
            if currency == 'USD':
                usd_to_cad = exchange_rates_by_date.get(date_str, fallback_rate)
                value *= usd_to_cad
            
            if date_str not in values_by_date:
                values_by_date[date_str] = 0.0
            values_by_date[date_str] += value
        
        # For each requested date, find closest available date
        result_values = {}
        available_dates = sorted(values_by_date.keys())
        
        for date_str in date_strs:
            if date_str in values_by_date:
                result_values[date_str] = values_by_date[date_str]
            else:
                # Find closest date before or on this date
                closest = None
                for avail_date in available_dates:
                    if avail_date <= date_str:
                        closest = avail_date
                    else:
                        break
                if closest:
                    result_values[date_str] = values_by_date[closest]
        
        return result_values
        
    except Exception as e:
        print(f"Error getting historical fund values: {e}")
        return {}


def get_user_investment_metrics(fund: str, total_portfolio_value: float, include_cash: bool = True) -> Optional[Dict[str, Any]]:
    """Get investment metrics for the currently logged-in user using NAV-based calculation.
    
    This calculates the user's investment performance using a unit-based system 
    (similar to mutual fund NAV). Investors who join when the fund is worth more 
    get fewer units per dollar, resulting in accurate per-investor returns.
    
    Args:
        fund: Fund name
        total_portfolio_value: Total portfolio value (positions only, before cash)
        include_cash: Whether to include cash in total fund value (default True)
    
    Returns:
        Dict with keys:
        - net_contribution: User's net contribution amount
        - current_value: Current value of their investment (NAV-based)
        - gain_loss: Absolute gain/loss amount
        - gain_loss_pct: Gain/loss percentage (accurate per-user return)
        - ownership_pct: Ownership percentage (based on units)
        - contributor_name: Their name (for display)
        
        Returns None if:
        - User not logged in
        - No contributor record found matching user's email
        - User has no contributions in the fund
    """
    from auth_utils import get_user_email
    from datetime import datetime
    
    # Get user email
    user_email = get_user_email()
    if not user_email:
        return None
    
    client = get_supabase_client()
    if not client:
        return None
    
    try:
        # Get ALL contributions with timestamps (not just the summary view)
        # WE MUST PAGINATE - Supabase has a hard limit of 1000 rows per request
        all_contributions = []
        batch_size = 1000
        offset = 0
        
        while True:
            query = client.supabase.table("fund_contributions").select(
                "contributor, email, amount, contribution_type, timestamp"
            ).eq("fund", fund)
            
            result = query.range(offset, offset + batch_size - 1).execute()
            
            if not result.data:
                break
            
            all_contributions.extend(result.data)
            
            # If we got fewer rows than batch_size, we're done
            if len(result.data) < batch_size:
                break
            
            offset += batch_size
            
            # Safety break to prevent infinite loops (e.g. max 50k rows = 50 batches)
            if offset > 50000:
                print("Warning: Reached 50,000 row safety limit in get_user_investment_metrics pagination")
                break
        
        if not all_contributions:
            return None
        
        # Get cash balances for total fund value
        cash_balances = get_cash_balances(fund)
        usd_to_cad_rate = 1.0
        try:
            rate_result = client.get_latest_exchange_rate('USD', 'CAD')
            if rate_result:
                usd_to_cad_rate = float(rate_result)
        except Exception:
            usd_to_cad_rate = 1.42
        
        total_cash_cad = cash_balances.get('CAD', 0.0) + (cash_balances.get('USD', 0.0) * usd_to_cad_rate)
        fund_total_value = total_portfolio_value + total_cash_cad if include_cash else total_portfolio_value
        
        if fund_total_value <= 0:
            return None
        
        # Parse and sort contributions chronologically
        contributions = []
        for record in all_contributions:
            timestamp_raw = record.get('timestamp', '')
            timestamp = None
            if timestamp_raw:
                try:
                    if isinstance(timestamp_raw, str):
                        for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                            try:
                                timestamp = datetime.strptime(timestamp_raw.split('+')[0].split('.')[0], fmt)
                                break
                            except ValueError:
                                continue
                except Exception:
                    pass
            
            contributions.append({
                'contributor': record.get('contributor', 'Unknown'),
                'email': record.get('email', ''),
                'amount': float(record.get('amount', 0)),
                'type': record.get('contribution_type', 'CONTRIBUTION').lower(),
                'timestamp': timestamp
            })
        
        contributions.sort(key=lambda x: x['timestamp'] or datetime.min)
        
        # Get all contribution dates for historical fund value lookup
        contrib_dates = [c['timestamp'] for c in contributions if c['timestamp']]
        
        # Fetch ACTUAL historical fund values from portfolio_positions
        historical_values = get_historical_fund_values(fund, contrib_dates)
        
        # Check if we have sufficient historical data
        use_historical = bool(historical_values)
        if not historical_values:
            print(f"⚠️  NAV WARNING: No historical fund values found for {fund}. Using time-weighted estimation.")
        elif len(historical_values) < len(set(d.strftime('%Y-%m-%d') for d in contrib_dates if d)):
            print(f"⚠️  NAV WARNING: Only {len(historical_values)} historical dates found, some contributions will use fallback estimation.")
        
        # Calculate time-weighted estimation parameters for fallback
        # This matches the logic in position_calculator.py
        total_net_contributions = sum(
            -c['amount'] if c['type'] == 'withdrawal' else c['amount'] 
            for c in contributions
        )
        growth_rate = fund_total_value / total_net_contributions if total_net_contributions > 0 else 1.0
        
        timestamps = [c['timestamp'] for c in contributions if c['timestamp']]
        if timestamps:
            first_timestamp = min(timestamps)
            now = datetime.now()
            total_days = max((now - first_timestamp).days, 1)
        else:
            first_timestamp = None
            total_days = 1
        
        # Calculate NAV-based ownership using actual historical data
        contributor_units = {}
        contributor_data = {}
        total_units = 0.0
        running_total_contributions = 0.0  # Total contributions up to this point
        
        for contrib in contributions:
            contributor = contrib['contributor']
            amount = contrib['amount']
            contrib_type = contrib['type']
            timestamp = contrib['timestamp']
            
            if contributor not in contributor_units:
                contributor_units[contributor] = 0.0
                contributor_data[contributor] = {
                    'email': contrib['email'],
                    'contributions': 0.0,
                    'withdrawals': 0.0,
                    'net_contribution': 0.0
                }
            
            if contrib_type == 'withdrawal':
                contributor_data[contributor]['withdrawals'] += amount
                contributor_data[contributor]['net_contribution'] -= amount
                
                # Redeem units at NAV on withdrawal date
                # IMPORTANT: Only redeem if contributor actually has units to prevent total_units corruption
                if total_units > 0 and contributor_units[contributor] > 0:
                    date_str = timestamp.strftime('%Y-%m-%d') if timestamp else None
                    if date_str and date_str in historical_values:
                        fund_value_at_date = historical_values[date_str]
                        nav_at_withdrawal = fund_value_at_date / total_units if total_units > 0 else 1.0
                    elif first_timestamp and timestamp:
                        # Time-weighted fallback (matches position_calculator.py)
                        elapsed_days = (timestamp - first_timestamp).days
                        time_fraction = elapsed_days / total_days
                        nav_at_withdrawal = 1.0 + (growth_rate - 1.0) * time_fraction
                    else:
                        nav_at_withdrawal = (running_total_contributions / total_units) if total_units > 0 else 1.0
                    
                    units_to_redeem = amount / nav_at_withdrawal if nav_at_withdrawal > 0 else amount
                    # Cap redemption at contributor's actual units to prevent going negative
                    actual_units_redeemed = min(units_to_redeem, contributor_units[contributor])
                    contributor_units[contributor] -= actual_units_redeemed
                    total_units -= actual_units_redeemed
                elif contributor_units[contributor] <= 0 and amount > 0:
                    print(f"⚠️  Withdrawal of ${amount} from {contributor} skipped - no units to redeem")
                
                running_total_contributions -= amount
            else:
                contributor_data[contributor]['contributions'] += amount
                contributor_data[contributor]['net_contribution'] += amount
                
                # Calculate NAV at time of contribution using ACTUAL fund value
                date_str = timestamp.strftime('%Y-%m-%d') if timestamp else None
                
                if total_units == 0:
                    # First contribution(s) - NAV = 1.0
                    nav_at_contribution = 1.0
                elif date_str and date_str in historical_values:
                    # We have actual fund value for this date!
                    # But we need the fund value BEFORE this contribution was added
                    # fund_value_at_date includes positions, not cash contributions
                    fund_value_at_date = historical_values[date_str]
                    nav_at_contribution = fund_value_at_date / total_units if total_units > 0 else 1.0
                elif first_timestamp and timestamp:
                    # Time-weighted fallback (matches position_calculator.py)
                    elapsed_days = (timestamp - first_timestamp).days
                    time_fraction = elapsed_days / total_days
                    nav_at_contribution = 1.0 + (growth_rate - 1.0) * time_fraction
                    print(f"⚠️  NAV FALLBACK: No historical data for {date_str} ({contributor}). Using time-weighted estimation.")
                else:
                    print(f"⚠️  NAV FALLBACK: No timestamp for {contributor}. Using simple estimation.")
                    nav_at_contribution = running_total_contributions / total_units if total_units > 0 else 1.0
                
                # Ensure NAV is at least the base value (1.0 for first contributions)
                if nav_at_contribution <= 0:
                    nav_at_contribution = 1.0
                
                units_purchased = amount / nav_at_contribution
                contributor_units[contributor] += units_purchased
                total_units += units_purchased
                running_total_contributions += amount
        
        if total_units <= 0:
            return None
        
        # Find the current user's data
        user_email_lower = user_email.lower()
        user_contributor = None
        user_units = 0.0
        
        for contributor, data in contributor_data.items():
            contrib_email = data.get('email', '')
            if contrib_email and contrib_email.lower() == user_email_lower:
                user_contributor = contributor
                user_units = contributor_units.get(contributor, 0.0)
                break
        
        if user_contributor is None or user_units <= 0:
            return None
        
        user_data = contributor_data[user_contributor]
        user_net_contribution = user_data['net_contribution']
        
        if user_net_contribution <= 0:
            return None
        
        # Calculate current NAV and user's value
        current_nav = fund_total_value / total_units
        current_value = user_units * current_nav
        ownership_pct = (user_units / total_units) * 100
        gain_loss = current_value - user_net_contribution
        gain_loss_pct = (gain_loss / user_net_contribution) * 100 if user_net_contribution > 0 else 0.0
        
        return {
            'net_contribution': user_net_contribution,
            'current_value': current_value,
            'gain_loss': gain_loss,
            'gain_loss_pct': gain_loss_pct,
            'ownership_pct': ownership_pct,
            'contributor_name': user_contributor,
            # Additional NAV transparency fields
            'units': user_units,
            'unit_price': current_nav
        }
        
    except Exception as e:
        print(f"Error getting user investment metrics: {e}")
        return None
