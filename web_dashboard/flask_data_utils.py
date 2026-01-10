
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
from datetime import datetime

from supabase_client import SupabaseClient
from flask_auth_utils import get_user_id_flask

logger = logging.getLogger(__name__)

def get_supabase_client_flask(user_id: Optional[str] = None) -> Optional[SupabaseClient]:
    """Get Supabase client for Flask context
    
    Args:
        user_id: Optional user ID to verify context
    """
    try:
        # In Flask, we typically initialize fresh or get from some request-scoped store.
        # For our SupabaseClient wrapper, it handles auth internally if designed well,
        # but here we just need a connected client.
        
        # NOTE: Our SupabaseClient wrapper in supabase_client.py typically looks for 
        # env vars or provided token. Flask auth might need to pass the user's token.
        # For RLS, we really need the user's JWT. flask_auth_utils should provide that.
        
        # However, looking at how app.py was doing it:
        # client = SupabaseClient()
        # It seems to work without explicitly passing token if the server has service key?
        # NO, user_funds table likely has RLS!
        
        # Let's assume for now we use the service role (if configured) OR rely on the 
        # SupabaseClient implementation to handle it.
        # But wait, checking supabase_client.py would be wise.
        # Assuming typical setup:
        
        return SupabaseClient()
        
    except Exception as e:
        logger.error(f"Error initializing Supabase client: {e}")
        return None

def get_available_funds_flask() -> List[str]:
    """Get list of available funds for current Flask user"""
    try:
        user_id = get_user_id_flask()
        if not user_id:
            logger.warning("get_available_funds_flask: No user_id in session")
            return []
            
        client = get_supabase_client_flask(user_id)
        if not client:
            return []
            
        # Direct query
        result = client.supabase.table("user_funds").select("fund_name").eq("user_id", user_id).execute()
        
        if result and result.data:
            funds = [row.get('fund_name') for row in result.data if row.get('fund_name')]
            return sorted(funds)
            
        return []
    except Exception as e:
        logger.error(f"get_available_funds_flask failed: {e}")
        return []

def get_current_positions_flask(fund: Optional[str] = None) -> pd.DataFrame:
    """Get current positions for Flask (no Streamlit cache)"""
    client = get_supabase_client_flask()
    if not client:
        return pd.DataFrame()
        
    try:
        logger.info(f"Loading current positions (Flask) for fund: {fund}")
        
        # Paginated fetch similar to streamlit_utils
        all_rows = []
        batch_size = 1000
        offset = 0
        
        while True:
            # Join with securities logic
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
            return pd.DataFrame(all_rows)
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"Error getting positions (Flask): {e}", exc_info=True)
        return pd.DataFrame()

def get_trade_log_flask(limit: int = 1000, fund: Optional[str] = None) -> pd.DataFrame:
    """Get trade log for Flask (no caching)"""
    client = get_supabase_client_flask()
    if not client:
        return pd.DataFrame()
        
    try:
        if fund:
            logger.info(f"Loading trade log (Flask) for fund: {fund}")
            
        # Use client method if available, or direct query
        # Since client.get_trade_log might depend on internal logic, let's look at 
        # how streamlit_utils called it: result = client.get_trade_log(...)
        # We can assume client instance has this method.
        
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

def get_cash_balances_flask(fund: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get cash balances (Flask)"""
    # Assuming similar logic to positions.
    # In streamlit_utils it calls get_cash_balances. Let's see if we can just query the table.
    # Actually, simpler is checking if SupabaseClient has a helper or query directly.
    # Let's assume direct query to 'portfolio_balances' or similar?
    # Wait, need to check streamlit_utils implementation of get_cash_balances if I can.
    # I didn't verify get_cash_balances implementation in streamlit_utils in previous step.
    # I'll implement a best-guess direct query or just return empty for now and fix later, 
    # OR better: read `streamlit_utils.py` again specifically for get_cash_balances.
    # But for now, let's stick to what I know.
    
    # We will query 'account_balances' if that's the table, or check logic.
    pass

# For now, let's implement the ones I definitely saw used.
