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
    
    Queries multiple tables (portfolio_positions, trade_log, cash_balances) to find
    all available funds. Returns a sorted list of unique fund names.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Step 1: Initialize Supabase client
    logger.debug("Initializing Supabase client...")
    client = get_supabase_client()
    
    if not client:
        logger.error("Failed to initialize Supabase client - client is None")
        print("ERROR: Supabase client initialization failed. Check environment variables and imports.")
        return []
    
    if not hasattr(client, 'supabase') or client.supabase is None:
        logger.error("Supabase client exists but supabase attribute is None")
        print("ERROR: Supabase client.supabase is None")
        return []
    
    logger.debug(f"Supabase client initialized successfully. URL: {getattr(client, 'url', 'unknown')}")
    
    all_funds = set()
    
    # Step 2: Try portfolio_positions table first
    try:
        logger.debug("Querying portfolio_positions table for funds...")
        result = client.supabase.table("portfolio_positions").select("fund").execute()
        
        if result is None:
            logger.warning("Query to portfolio_positions returned None")
        elif not hasattr(result, 'data'):
            logger.warning("Query result has no 'data' attribute")
        elif result.data is None:
            logger.warning("Query result.data is None")
        else:
            funds_from_positions = [row.get('fund') for row in result.data if row.get('fund')]
            all_funds.update(funds_from_positions)
            logger.debug(f"Found {len(funds_from_positions)} unique funds in portfolio_positions: {funds_from_positions}")
    except Exception as e:
        logger.error(f"Error querying portfolio_positions: {e}", exc_info=True)
        print(f"WARNING: Error querying portfolio_positions table: {e}")
    
    # Step 3: Fallback to trade_log table
    try:
        logger.debug("Querying trade_log table for funds...")
        result = client.supabase.table("trade_log").select("fund").execute()
        
        if result and hasattr(result, 'data') and result.data:
            funds_from_trades = [row.get('fund') for row in result.data if row.get('fund')]
            all_funds.update(funds_from_trades)
            logger.debug(f"Found {len(funds_from_trades)} unique funds in trade_log: {funds_from_trades}")
    except Exception as e:
        logger.error(f"Error querying trade_log: {e}", exc_info=True)
        print(f"WARNING: Error querying trade_log table: {e}")
    
    # Step 4: Fallback to cash_balances table
    try:
        logger.debug("Querying cash_balances table for funds...")
        result = client.supabase.table("cash_balances").select("fund").execute()
        
        if result and hasattr(result, 'data') and result.data:
            funds_from_cash = [row.get('fund') for row in result.data if row.get('fund')]
            all_funds.update(funds_from_cash)
            logger.debug(f"Found {len(funds_from_cash)} unique funds in cash_balances: {funds_from_cash}")
    except Exception as e:
        logger.error(f"Error querying cash_balances: {e}", exc_info=True)
        print(f"WARNING: Error querying cash_balances table: {e}")
    
    # Step 5: Return sorted list
    if all_funds:
        sorted_funds = sorted(list(all_funds))
        logger.info(f"Successfully retrieved {len(sorted_funds)} funds: {sorted_funds}")
        return sorted_funds
    else:
        logger.warning("No funds found in any table (portfolio_positions, trade_log, cash_balances)")
        print("WARNING: No funds found in database. Check that data exists in portfolio_positions, trade_log, or cash_balances tables.")
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


