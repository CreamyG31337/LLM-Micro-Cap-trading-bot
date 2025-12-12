#!/usr/bin/env python3
"""
Streamlit utilities for fetching data from Supabase
"""

import os
from typing import Dict, List, Optional, Any, Tuple, Union
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


def get_available_funds(return_debug_info: bool = False) -> Union[List[str], Tuple[List[str], Dict[str, Any]]]:
    """Get list of available funds from Supabase
    
    First queries user_funds table to get funds assigned to the authenticated user.
    Falls back to querying portfolio_positions, trade_log, and cash_balances tables if needed.
    Returns a sorted list of unique fund names.
    
    Args:
        return_debug_info: If True, returns tuple of (funds_list, debug_dict) instead of just funds_list
    
    Returns:
        List of fund names, or tuple of (funds_list, debug_dict) if return_debug_info=True
    """
    import logging
    logger = logging.getLogger(__name__)
    debug_info = {
        "client_initialized": False,
        "client_url": None,
        "user_id": None,
        "user_funds": {"queried": False, "row_count": 0, "funds_found": [], "error": None},
        "portfolio_positions": {"queried": False, "row_count": 0, "funds_found": [], "error": None},
        "trade_log": {"queried": False, "row_count": 0, "funds_found": [], "error": None},
        "cash_balances": {"queried": False, "row_count": 0, "funds_found": [], "error": None},
        "total_funds": 0
    }
    
    # Step 1: Initialize Supabase client
    logger.debug("Initializing Supabase client...")
    client = get_supabase_client()
    
    if not client:
        logger.error("Failed to initialize Supabase client - client is None")
        debug_info["error"] = "Supabase client initialization failed - client is None"
        if return_debug_info:
            return [], debug_info
        return []
    
    if not hasattr(client, 'supabase') or client.supabase is None:
        logger.error("Supabase client exists but supabase attribute is None")
        debug_info["error"] = "Supabase client.supabase is None"
        if return_debug_info:
            return [], debug_info
        return []
    
    debug_info["client_initialized"] = True
    debug_info["client_url"] = getattr(client, 'url', 'unknown')
    logger.debug(f"Supabase client initialized successfully. URL: {debug_info['client_url']}")
    
    # Get user ID for querying user_funds table
    try:
        from auth_utils import get_user_id
        user_id = get_user_id()
        debug_info["user_id"] = user_id
        if user_id:
            logger.debug(f"Authenticated user ID: {user_id}")
        else:
            logger.warning("No user ID found in session - user may not be authenticated")
    except Exception as e:
        logger.warning(f"Could not get user ID: {e}")
        debug_info["user_id"] = None
    
    all_funds = set()
    
    # Step 2: Query user_funds table first (primary source)
    if user_id:
        try:
            logger.debug(f"Querying user_funds table for user_id: {user_id}...")
            debug_info["user_funds"]["queried"] = True
            result = client.supabase.table("user_funds").select("fund_name").eq("user_id", user_id).execute()
            
            if result is None:
                logger.warning("Query to user_funds returned None")
                debug_info["user_funds"]["error"] = "Query returned None"
            elif not hasattr(result, 'data'):
                logger.warning("Query result has no 'data' attribute")
                debug_info["user_funds"]["error"] = "Result has no 'data' attribute"
            elif result.data is None:
                logger.warning("Query result.data is None")
                debug_info["user_funds"]["error"] = "Result.data is None"
            elif len(result.data) == 0:
                logger.warning(f"Query returned 0 rows for user_id: {user_id}")
                debug_info["user_funds"]["error"] = f"Query returned 0 rows for user_id: {user_id}"
            else:
                debug_info["user_funds"]["row_count"] = len(result.data)
                funds_from_user_funds = [row.get('fund_name') for row in result.data if row.get('fund_name')]
                all_funds.update(funds_from_user_funds)
                debug_info["user_funds"]["funds_found"] = funds_from_user_funds
                logger.debug(f"Found {len(funds_from_user_funds)} funds in user_funds: {funds_from_user_funds}")
        except Exception as e:
            logger.error(f"Error querying user_funds: {e}", exc_info=True)
            debug_info["user_funds"]["error"] = str(e)
    else:
        logger.warning("No user_id available - skipping user_funds query")
        debug_info["user_funds"]["error"] = "No user_id available in session"
    
    # Step 3: Fallback to portfolio_positions table
    try:
        logger.debug("Querying portfolio_positions table for funds...")
        debug_info["portfolio_positions"]["queried"] = True
        result = client.supabase.table("portfolio_positions").select("fund").execute()
        
        if result is None:
            logger.warning("Query to portfolio_positions returned None")
            debug_info["portfolio_positions"]["error"] = "Query returned None"
        elif not hasattr(result, 'data'):
            logger.warning("Query result has no 'data' attribute")
            debug_info["portfolio_positions"]["error"] = "Result has no 'data' attribute"
        elif result.data is None:
            logger.warning("Query result.data is None")
            debug_info["portfolio_positions"]["error"] = "Result.data is None"
        elif len(result.data) == 0:
            logger.warning("Query returned empty result.data")
            debug_info["portfolio_positions"]["error"] = "Query returned 0 rows"
        else:
            debug_info["portfolio_positions"]["row_count"] = len(result.data)
            funds_from_positions = [row.get('fund') for row in result.data if row.get('fund')]
            all_funds.update(funds_from_positions)
            debug_info["portfolio_positions"]["funds_found"] = funds_from_positions
            logger.debug(f"Found {len(funds_from_positions)} unique funds in portfolio_positions: {funds_from_positions}")
    except Exception as e:
        logger.error(f"Error querying portfolio_positions: {e}", exc_info=True)
        debug_info["portfolio_positions"]["error"] = str(e)
    
    # Step 4: Fallback to trade_log table
    try:
        logger.debug("Querying trade_log table for funds...")
        debug_info["trade_log"]["queried"] = True
        result = client.supabase.table("trade_log").select("fund").execute()
        
        if result is None:
            debug_info["trade_log"]["error"] = "Query returned None"
        elif not hasattr(result, 'data'):
            debug_info["trade_log"]["error"] = "Result has no 'data' attribute"
        elif result.data is None:
            debug_info["trade_log"]["error"] = "Result.data is None"
        elif len(result.data) == 0:
            debug_info["trade_log"]["error"] = "Query returned 0 rows"
        else:
            debug_info["trade_log"]["row_count"] = len(result.data)
            funds_from_trades = [row.get('fund') for row in result.data if row.get('fund')]
            all_funds.update(funds_from_trades)
            debug_info["trade_log"]["funds_found"] = funds_from_trades
            logger.debug(f"Found {len(funds_from_trades)} unique funds in trade_log: {funds_from_trades}")
    except Exception as e:
        logger.error(f"Error querying trade_log: {e}", exc_info=True)
        debug_info["trade_log"]["error"] = str(e)
    
    # Step 5: Fallback to cash_balances table
    try:
        logger.debug("Querying cash_balances table for funds...")
        debug_info["cash_balances"]["queried"] = True
        result = client.supabase.table("cash_balances").select("fund").execute()
        
        if result is None:
            debug_info["cash_balances"]["error"] = "Query returned None"
        elif not hasattr(result, 'data'):
            debug_info["cash_balances"]["error"] = "Result has no 'data' attribute"
        elif result.data is None:
            debug_info["cash_balances"]["error"] = "Result.data is None"
        elif len(result.data) == 0:
            debug_info["cash_balances"]["error"] = "Query returned 0 rows"
        else:
            debug_info["cash_balances"]["row_count"] = len(result.data)
            funds_from_cash = [row.get('fund') for row in result.data if row.get('fund')]
            all_funds.update(funds_from_cash)
            debug_info["cash_balances"]["funds_found"] = funds_from_cash
            logger.debug(f"Found {len(funds_from_cash)} unique funds in cash_balances: {funds_from_cash}")
    except Exception as e:
        logger.error(f"Error querying cash_balances: {e}", exc_info=True)
        debug_info["cash_balances"]["error"] = str(e)
    
    # Step 6: Return sorted list
    if all_funds:
        sorted_funds = sorted(list(all_funds))
        debug_info["total_funds"] = len(sorted_funds)
        logger.info(f"Successfully retrieved {len(sorted_funds)} funds: {sorted_funds}")
        if return_debug_info:
            return sorted_funds, debug_info
        return sorted_funds
    else:
        debug_info["total_funds"] = 0
        logger.warning("No funds found in any table (portfolio_positions, trade_log, cash_balances)")
        if return_debug_info:
            return [], debug_info
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


def calculate_portfolio_value_over_time(fund: Optional[str] = None) -> pd.DataFrame:
    """Calculate portfolio value over time from trade log"""
    trades_df = get_trade_log(limit=10000, fund=fund)
    
    if trades_df.empty:
        return pd.DataFrame()
    
    # Sort by date
    trades_df = trades_df.sort_values('date')
    
    # Calculate cumulative portfolio value
    # This is a simplified calculation - you may want to enhance this
    portfolio_values = []
    current_value = 0.0
    
    for _, trade in trades_df.iterrows():
        trade_type = str(trade.get('type', '')).upper()
        shares = float(trade.get('shares', 0))
        price = float(trade.get('price', 0))
        cost_basis = float(trade.get('cost_basis', shares * price))
        
        if trade_type == 'BUY':
            current_value += cost_basis
        elif trade_type == 'SELL':
            current_value -= cost_basis
        
        portfolio_values.append({
            'date': trade['date'],
            'value': current_value
        })
    
    if not portfolio_values:
        return pd.DataFrame()
    
    result_df = pd.DataFrame(portfolio_values)
    # Ensure date column is datetime
    if 'date' in result_df.columns:
        result_df['date'] = pd.to_datetime(result_df['date'])
    
    return result_df


