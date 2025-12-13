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
                # We need to call the auth() method (not assign to auth property) to set the Authorization header
                if hasattr(self.supabase, 'postgrest'):
                    # Call the auth() method with the token to set Authorization header
                    # The postgrest client uses this for Authorization header in all queries
                    self.supabase.postgrest.auth(user_token)
                    logger.debug("User token set on postgrest client via auth() method")
                else:
                    # Fallback: try to access via table client
                    # Create a dummy table query to access the underlying client
                    dummy_table = self.supabase.table("_dummy_table_for_auth")
                    if hasattr(dummy_table, '_client'):
                        # Call auth() method on the underlying postgrest client
                        dummy_table._client.auth(user_token)
                        logger.debug("User token set on table client's postgrest client via auth() method")
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
    
    def ensure_ticker_in_securities(self, ticker: str, currency: str, company_name: Optional[str] = None) -> bool:
        """Ensure ticker exists in securities table with metadata from yfinance.
        
        This method is called on first trade to populate the securities table.
        It checks if the ticker exists and has company metadata. If not, it fetches
        from yfinance and inserts/updates the record.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'SHOP.TO')
            currency: Currency code ('CAD' or 'USD')
            company_name: Optional company name if already known (avoids yfinance call)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if ticker already exists with complete metadata
            existing = self.supabase.table("securities").select("ticker, company_name").eq("ticker", ticker).execute()
            
            # If ticker exists with valid company name (not NULL, empty, or 'Unknown'), no need to update
            company_name = existing.data[0].get('company_name')
            if existing.data and company_name and company_name != 'Unknown':
                logger.debug(f"Ticker {ticker} already exists in securities table with company name")
                return True
            
            # Need to fetch metadata from yfinance
            metadata = {
                'ticker': ticker,
                'currency': currency
            }
            
            # If company_name was provided, use it; otherwise fetch from yfinance
            if company_name and company_name.strip():
                metadata['company_name'] = company_name.strip()
            else:
                # Fetch from yfinance
                try:
                    import yfinance as yf
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    if info:
                        # Get company name (prefer longName over shortName)
                        metadata['company_name'] = info.get('longName') or info.get('shortName', 'Unknown')
                        
                        # Get additional metadata
                        metadata['sector'] = info.get('sector')
                        metadata['industry'] = info.get('industry')
                        metadata['country'] = info.get('country')
                        
                        # Get market cap (store as text since it can be very large)
                        market_cap = info.get('marketCap')
                        if market_cap:
                            metadata['market_cap'] = str(market_cap)
                        
                        logger.debug(f"Fetched metadata for {ticker}: {metadata.get('company_name')}")
                    else:
                        logger.warning(f"No yfinance info available for {ticker}")
                        metadata['company_name'] = 'Unknown'
                        
                except Exception as yf_error:
                    logger.warning(f"Failed to fetch yfinance data for {ticker}: {yf_error}")
                    metadata['company_name'] = 'Unknown'
            
            # Set last_updated timestamp
            metadata['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            # Upsert into securities table
            result = self.supabase.table("securities").upsert(metadata, on_conflict="ticker").execute()
            
            logger.info(f"✅ Ensured {ticker} in securities table: {metadata.get('company_name')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error ensuring ticker {ticker} in securities table: {e}")
            return False
    
    def upsert_portfolio_positions(self, positions_df: pd.DataFrame) -> bool:
        """Insert or update portfolio positions"""
        try:
            if positions_df.empty:
                return True
            
            # Extract unique tickers and ensure they exist in securities table
            unique_tickers = positions_df['Ticker'].unique()
            for ticker in unique_tickers:
                # Get currency for this ticker (use first occurrence)
                ticker_rows = positions_df[positions_df['Ticker'] == ticker]
                currency = ticker_rows.iloc[0].get('Currency', 'USD') if 'Currency' in ticker_rows.columns else 'USD'
                
                # Get company name if available (avoid yfinance call if we already have it)
                company_name = ticker_rows.iloc[0].get('Company') if 'Company' in ticker_rows.columns else None
                
                # Ensure ticker is in securities table
                self.ensure_ticker_in_securities(ticker, currency, company_name)
            
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
            
            # Extract unique tickers and ensure they exist in securities table
            unique_tickers = trades_df['Ticker'].unique()
            for ticker in unique_tickers:
                # Get currency for this ticker (use first occurrence)
                ticker_rows = trades_df[trades_df['Ticker'] == ticker]
                currency = ticker_rows.iloc[0].get('Currency', 'USD') if 'Currency' in ticker_rows.columns else 'USD'
                
                # Ensure ticker is in securities table (no company name in trade log)
                self.ensure_ticker_in_securities(ticker, currency, None)
            
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
        """Get recent trade log entries with company names, optionally filtered by fund"""
        try:
            # Select trade_log columns and join with securities for company_name
            query = self.supabase.table("trade_log").select(
                "*, securities(company_name)"
            ).order("date", desc=True).limit(limit)
            
            if fund:
                query = query.eq("fund", fund)
            
            result = query.execute()
            
            # Flatten the nested securities object for easier consumption
            trades = []
            for row in result.data:
                trade = row.copy()
                # Extract company_name from nested securities object
                if 'securities' in trade and trade['securities']:
                    trade['company_name'] = trade['securities'].get('company_name')
                    del trade['securities']  # Remove the nested object
                else:
                    trade['company_name'] = None
                trades.append(trade)
            
            return trades
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
    
    # =====================================================
    # EXCHANGE RATES METHODS
    # =====================================================
    
    def get_exchange_rate(self, date: datetime, from_currency: str = 'USD', to_currency: str = 'CAD') -> Optional[Decimal]:
        """Get exchange rate for a specific date.
        
        Returns the most recent rate on or before the target date.
        
        Args:
            date: Target date for the exchange rate
            from_currency: Source currency (default: 'USD')
            to_currency: Target currency (default: 'CAD')
            
        Returns:
            Exchange rate as Decimal, or None if not found
        """
        try:
            # Ensure date is timezone-aware
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            
            query = self.supabase.table("exchange_rates").select("rate").eq(
                "from_currency", from_currency
            ).eq("to_currency", to_currency).lte("timestamp", date.isoformat()).order(
                "timestamp", desc=True
            ).limit(1)
            
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                return Decimal(str(result.data[0]['rate']))
            else:
                logger.debug(f"No exchange rate found for {from_currency}/{to_currency} on {date}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting exchange rate: {e}")
            return None
    
    def get_exchange_rates(self, start_date: datetime, end_date: datetime, 
                          from_currency: str = 'USD', to_currency: str = 'CAD') -> List[Dict]:
        """Get exchange rates for a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            from_currency: Source currency (default: 'USD')
            to_currency: Target currency (default: 'CAD')
            
        Returns:
            List of dictionaries with 'timestamp' and 'rate' keys
        """
        try:
            # Ensure dates are timezone-aware
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            query = self.supabase.table("exchange_rates").select("timestamp, rate").eq(
                "from_currency", from_currency
            ).eq("to_currency", to_currency).gte(
                "timestamp", start_date.isoformat()
            ).lte("timestamp", end_date.isoformat()).order("timestamp")
            
            result = query.execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"❌ Error getting exchange rates: {e}")
            return []
    
    def get_latest_exchange_rate(self, from_currency: str = 'USD', to_currency: str = 'CAD') -> Optional[Decimal]:
        """Get the most recent exchange rate.
        
        Args:
            from_currency: Source currency (default: 'USD')
            to_currency: Target currency (default: 'CAD')
            
        Returns:
            Latest exchange rate as Decimal, or None if not found
        """
        try:
            query = self.supabase.table("exchange_rates").select("rate").eq(
                "from_currency", from_currency
            ).eq("to_currency", to_currency).order("timestamp", desc=True).limit(1)
            
            result = query.execute()
            
            if result.data and len(result.data) > 0:
                return Decimal(str(result.data[0]['rate']))
            else:
                logger.debug(f"No exchange rate found for {from_currency}/{to_currency}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error getting latest exchange rate: {e}")
            return None
    
    def upsert_exchange_rate(self, date: datetime, rate: Decimal, 
                            from_currency: str = 'USD', to_currency: str = 'CAD') -> bool:
        """Insert or update a single exchange rate.
        
        Args:
            date: Date for the exchange rate
            rate: Exchange rate value
            from_currency: Source currency (default: 'USD')
            to_currency: Target currency (default: 'CAD')
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure date is timezone-aware
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            
            rate_data = {
                'from_currency': from_currency,
                'to_currency': to_currency,
                'rate': float(rate),
                'timestamp': date.isoformat()
            }
            
            result = self.supabase.table("exchange_rates").upsert(
                rate_data,
                on_conflict="from_currency,to_currency,timestamp"
            ).execute()
            
            logger.info(f"✅ Upserted exchange rate: {from_currency}/{to_currency} = {rate} on {date.date()}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting exchange rate: {e}")
            return False
    
    def upsert_exchange_rates(self, rates: List[Dict]) -> bool:
        """Bulk insert or update exchange rates.
        
        Args:
            rates: List of dictionaries with keys: 'timestamp', 'rate', 'from_currency', 'to_currency'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not rates:
                return True
            
            # Ensure all timestamps are properly formatted
            formatted_rates = []
            for rate in rates:
                formatted_rate = rate.copy()
                
                # Ensure timestamp is ISO format
                if isinstance(formatted_rate.get('timestamp'), datetime):
                    timestamp = formatted_rate['timestamp']
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    formatted_rate['timestamp'] = timestamp.isoformat()
                
                # Ensure rate is float
                if isinstance(formatted_rate.get('rate'), Decimal):
                    formatted_rate['rate'] = float(formatted_rate['rate'])
                
                formatted_rates.append(formatted_rate)
            
            result = self.supabase.table("exchange_rates").upsert(
                formatted_rates,
                on_conflict="from_currency,to_currency,timestamp"
            ).execute()
            
            logger.info(f"✅ Upserted {len(formatted_rates)} exchange rates")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting exchange rates: {e}")
            return False