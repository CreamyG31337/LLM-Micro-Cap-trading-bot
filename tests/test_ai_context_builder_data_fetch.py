#!/usr/bin/env python3
"""
Test for AI Context Builder data fetching issues
=================================================

Tests that MarketDataFetcher is properly initialized and can fetch
price/volume and fundamentals data like the console app does.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pandas as pd
from datetime import datetime, timedelta

from market_data.data_fetcher import MarketDataFetcher
from market_data.price_cache import PriceCache
from market_data.market_hours import MarketHours
from config.settings import get_settings


def test_market_data_fetcher_initialization():
    """Test that MarketDataFetcher can be initialized with cache like console app."""
    # This is how console app initializes it (prompt_generator.py line 137-138)
    settings = get_settings()
    price_cache = PriceCache(settings=settings)
    market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
    
    assert market_data_fetcher is not None
    assert market_data_fetcher.cache is not None
    assert market_data_fetcher.cache == price_cache


def test_fetch_price_data_with_cache():
    """Test that we can fetch price data for test tickers."""
    settings = get_settings()
    price_cache = PriceCache(settings=settings)
    market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
    market_hours = MarketHours(settings=settings)
    
    # Test tickers from user's issue
    test_tickers = ["XMA.TO", "GMIN.TO", "SMH"]
    
    # Get trading day window
    start_d, end_d = market_hours.trading_day_window()
    # Get historical window for avg volume (90 days like console app)
    start_d = end_d - pd.Timedelta(days=90)
    
    for ticker in test_tickers:
        result = market_data_fetcher.fetch_price_data(ticker, start_d, end_d)
        
        # Should have data
        assert result.df is not None, f"Failed to fetch data for {ticker}"
        assert not result.df.empty, f"Empty data for {ticker}"
        assert "Close" in result.df.columns, f"No Close column for {ticker}"
        
        # Should have at least 2 days of data for % change calculation
        assert len(result.df) >= 2, f"Not enough data for {ticker} (need 2+ days)"
        
        # Should have volume data
        if "Volume" in result.df.columns:
            volume = result.df["Volume"].iloc[-1]
            assert pd.notna(volume) or volume > 0, f"No volume data for {ticker}"


def test_fetch_fundamentals_data():
    """Test that we can fetch fundamentals data for test tickers."""
    settings = get_settings()
    price_cache = PriceCache(settings=settings)
    market_data_fetcher = MarketDataFetcher(cache_instance=price_cache)
    
    # Test tickers from user's issue
    test_tickers = ["XMA.TO", "GMIN.TO", "SMH"]
    
    for ticker in test_tickers:
        fundamentals = market_data_fetcher.fetch_fundamentals(ticker)
        
        # Should have fundamentals data
        assert fundamentals is not None, f"Failed to fetch fundamentals for {ticker}"
        
        # Check that we have at least some data (not all N/A)
        # Market cap should be available for most tickers
        market_cap = fundamentals.get('marketCap', 'N/A')
        sector = fundamentals.get('sector', 'N/A')
        industry = fundamentals.get('industry', 'N/A')
        
        # At least one of these should not be N/A
        has_data = (
            market_cap != 'N/A' or 
            sector != 'N/A' or 
            industry != 'N/A'
        )
        
        assert has_data, f"All fundamentals are N/A for {ticker}: {fundamentals}"


def test_format_price_volume_table_integration():
    """Test the actual format_price_volume_table function with proper initialization."""
    from web_dashboard.ai_context_builder import format_price_volume_table
    
    # Create a test positions DataFrame
    positions_df = pd.DataFrame([
        {
            'symbol': 'XMA.TO',
            'ticker': 'XMA.TO',
            'current_price': 41.74,
            'price': 41.74
        },
        {
            'symbol': 'GMIN.TO',
            'ticker': 'GMIN.TO',
            'current_price': 38.17,
            'price': 38.17
        },
        {
            'symbol': 'SMH',
            'ticker': 'SMH',
            'current_price': 373.30,
            'price': 373.30
        }
    ])
    
    # Format the table
    result = format_price_volume_table(positions_df)
    
    # Should have output
    assert result is not None
    assert len(result) > 0
    
    # Should contain ticker symbols
    assert 'XMA.TO' in result
    assert 'GMIN.TO' in result
    assert 'SMH' in result
    
    # Should not have all N/A values (at least prices should be there)
    # Check that we have some actual data, not all N/A
    lines = result.split('\n')
    data_lines = [l for l in lines if 'XMA.TO' in l or 'GMIN.TO' in l or 'SMH' in l]
    
    for line in data_lines:
        # Should have price data (not all N/A)
        assert 'N/A' not in line or line.count('N/A') < 4, f"Too many N/A values in line: {line}"


def test_format_fundamentals_table_integration():
    """Test the actual format_fundamentals_table function with proper initialization."""
    from web_dashboard.ai_context_builder import format_fundamentals_table
    
    # Create a test positions DataFrame
    positions_df = pd.DataFrame([
        {
            'symbol': 'XMA.TO',
            'ticker': 'XMA.TO'
        },
        {
            'symbol': 'GMIN.TO',
            'ticker': 'GMIN.TO'
        },
        {
            'symbol': 'SMH',
            'ticker': 'SMH'
        }
    ])
    
    # Format the table
    result = format_fundamentals_table(positions_df)
    
    # Should have output
    assert result is not None
    assert len(result) > 0
    
    # Should contain ticker symbols
    assert 'XMA.TO' in result
    assert 'GMIN.TO' in result
    assert 'SMH' in result
    
    # Should not have all N/A values - check that we have some actual data
    lines = result.split('\n')
    data_lines = [l for l in lines if 'XMA.TO' in l or 'GMIN.TO' in l or 'SMH' in l]
    
    for line in data_lines:
        # Should have at least some non-N/A data
        # Count N/A occurrences - should not be all N/A
        na_count = line.count('N/A')
        assert na_count < 8, f"Too many N/A values in line: {line}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

