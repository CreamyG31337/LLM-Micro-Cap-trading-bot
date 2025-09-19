#!/usr/bin/env python3
"""
Supabase client for portfolio dashboard
Handles all database operations
"""

import os
import json
import pandas as pd
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
    print("Installing supabase client...")
    import subprocess
    subprocess.check_call(["pip", "install", "supabase"])
    from supabase import create_client, Client

logger = logging.getLogger(__name__)

class SupabaseClient:
    """Client for interacting with Supabase database"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        
        # Debug logging for environment variables
        logger.info(f"SUPABASE_URL exists: {bool(self.url)}")
        logger.info(f"SUPABASE_ANON_KEY exists: {bool(self.key)}")
        
        if not self.url or not self.key:
            logger.error(f"Missing environment variables - URL: {bool(self.url)}, KEY: {bool(self.key)}")
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY environment variables must be set")
        
        self.supabase: Client = create_client(self.url, self.key)
    
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
    
    def get_daily_performance_data(self, days: int = 30) -> List[Dict]:
        """Get daily performance data for charting"""
        try:
            # Get positions grouped by date
            result = self.supabase.table("portfolio_positions").select(
                "date, ticker, shares, price, cost_basis, pnl, total_value"
            ).gte("date", (datetime.now() - pd.Timedelta(days=days)).isoformat()).execute()
            
            if not result.data:
                return []
            
            # Group by date and calculate daily totals
            df = pd.DataFrame(result.data)
            df["date"] = pd.to_datetime(df["date"]).dt.date
            
            daily_data = []
            for date, group in df.groupby("date"):
                current_positions = group[group["shares"] > 0]
                if not current_positions.empty:
                    total_value = current_positions["total_value"].sum()
                    total_cost_basis = current_positions["cost_basis"].sum()
                    unrealized_pnl = current_positions["pnl"].sum()
                    performance_pct = (unrealized_pnl / total_cost_basis * 100) if total_cost_basis > 0 else 0
                    
                    daily_data.append({
                        "date": date.isoformat(),
                        "total_value": round(total_value, 2),
                        "cost_basis": round(total_cost_basis, 2),
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "performance_pct": round(performance_pct, 2),
                        "performance_index": round(performance_pct + 100, 2)
                    })
            
            return sorted(daily_data, key=lambda x: x["date"])
            
        except Exception as e:
            logger.error(f"❌ Error getting daily performance data: {e}")
            return []
