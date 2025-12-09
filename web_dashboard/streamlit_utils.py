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
    if SupabaseClient is None:
        return None
    
    try:
        # Get user token from session if not provided
        if user_token is None and get_user_token:
            user_token = get_user_token()
        
        # Use user token if available (respects RLS)
        return SupabaseClient(user_token=user_token)
    except Exception as e:
        print(f"Error initializing Supabase client: {e}")
        return None


def get_available_funds() -> List[str]:
    """Get list of available funds from Supabase"""
    client = get_supabase_client()
    if not client:
        return []
    
    try:
        # Get unique fund names from portfolio_positions
        result = client.supabase.table("portfolio_positions").select("fund").execute()
        funds = list(set(row['fund'] for row in result.data if row.get('fund')))
        return sorted(funds)
    except Exception as e:
        print(f"Error getting funds: {e}")
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


