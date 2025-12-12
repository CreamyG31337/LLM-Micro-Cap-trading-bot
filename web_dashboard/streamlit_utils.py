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


