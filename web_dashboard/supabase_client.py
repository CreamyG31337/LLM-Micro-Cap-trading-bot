#!/usr/bin/env python3
"""
Supabase client for portfolio dashboard
Handles all database operations
"""

import os
import json

# Check critical dependencies first
try:
    import pandas as pd
except ImportError:
    print("❌ ERROR: pandas not available")
    print("🔔 SOLUTION: Activate the virtual environment first!")
    print("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
    print("   You should see (venv) in your prompt when activated.")
    raise ImportError("pandas not available. Activate virtual environment.")

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from decimal import Decimal
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from supabase import create_client, Client
except ImportError:
    print("❌ ERROR: Supabase client not available")
    print("🔔 SOLUTION: Activate the virtual environment first!")
    print("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
    print("   You should see (venv) in your prompt when activated.")
    raise ImportError("Supabase client not available. Activate virtual environment.")

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Client for interacting with Supabase database"""
    
    def __init__(self, user_token: Optional[str] = None, use_service_role: bool = False):
        """Initialize Supabase client
        
        Args:
            user_token: Optional JWT token from authenticated user (respects RLS)
            use_service_role: If True, use service role key (bypasses RLS, admin only)
        """
        self.url = os.getenv("SUPABASE_URL")
        
        if use_service_role:
            # Use service role key for admin operations (bypasses RLS)
            self.key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if not self.key:
                raise ValueError("SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY must be set for admin operations")
        else:
            # Always use publishable key to initialize client (required by Supabase Python library)
            self.key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
            if not self.key:
                raise ValueError("SUPABASE_PUBLISHABLE_KEY or SUPABASE_ANON_KEY must be set")
        
        # Debug logging for environment variables
        logger.debug(f"SUPABASE_URL exists: {bool(self.url)}")
        logger.debug(f"Using key type: {'service_role' if use_service_role else 'publishable'}")
        logger.debug(f"User token provided: {bool(user_token)}")
        
        if not self.url or not self.key:
            logger.error(f"Missing environment variables - URL: {bool(self.url)}, KEY: {bool(self.key)}")
            raise ValueError("SUPABASE_URL and appropriate key must be set")
        
        # Create client with publishable/service role key
        self.supabase: Client = create_client(self.url, self.key)
        
        # If user token provided, set it as the auth session
        if user_token and not use_service_role:
            # Store token for use in queries
            self._user_token = user_token
            
            try:
                # Try to set the access token in the auth session
                # Supabase client needs both access_token and refresh_token for set_session
                # If we only have access_token, we'll manually set headers instead
                self.supabase.auth.set_session(
                    access_token=user_token,
                    refresh_token=""  # Empty refresh token - may cause set_session to fail
                )
                logger.debug("User token set in Supabase auth session")
            except Exception as e:
                logger.debug(f"set_session failed (expected if no refresh token): {e}")
                # We'll use the stored token to set headers manually in queries
            
            # Manually set Authorization header on postgrest client
            # This is the key fix - we need to set the Authorization header on the underlying postgrest client
            try:
                # The Supabase client uses postgrest for database queries
                # We need to set the Authorization header on the postgrest client's session
                if hasattr(self.supabase, 'postgrest'):
                    # Set the auth token on the postgrest client
                    # The postgrest client uses this for Authorization header
                    self.supabase.postgrest.auth = user_token
                    logger.debug("User token set on postgrest client")
                else:
                    # Fallback: try to access via table client
                    # Create a dummy table query to access the underlying client
                    dummy_table = self.supabase.table("_dummy_table_for_auth")
                    if hasattr(dummy_table, '_client'):
                        # Set auth on the underlying postgrest client
                        dummy_table._client.auth = user_token
                        logger.debug("User token set on table client's postgrest client")
            except Exception as header_error:
                logger.warning(f"Could not set Authorization header: {header_error}")
                # Token is stored in self._user_token as fallback
    
    def test_connection(self) -> bool:
        """Test database connection"""
        try:
            result = self.supabase.table("cash_balances").select("*").limit(1).execute()
            logger.info("✅ Supabase connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ Supabase connection failed: {e}")
            return False
    
    def upsert_portfolio_positions(self, positions_df: pd.DataFrame) -> bool:
        """Insert or update portfolio positions"""
        try:
            if positions_df.empty:
                return True
            
            # Convert DataFrame to list of dictionaries
            positions = []
            for _, row in positions_df.iterrows():
                positions.append({
                    "ticker": row["Ticker"],
                    "shares": float(row["Shares"]),
                    "price": float(row["Current Price"]),  # Fixed column name
                    "cost_basis": float(row["Cost Basis"]),
                    "pnl": float(row["PnL"]),
                    "date": row["Date"].isoformat() if pd.notna(row["Date"]) else datetime.now(timezone.utc).isoformat()
                })
            
            # Upsert positions (insert or update on conflict)
            result = self.supabase.table("portfolio_positions").upsert(positions).execute()
            logger.info(f"✅ Upserted {len(positions)} portfolio positions")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting portfolio positions: {e}")
            return False
    
    def upsert_trade_log(self, trades_df: pd.DataFrame) -> bool:
        """Insert or update trade log"""
        try:
            if trades_df.empty:
                return True
            
            # Convert DataFrame to list of dictionaries
            trades = []
            for _, row in trades_df.iterrows():
                trades.append({
                    "date": row["Date"].isoformat() if pd.notna(row["Date"]) else datetime.now(timezone.utc).isoformat(),
                    "ticker": row["Ticker"],
                    "shares": float(row["Shares"]),
                    "price": float(row["Price"]),
                    "cost_basis": float(row["Cost Basis"]),
                    "pnl": float(row["PnL"]),
                    "reason": str(row["Reason"])
                })
            
            # Insert trades (no upsert needed for trade log)
            result = self.supabase.table("trade_log").insert(trades).execute()
            logger.info(f"✅ Inserted {len(trades)} trade log entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error inserting trade log: {e}")
            return False
    
    def upsert_cash_balances(self, cash_balances: Dict[str, float]) -> bool:
        """Update cash balances"""
        try:
            for currency, amount in cash_balances.items():
                result = self.supabase.table("cash_balances").update({
                    "amount": float(amount),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("currency", currency).execute()
            
            logger.info(f"✅ Updated cash balances: {cash_balances}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating cash balances: {e}")
            return False
    
    def get_current_positions(self, fund: Optional[str] = None) -> List[Dict]:
        """Get current portfolio positions, optionally filtered by fund"""
        try:
            query = self.supabase.table("current_positions").select("*")
            if fund:
                query = query.eq("fund", fund)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ Error getting current positions: {e}")
            return []
    
    def get_trade_log(self, limit: int = 100, fund: Optional[str] = None) -> List[Dict]:
        """Get recent trade log entries, optionally filtered by fund"""
        try:
            query = self.supabase.table("trade_log").select("*").order("date", desc=True).limit(limit)
            if fund:
                query = query.eq("fund", fund)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ Error getting trade log: {e}")
            return []
    
    def get_cash_balances(self, fund: Optional[str] = None) -> Dict[str, float]:
        """Get current cash balances, optionally filtered by fund"""
        try:
            query = self.supabase.table("cash_balances").select("*")
            if fund:
                query = query.eq("fund", fund)
            result = query.execute()
            balances = {}
            for row in result.data:
                key = f"{row['fund']}_{row['currency']}" if not fund else row["currency"]
                balances[key] = float(row["amount"])
            return balances
        except Exception as e:
            logger.error(f"❌ Error getting cash balances: {e}")
            return {"CAD": 0.0, "USD": 0.0}
    
    def get_available_funds(self) -> List[str]:
        """Get list of all available funds"""
        try:
            result = self.supabase.table("portfolio_positions").select("fund").execute()
            funds = list(set(row["fund"] for row in result.data))
            return sorted(funds)
        except Exception as e:
            logger.error(f"❌ Error getting available funds: {e}")
            return []
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Calculate and return performance metrics"""
        try:
            # Get current positions
            positions = self.get_current_positions()
            
            # Calculate metrics
            total_value = sum(pos["total_market_value"] for pos in positions)
            total_cost_basis = sum(pos["total_cost_basis"] for pos in positions)
            unrealized_pnl = sum(pos["total_pnl"] for pos in positions)
            performance_pct = (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
            
            # Get trade statistics
            trades = self.get_trade_log(limit=1000)
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t["pnl"] > 0])
            losing_trades = len([t for t in trades if t["pnl"] < 0])
            
            return {
                "total_value": round(total_value, 2),
                "total_cost_basis": round(total_cost_basis, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "performance_pct": round(performance_pct, 2),
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades
            }
            
        except Exception as e:
            logger.error(f"❌ Error calculating performance metrics: {e}")
            return {
                "total_value": 0,
                "total_cost_basis": 0,
                "unrealized_pnl": 0,
                "performance_pct": 0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0
            }
    
    def get_daily_performance_data(self, days: int = 30, fund: Optional[str] = None) -> List[Dict]:
        """Get daily performance data for charting, optionally filtered by fund"""
        try:
            # Get performance metrics data
            query = self.supabase.table("performance_metrics").select(
                "date, total_value, cost_basis, unrealized_pnl, performance_pct, fund"
            ).gte("date", (datetime.now() - pd.Timedelta(days=days)).isoformat()).order("date")
            
            if fund:
                query = query.eq("fund", fund)
            
            result = query.execute()
            
            if not result.data:
                return []
            
            # Process performance metrics data - return as DataFrame-like structure
            df = pd.DataFrame(result.data)
            df["date"] = pd.to_datetime(df["date"])
            df["performance_index"] = df["performance_pct"] + 100
            
            # Return as list of dictionaries with the exact format the chart expects
            daily_data = []
            for _, row in df.iterrows():
                daily_data.append({
                    "date": row["date"].strftime('%Y-%m-%d'),  # Convert to string for JSON serialization
                    "performance_index": round(float(row["performance_index"]), 2),
                    "total_value": round(float(row["total_value"]), 2),
                    "cost_basis": round(float(row["cost_basis"]), 2),
                    "unrealized_pnl": round(float(row["unrealized_pnl"]), 2),
                    "performance_pct": round(float(row["performance_pct"]), 2)
                })
            
            return sorted(daily_data, key=lambda x: x["date"])
            
        except Exception as e:
            logger.error(f"❌ Error getting daily performance data: {e}")
            return []
