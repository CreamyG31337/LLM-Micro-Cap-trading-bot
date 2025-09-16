"""
Market data fetcher with robust Yahoo Finance -> Stooq fallback logic.

This module provides the MarketDataFetcher class that implements a multi-stage
fallback strategy for fetching OHLCV data:
1. Yahoo Finance via yfinance
2. Stooq via pandas-datareader  
3. Stooq direct CSV
4. Index proxies (e.g., ^GSPC->SPY, ^RUT->IWM) via Yahoo

The fetcher is designed to work with both current CSV storage and future database backends.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional pandas-datareader import for Stooq access
try:
    import pandas_datareader.data as pdr
    _HAS_PDR = True
except ImportError:
    _HAS_PDR = False
    # Downgrade to debug to avoid noisy warnings in terminal output
    logger.debug("pandas-datareader not available. Stooq PDR fallback disabled.")

# Known Stooq symbol remaps for common indices
STOOQ_MAP = {
    "^GSPC": "^SPX",  # S&P 500
    "^DJI": "^DJI",   # Dow Jones
    "^IXIC": "^IXIC", # Nasdaq Composite
    # "^RUT": not on Stooq; keep Yahoo
}

# Symbols we should *not* attempt on Stooq
STOOQ_BLOCKLIST = {"^RUT"}

# Index proxy mappings for fallback
PROXY_MAP = {
    "^GSPC": "SPY",   # S&P 500 -> SPDR S&P 500 ETF
    "^RUT": "IWM",    # Russell 2000 -> iShares Russell 2000 ETF
    "^IXIC": "QQQ",   # Nasdaq -> Invesco QQQ Trust
    "^DJI": "DIA",    # Dow Jones -> SPDR Dow Jones Industrial Average ETF
}


@dataclass
class FetchResult:
    """Result of a market data fetch operation."""
    df: pd.DataFrame
    source: str  # "yahoo" | "stooq-pdr" | "stooq-csv" | "yahoo:<proxy>-proxy" | "empty"


class MarketDataFetcher:
    """
    Robust market data fetcher with multi-stage fallback logic.
    
    Supports both current CSV-based storage and future database backends
    through a consistent interface.
    """
    
    def __init__(self, cache_instance: Optional[Any] = None):
        """
        Initialize the market data fetcher.
        
        Args:
            cache_instance: Optional cache instance for storing/retrieving data
        """
        self.cache = cache_instance
        self.proxy_map = PROXY_MAP.copy()
        
        # Access global settings for configurable TTL
        try:
            from config.settings import get_settings  # lazy import to avoid cycles
            self.settings = get_settings()
        except Exception:
            self.settings = None
        
        # In-memory fundamentals cache (TTL-based)
        self._fund_cache: Dict[str, Dict[str, Any]] = {}
        self._fund_cache_meta: Dict[str, Dict[str, Any]] = {}
        ttl_hours = 12
        try:
            if self.settings:
                ttl_hours = int(self.settings.get('market_data.fundamentals_cache_ttl_hours', 12))
        except Exception:
            ttl_hours = 12
        self._fund_cache_ttl = timedelta(hours=ttl_hours)
        
        # Load fundamentals overrides (one-time load)
        self._fundamentals_overrides: Dict[str, Dict[str, Any]] = {}
        self._load_fundamentals_overrides()
        
        # Attempt to load fundamentals cache from disk
        try:
            self._load_fundamentals_cache()
        except Exception as e:
            logging.getLogger(__name__).debug(f"Could not load fundamentals cache: {e}")
    
    def _load_fundamentals_overrides(self) -> None:
        """Load fundamentals overrides from JSON file to correct misleading API data."""
        try:
            # Look for overrides file in config directory
            project_root = Path(__file__).parent.parent
            overrides_path = project_root / "config" / "fundamentals_overrides.json"
            
            if not overrides_path.exists():
                logger.debug(f"Fundamentals overrides file not found: {overrides_path}")
                return
                
            import json
            with open(overrides_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract ticker overrides (skip metadata fields starting with _)
            for ticker, overrides in data.items():
                if not ticker.startswith('_'):
                    self._fundamentals_overrides[ticker.upper()] = overrides
                    
            logger.debug(f"Loaded fundamentals overrides for {len(self._fundamentals_overrides)} tickers")
            
        except Exception as e:
            logger.debug(f"Failed to load fundamentals overrides: {e}")
    
    def _apply_fundamentals_overrides(self, ticker_key: str, fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        """Apply overrides to fundamentals data if they exist for the ticker.
        
        Args:
            ticker_key: Uppercase ticker symbol
            fundamentals: Base fundamentals data from API
            
        Returns:
            Fundamentals data with overrides applied
        """
        overrides = self._fundamentals_overrides.get(ticker_key)
        if not overrides:
            return fundamentals
            
        # Create a copy to avoid modifying the original
        result = fundamentals.copy()
        
        # Apply each override field
        for field, value in overrides.items():
            # Skip metadata fields  
            if field.startswith('_') or field == 'description_note':
                continue
                
            # Apply the override value
            result[field] = str(value) if value is not None else 'N/A'
            
        logger.debug(f"Applied {len([k for k in overrides.keys() if not k.startswith('_') and k != 'description_note'])} overrides for {ticker_key}")
        return result
    
    def fetch_price_data(
        self,
        ticker: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        period: str = "1d",
        **kwargs: Any
    ) -> FetchResult:
        """
        Fetch OHLCV data with robust fallback logic.
        
        Args:
            ticker: Stock ticker symbol
            start: Start date for data fetch
            end: End date for data fetch  
            period: Period for data (default "1d")
            **kwargs: Additional arguments passed to yfinance
            
        Returns:
            FetchResult with DataFrame and source information
        """
        # Check cache first if available
        if self.cache:
            cached_data = self.cache.get_cached_price(ticker, start, end)
            if cached_data is not None:
                return FetchResult(cached_data, "cache")
        
        # Determine date range
        start_date, end_date = self._weekend_safe_range(period, start, end)
        
        # Stage 1: Yahoo Finance
        result = self._fetch_yahoo_data(ticker, start_date, end_date, **kwargs)
        if not result.df.empty:
            self._cache_result(ticker, result)
            return result
            
        # Stage 2: Stooq via pandas-datareader
        result = self._fetch_stooq_pdr(ticker, start_date, end_date)
        if not result.df.empty:
            self._cache_result(ticker, result)
            return result
            
        # Stage 3: Stooq direct CSV
        result = self._fetch_stooq_csv(ticker, start_date, end_date)
        if not result.df.empty:
            self._cache_result(ticker, result)
            return result
            
        # Stage 4: Index proxies
        result = self._fetch_proxy_data(ticker, start_date, end_date, **kwargs)
        if not result.df.empty:
            self._cache_result(ticker, result)
            return result
            
        # All methods failed
        logger.warning(f"All fetch methods failed for {ticker}")
        return FetchResult(pd.DataFrame(), "empty")
    
    def _weekend_safe_range(
        self,
        period: str,
        start: Optional[datetime],
        end: Optional[datetime]
    ) -> tuple[pd.Timestamp, pd.Timestamp]:
        """
        Calculate weekend-safe date range for data fetching.
        
        Args:
            period: Period string (e.g., "1d", "5d")
            start: Optional start date
            end: Optional end date
            
        Returns:
            Tuple of (start_timestamp, end_timestamp)
        """
        if start and end:
            return pd.Timestamp(start), pd.Timestamp(end)
            
        # Default to recent trading days
        now = pd.Timestamp.now()
        
        # Map period to days
        period_days = {
            "1d": 1, "5d": 5, "1mo": 30, "3mo": 90,
            "6mo": 180, "1y": 365, "2y": 730, "5y": 1825
        }
        
        days = period_days.get(period, 5)
        start_ts = now - timedelta(days=days + 10)  # Extra buffer for weekends
        end_ts = now + timedelta(days=1)  # Include today
        
        return start_ts, end_ts
    
    def _fetch_yahoo_data(
        self,
        ticker: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        **kwargs: Any
    ) -> FetchResult:
        """Fetch data from Yahoo Finance via yfinance."""
        try:
            import yfinance as yf
            
            # Suppress yfinance logging
            logging.getLogger("yfinance").setLevel(logging.ERROR)
            
            # Use Ticker.history() instead of yf.download() for single ticker
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(
                start=start,
                end=end,
                **kwargs
            )
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                # Remove extra columns that aren't OHLCV
                ohlcv_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                df = df[ohlcv_columns]
                df = self._normalize_ohlcv(self._to_datetime_index(df))
                return FetchResult(df, "yahoo")
                
        except Exception as e:
            logger.debug(f"Yahoo fetch failed for {ticker}: {e}")
            
        return FetchResult(pd.DataFrame(), "empty")
    
    def _fetch_stooq_pdr(
        self,
        ticker: str,
        start: pd.Timestamp,
        end: pd.Timestamp
    ) -> FetchResult:
        """Fetch data from Stooq via pandas-datareader."""
        if not _HAS_PDR or ticker in STOOQ_BLOCKLIST:
            return FetchResult(pd.DataFrame(), "empty")
            
        try:
            # Map ticker for Stooq
            stooq_ticker = STOOQ_MAP.get(ticker, ticker)
            if not stooq_ticker.startswith("^"):
                stooq_ticker = stooq_ticker.lower()
                # Handle Canadian tickers (.TO suffix) - keep as is for Stooq
                if not stooq_ticker.endswith(".to") and not stooq_ticker.endswith(".us"):
                    # Default to .us for US tickers if no suffix
                    stooq_ticker += ".us"
            
            df = cast(pd.DataFrame, pdr.DataReader(
                stooq_ticker, "stooq", start=start, end=end
            ))
            
            if isinstance(df, pd.DataFrame) and not df.empty:
                df.sort_index(inplace=True)
                df = self._normalize_ohlcv(self._to_datetime_index(df))
                return FetchResult(df, "stooq-pdr")
                
        except Exception as e:
            logger.debug(f"Stooq PDR fetch failed for {ticker}: {e}")
            
        return FetchResult(pd.DataFrame(), "empty")
    
    def _fetch_stooq_csv(
        self,
        ticker: str,
        start: pd.Timestamp,
        end: pd.Timestamp
    ) -> FetchResult:
        """Fetch data from Stooq CSV endpoint."""
        if ticker in STOOQ_BLOCKLIST:
            return FetchResult(pd.DataFrame(), "empty")
            
        try:
            import requests
            import io
            
            # Map ticker for Stooq
            stooq_ticker = STOOQ_MAP.get(ticker, ticker)
            
            # Stooq daily CSV: lowercase; handle different exchanges
            if not stooq_ticker.startswith("^"):
                sym = stooq_ticker.lower()
            else:
                sym = stooq_ticker.lower()
            
            url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Parse CSV
            df = pd.read_csv(io.StringIO(response.text))
            df["Date"] = pd.to_datetime(df["Date"])
            df.set_index("Date", inplace=True)
            df.sort_index(inplace=True)
            
            # Filter to [start, end) (Stooq end is exclusive)
            df = df.loc[(df.index >= start.normalize()) & (df.index < end.normalize())]
            
            # Normalize to Yahoo-like schema
            if "Adj Close" not in df.columns:
                df["Adj Close"] = df["Close"]
                
            if not df.empty:
                df = self._normalize_ohlcv(df)
                return FetchResult(df, "stooq-csv")
                
        except Exception as e:
            logger.debug(f"Stooq CSV fetch failed for {ticker}: {e}")
            
        return FetchResult(pd.DataFrame(), "empty")
    
    def _fetch_proxy_data(
        self,
        ticker: str,
        start: pd.Timestamp,
        end: pd.Timestamp,
        **kwargs: Any
    ) -> FetchResult:
        """Fetch data using proxy ticker (e.g., ^GSPC -> SPY)."""
        proxy = self.proxy_map.get(ticker)
        if not proxy:
            return FetchResult(pd.DataFrame(), "empty")
            
        try:
            result = self._fetch_yahoo_data(proxy, start, end, **kwargs)
            if not result.df.empty:
                return FetchResult(result.df, f"yahoo:{proxy}-proxy")
                
        except Exception as e:
            logger.debug(f"Proxy fetch failed for {ticker} -> {proxy}: {e}")
            
        return FetchResult(pd.DataFrame(), "empty")
    
    def _to_datetime_index(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame index to datetime if needed."""
        if not isinstance(df.index, pd.DatetimeIndex):
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            else:
                df.index = pd.to_datetime(df.index)
        return df
    
    def _normalize_ohlcv(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize OHLCV DataFrame to standard format with Decimal conversion."""
        from decimal import Decimal
        
        # Ensure required columns exist
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        existing_cols = [col for col in required_cols if col in df.columns]
        
        # Add Adj Close if missing
        if "Adj Close" not in df.columns and "Close" in df.columns:
            df["Adj Close"] = df["Close"]
            
        # Return only the columns we need
        cols = existing_cols + (["Adj Close"] if "Adj Close" in df.columns else [])
        result_df = df[cols].copy()
        
        # Convert all price columns to Decimal for precision
        price_cols = [col for col in cols if col != "Volume"]
        for col in price_cols:
            if col in result_df.columns:
                # Convert float to Decimal string to avoid precision errors
                result_df[col] = result_df[col].apply(
                    lambda x: Decimal(str(round(x, 6))) if pd.notna(x) and x != 0 else Decimal('0')
                )
        
        # Volume stays as int/float since it's not monetary
        return result_df
    
    def _cache_result(self, ticker: str, result: FetchResult) -> None:
        """Cache the fetch result if cache is available."""
        if self.cache and not result.df.empty:
            self.cache.cache_price_data(ticker, result.df, result.source)
    
    # -------------------- Fundamentals cache persistence --------------------
    def _get_fund_cache_path(self) -> Optional[Path]:
        """Determine the cache file path for fundamentals."""
        try:
            if self.cache and getattr(self.cache, 'settings', None):
                data_dir = self.cache.settings.get_data_directory()
                cache_dir = Path(data_dir) / ".cache"
            elif getattr(self, 'settings', None):
                data_dir = self.settings.get_data_directory()
                cache_dir = Path(data_dir) / ".cache"
            else:
                # Fallback to current working directory .cache
                cache_dir = Path.cwd() / ".cache"
            cache_dir.mkdir(exist_ok=True)
            return cache_dir / "fundamentals_cache.json"
        except Exception:
            return None
    
    def _load_fundamentals_cache(self) -> None:
        """Load fundamentals cache from disk if available."""
        path = self._get_fund_cache_path()
        if not path or not path.exists():
            return
        import json
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            entries: Dict[str, Dict[str, Any]] = data.get('entries', {})
            ttl_minutes: int = data.get('default_ttl_minutes', int(self._fund_cache_ttl.total_minutes()) if hasattr(self._fund_cache_ttl, 'total_minutes') else int(self._fund_cache_ttl.total_seconds() // 60))
            default_ttl = timedelta(minutes=ttl_minutes)
            for ticker_key, payload in entries.items():
                fund = payload.get('data', {})
                ts_str = payload.get('ts')
                ttl_min = payload.get('ttl_minutes', ttl_minutes)
                try:
                    ts = datetime.fromisoformat(ts_str) if ts_str else None
                except Exception:
                    ts = None
                # Skip expired entries
                if ts and (datetime.now() - ts) < timedelta(minutes=ttl_min):
                    self._fund_cache[ticker_key] = fund
                    self._fund_cache_meta[ticker_key] = {
                        'ts': ts,
                        'ttl': timedelta(minutes=ttl_min) if ttl_min else default_ttl
                    }
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to load fundamentals cache: {e}")
    
    def _save_fundamentals_cache(self) -> None:
        """Save fundamentals cache to disk."""
        path = self._get_fund_cache_path()
        if not path:
            return
        import json
        try:
            # Build serializable structure
            entries: Dict[str, Any] = {}
            for ticker_key, fund in self._fund_cache.items():
                meta = self._fund_cache_meta.get(ticker_key, {})
                ts = meta.get('ts')
                ttl = meta.get('ttl', self._fund_cache_ttl)
                entries[ticker_key] = {
                    'data': fund,
                    'ts': ts.isoformat() if isinstance(ts, datetime) else None,
                    'ttl_minutes': int(ttl.total_seconds() // 60) if isinstance(ttl, timedelta) else int(self._fund_cache_ttl.total_seconds() // 60)
                }
            payload = {
                'entries': entries,
                'default_ttl_minutes': int(self._fund_cache_ttl.total_seconds() // 60)
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logging.getLogger(__name__).debug(f"Failed to save fundamentals cache: {e}")
    
    def fetch_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """Fetch fundamental data for a ticker using yfinance with TTL cache.
        
        Returns:
            Dict with keys: sector, industry, country, marketCap, trailingPE, 
            dividendYield, fiftyTwoWeekHigh, fiftyTwoWeekLow, or "N/A" if unavailable
        """
        ticker_key = ticker.upper().strip()
        
        # Check in-memory TTL cache first
        meta = self._fund_cache_meta.get(ticker_key)
        if meta:
            ts: datetime = meta.get('ts')
            ttl: timedelta = meta.get('ttl', self._fund_cache_ttl)
            if ts and (datetime.now() - ts) < ttl:
                cached = self._fund_cache.get(ticker_key)
                if cached:
                    # Apply overrides to cached data before returning
                    return self._apply_fundamentals_overrides(ticker_key, cached)
            else:
                # Expired
                self._fund_cache.pop(ticker_key, None)
                self._fund_cache_meta.pop(ticker_key, None)
        
        fundamentals = {
            'sector': 'N/A',
            'industry': 'N/A', 
            'country': 'N/A',
            'marketCap': 'N/A',
            'trailingPE': 'N/A',
            'dividendYield': 'N/A',
            'fiftyTwoWeekHigh': 'N/A',
            'fiftyTwoWeekLow': 'N/A'
        }
        
        try:
            import yfinance as yf
            
            # Suppress yfinance logging
            logging.getLogger("yfinance").setLevel(logging.ERROR)
            
            ticker_obj = yf.Ticker(ticker)
            
            # Try new get_info() first, fallback to .info for compatibility
            info = {}
            try:
                get_info = getattr(ticker_obj, 'get_info', None)
                if callable(get_info):
                    info = get_info() or {}
            except Exception:
                info = {}
            if not info:
                try:
                    info = ticker_obj.info or {}
                except Exception:
                    info = {}
            
            # fast_info for performant fields
            try:
                finfo = getattr(ticker_obj, 'fast_info', None)
            except Exception:
                finfo = None
            finfo = finfo or {}
            
            # Current price (for computed dividend yield)
            price = None
            try:
                price = finfo.get('last_price')
            except Exception:
                price = None
            if not price:
                # Fallback to recent close
                try:
                    pr = self.fetch_price_data(ticker, period='5d')
                    if not pr.df.empty and 'Close' in pr.df.columns:
                        # Price is now Decimal from _normalize_ohlcv, convert to float for display only
                        price = float(pr.df['Close'].iloc[-1])
                except Exception:
                    price = None
            
            # Extract available fields with fallbacks
            fundamentals['sector'] = info.get('sector', 'N/A') or 'N/A'
            fundamentals['industry'] = info.get('industry', 'N/A') or 'N/A'
            fundamentals['country'] = info.get('country', 'N/A') or 'N/A'
            
            # Market cap with formatting - check for ETF first
            company_name = info.get('longName', ticker) or ticker
            market_cap = info.get('marketCap')
            if 'ETF' in company_name.upper():
                fundamentals['marketCap'] = 'ETF'
            else:
                if not market_cap and finfo:
                    market_cap = finfo.get('market_cap')
                if market_cap and isinstance(market_cap, (int, float)) and market_cap > 0:
                    if market_cap >= 1e9:
                        fundamentals['marketCap'] = f"${market_cap/1e9:.2f}B"
                    elif market_cap >= 1e6:
                        fundamentals['marketCap'] = f"${market_cap/1e6:.1f}M"
                    else:
                        fundamentals['marketCap'] = f"${market_cap:,.0f}"
            
            # P/E ratio
            pe_ratio = info.get('trailingPE')
            if not pe_ratio and finfo:
                pe_ratio = finfo.get('trailing_pe')
            if pe_ratio and isinstance(pe_ratio, (int, float)) and pe_ratio > 0:
                fundamentals['trailingPE'] = f"{pe_ratio:.1f}"
                
            # Dividend yield (prefer computed from last 365 days of dividends)
            computed_yield = None
            try:
                div_series = ticker_obj.dividends
                if div_series is not None and not div_series.empty and price and price > 0:
                    recent = div_series[div_series.index >= pd.Timestamp.now() - pd.Timedelta(days=365)]
                    if not recent.empty:
                        annual_div = float(recent.sum())
                        if annual_div > 0:
                            computed_yield = (annual_div / float(price)) * 100.0
            except Exception:
                computed_yield = None
            
            if computed_yield is not None:
                fundamentals['dividendYield'] = f"{computed_yield:.1f}%"
            else:
                # Normalize possibly inconsistent API fields
                div_yield = info.get('dividendYield')
                if not div_yield:
                    div_yield = info.get('trailingAnnualDividendYield')
                if div_yield and isinstance(div_yield, (int, float)) and div_yield > 0:
                    if div_yield > 1.0:
                        # Assume already percent
                        fundamentals['dividendYield'] = f"{div_yield:.1f}%"
                    else:
                        fundamentals['dividendYield'] = f"{div_yield*100:.1f}%"
            
            # 52-week high/low
            high_52w = info.get('fiftyTwoWeekHigh')
            low_52w = info.get('fiftyTwoWeekLow')
            # Try fast_info names
            if not high_52w and finfo:
                high_52w = finfo.get('year_high') or finfo.get('fifty_two_week_high')
            if not low_52w and finfo:
                low_52w = finfo.get('year_low') or finfo.get('fifty_two_week_low')
            
            # As a final fallback, compute from last ~1y of history
            if (not high_52w or not low_52w):
                try:
                    hist = self.fetch_price_data(ticker, period='1y')
                    if not hist.df.empty:
                        if not high_52w and 'High' in hist.df.columns:
                            # High/Low are now Decimals from _normalize_ohlcv, convert to float for display only
                            high_52w = float(hist.df['High'].max())
                        if not low_52w and 'Low' in hist.df.columns:
                            # High/Low are now Decimals from _normalize_ohlcv, convert to float for display only
                            low_52w = float(hist.df['Low'].min())
                except Exception:
                    pass
            
            if high_52w and isinstance(high_52w, (int, float)):
                fundamentals['fiftyTwoWeekHigh'] = f"${high_52w:.2f}"
            if low_52w and isinstance(low_52w, (int, float)):
                fundamentals['fiftyTwoWeekLow'] = f"${low_52w:.2f}"
                
            # Normalize country names and apply fallbacks
            country = fundamentals['country']
            if country and country != 'N/A':
                # Normalize common country names to shorter versions
                country_map = {
                    'United States': 'USA',
                    'United States of America': 'USA',
                    'US': 'USA',
                    'Canada': 'Canada',
                    'United Kingdom': 'UK',
                    'Great Britain': 'UK'
                }
                fundamentals['country'] = country_map.get(country, country)
            
            # Country fallback based on ticker suffix
            if fundamentals['country'] == 'N/A':
                if ticker.endswith('.TO') or ticker.endswith('.V'):
                    fundamentals['country'] = 'Canada'
                else:
                    fundamentals['country'] = 'USA'
                    
        except Exception as e:
            logger.debug(f"Fundamentals fetch failed for {ticker}: {e}")
            
        # Store in cache (even if partial) to avoid repeated calls in same run
        self._fund_cache[ticker_key] = fundamentals
        self._fund_cache_meta[ticker_key] = {
            'ts': datetime.now(),
            'ttl': self._fund_cache_ttl
        }
        
        # Persist to disk (best-effort)
        try:
            self._save_fundamentals_cache()
        except Exception as e:
            logging.getLogger(__name__).debug(f"Could not save fundamentals cache: {e}")
        
        # Apply overrides before returning
        return self._apply_fundamentals_overrides(ticker_key, fundamentals)
