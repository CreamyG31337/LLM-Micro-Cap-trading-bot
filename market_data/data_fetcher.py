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
        """Normalize OHLCV DataFrame to standard format."""
        # Ensure required columns exist
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        existing_cols = [col for col in required_cols if col in df.columns]
        
        # Add Adj Close if missing
        if "Adj Close" not in df.columns and "Close" in df.columns:
            df["Adj Close"] = df["Close"]
            
        # Return only the columns we need
        cols = existing_cols + (["Adj Close"] if "Adj Close" in df.columns else [])
        return df[cols]
    
    def _cache_result(self, ticker: str, result: FetchResult) -> None:
        """Cache the fetch result if cache is available."""
        if self.cache and not result.df.empty:
            self.cache.cache_price_data(ticker, result.df, result.source)