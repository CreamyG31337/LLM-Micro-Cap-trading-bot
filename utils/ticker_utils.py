"""Ticker symbol utilities.

This module provides functions for normalizing and validating ticker symbols,
including adding appropriate suffixes for different markets. Uses yfinance
to intelligently detect Canadian vs US stocks.
"""

import re
import logging
from typing import Optional, Union
from decimal import Decimal

logger = logging.getLogger(__name__)

# Cache for ticker corrections to avoid repeated API calls
TICKER_CORRECTION_CACHE = {}


def detect_currency_context(ticker: str, buy_price: float = None) -> str:
    """
    Detect if a ticker is likely Canadian based on context clues.
    Returns 'CAD', 'USD', or 'UNKNOWN'
    """
    # If we have a buy price, use it as a clue
    if buy_price is not None:
        # Canadian small-caps typically trade in the $1-50 range
        # US small-caps can be much higher
        if 1 <= buy_price <= 50:
            return 'CAD'  # More likely Canadian
        elif buy_price > 50:
            return 'USD'  # More likely US
    
    # Check if ticker has Canadian characteristics
    canadian_patterns = [
        # Common Canadian company name patterns
        'CAN', 'CANADA', 'NORTH', 'NORTHERN', 'WESTERN', 'EASTERN',
        'QUEBEC', 'ONTARIO', 'ALBERTA', 'BRITISH', 'COLUMBIA'
    ]
    
    ticker_upper = ticker.upper()
    for pattern in canadian_patterns:
        if pattern in ticker_upper:
            return 'CAD'
    
    return 'UNKNOWN'


def detect_and_correct_ticker(ticker: str, buy_price: float = None) -> str:
    """
    Detect if a ticker is Canadian and automatically add the appropriate suffix.
    Tests all variants (.TO, .V, and no suffix) and asks user if multiple matches found.
    
    Returns the corrected ticker symbol with appropriate suffix.
    """
    ticker = ticker.upper().strip()
    
    # Check cache first
    if ticker in TICKER_CORRECTION_CACHE:
        return TICKER_CORRECTION_CACHE[ticker]
    
    # If already has a suffix, return as-is
    if any(ticker.endswith(suffix) for suffix in ['.TO', '.V', '.CN', '.NE']):
        TICKER_CORRECTION_CACHE[ticker] = ticker
        return ticker
    
    try:
        import yfinance as yf
        import logging
        
        # Suppress all yfinance logging and warnings
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)
        
        # Test all variants
        variants_to_test = [
            ticker,           # No suffix (US)
            f"{ticker}.TO",   # TSX
            f"{ticker}.V",    # TSX Venture
        ]
        
        valid_matches = []
        
        for variant in variants_to_test:
            try:
                stock = yf.Ticker(variant)
                info = stock.info
                
                # Check if we get valid info (not just empty dict)
                if info and info.get('symbol') and info.get('symbol') != 'N/A':
                    exchange = info.get('exchange', '')
                    name = info.get('longName', info.get('shortName', ''))
                    
                    # Only count as valid if we have a real exchange AND a real company name
                    if (exchange and exchange != 'N/A' and 
                        name and name != 'N/A' and name != 'Unknown' and 
                        len(name) > 3):  # Real company names are longer than 3 chars
                        valid_matches.append({
                            'ticker': variant,
                            'exchange': exchange,
                            'name': name
                        })
            except Exception as e:
                # Silently skip invalid tickers - don't show 404 errors to user
                continue
        
        # If no valid matches found, return original
        if not valid_matches:
            TICKER_CORRECTION_CACHE[ticker] = ticker
            return ticker
        
        # If only one match, use it
        if len(valid_matches) == 1:
            result = valid_matches[0]['ticker']
            TICKER_CORRECTION_CACHE[ticker] = result
            logger.info(f"Auto-corrected ticker {ticker} to {result}")
            return result
        
        # Multiple matches found - ask user to choose
        print(f"\n🔍 Multiple valid tickers found for '{ticker}':")
        for i, match in enumerate(valid_matches, 1):
            print(f"  {i}. {match['ticker']} - {match['name']} ({match['exchange']})")
        
        while True:
            try:
                choice = input(f"Select ticker (1-{len(valid_matches)}) or press Enter for {ticker}: ").strip()
                if not choice:
                    # Default to original if no choice made
                    result = ticker
                    break
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(valid_matches):
                    result = valid_matches[choice_idx]['ticker']
                    break
                else:
                    print(f"Please enter a number between 1 and {len(valid_matches)}")
            except ValueError:
                print("Please enter a valid number")
        
        TICKER_CORRECTION_CACHE[ticker] = result
        return result
        
    except Exception as e:
        logger.warning(f"Could not detect ticker type for {ticker}: {e}")
        # Default to original ticker
        TICKER_CORRECTION_CACHE[ticker] = ticker
        return ticker


def normalize_ticker_symbol(ticker: str, currency: str = "CAD", buy_price: Union[float, Decimal, None] = None) -> str:
    """Normalize ticker symbol using intelligent detection.
    
    Args:
        ticker: Raw ticker symbol from user input
        currency: Currency code (CAD or USD) - used as hint
        buy_price: Optional buy price for context clues
        
    Returns:
        Normalized ticker symbol with appropriate suffix
        
    Examples:
        normalize_ticker_symbol("VEE", "CAD", 44.59) -> "VEE.TO"
        normalize_ticker_symbol("AAPL", "USD", 150.0) -> "AAPL"
        normalize_ticker_symbol("VEE.TO", "CAD") -> "VEE.TO"  # Already normalized
    """
    if not ticker:
        return ticker
    
    # Use the intelligent detection function
    return detect_and_correct_ticker(ticker, buy_price)


def is_canadian_ticker(ticker: str) -> bool:
    """Check if ticker is Canadian based on suffix.
    
    Args:
        ticker: Ticker symbol to check
        
    Returns:
        True if Canadian ticker, False otherwise
    """
    if not ticker:
        return False
    
    ticker = ticker.upper().strip()
    return (ticker.endswith('.TO') or 
            ticker.endswith('.V') or 
            ticker.endswith('.CN') or
            ticker.endswith('.TSX'))


def is_us_ticker(ticker: str) -> bool:
    """Check if ticker is US based on format.
    
    Args:
        ticker: Ticker symbol to check
        
    Returns:
        True if US ticker, False otherwise
    """
    if not ticker:
        return False
    
    ticker = ticker.upper().strip()
    return (not is_canadian_ticker(ticker) and 
            not ticker.startswith('^') and
            not ticker.endswith('.L'))  # London Stock Exchange


def get_ticker_currency(ticker: str) -> str:
    """Get currency for ticker based on suffix.
    
    Args:
        ticker: Ticker symbol
        
    Returns:
        Currency code ('CAD' or 'USD')
    """
    if is_canadian_ticker(ticker):
        return 'CAD'
    elif is_us_ticker(ticker):
        return 'USD'
    else:
        # Default to USD for unknown formats
        return 'USD'


def validate_ticker_format(ticker: str) -> bool:
    """Validate ticker symbol format.
    
    Args:
        ticker: Ticker symbol to validate
        
    Returns:
        True if valid format, False otherwise
    """
    if not ticker or not isinstance(ticker, str):
        return False
    
    ticker = ticker.strip().upper()
    if not ticker:
        return False
    
    # Valid tickers: start with a letter; allow letters/digits/dot/dash afterwards
    pattern = r"^[A-Za-z][A-Za-z0-9\.-]*$"
    return bool(re.fullmatch(pattern, ticker))


def get_company_name(ticker: str) -> str:
    """Get company name for ticker symbol with Canadian suffix support and caching.

    Order of resolution:
    1) Read from persisted name cache (PriceCache)
    2) Try different ticker variants (.TO, .V, no suffix) with yfinance
    3) Persist successful lookups to cache

    Args:
        ticker: Ticker symbol

    Returns:
        Company name or 'Unknown' if not found
    """
    if not ticker:
        return 'Unknown'

    try:
        from market_data.price_cache import PriceCache
        pc = PriceCache()
        key = ticker.upper().strip()
        
        # Check if we have currency info that might indicate a different variant should be used
        # If so, clear the cache to force a fresh lookup
        try:
            import pandas as pd
            import glob
            
            # Load currency cache from portfolio files
            portfolio_files = glob.glob('trading_data/funds/*/llm_portfolio_update.csv')
            currency_cache = {}
            
            for file_path in portfolio_files:
                try:
                    df = pd.read_csv(file_path)
                    if 'Ticker' in df.columns and 'Currency' in df.columns:
                        latest_entries = df.groupby('Ticker').last()
                        for ticker, row in latest_entries.iterrows():
                            currency_cache[ticker] = row['Currency']
                except Exception:
                    continue
            
            currency = currency_cache.get(key)
            if currency == 'CAD' and not key.endswith(('.TO', '.V')):
                # This is a Canadian ticker without suffix, clear cache to force fresh lookup
                pc.clear_company_name_cache(key)
                logger.debug(f"Cleared cache for Canadian ticker {key}")
        except Exception:
            pass
        
        cached = pc.get_company_name(key)
        if cached:
            return cached
    except Exception:
        pc = None
        key = ticker.upper().strip()

    # Try different ticker variants for better coverage
    name = 'Unknown'
    successful_ticker = key

    # Use currency-based logic to determine which variants to try first
    variants_to_try = []
    
    # Check if this is a Canadian ticker based on currency in portfolio data
    is_likely_canadian = key.endswith(('.TO', '.V'))  # Already has Canadian suffix
    
    # If no suffix, check if we have currency info from portfolio
    if not is_likely_canadian:
        try:
            import pandas as pd
            import glob
            
            # Load currency cache from portfolio files
            portfolio_files = glob.glob('trading_data/funds/*/llm_portfolio_update.csv')
            currency_cache = {}
            
            for file_path in portfolio_files:
                try:
                    df = pd.read_csv(file_path)
                    if 'Ticker' in df.columns and 'Currency' in df.columns:
                        latest_entries = df.groupby('Ticker').last()
                        for ticker, row in latest_entries.iterrows():
                            currency_cache[ticker] = row['Currency']
                except Exception:
                    continue
            
            currency = currency_cache.get(key)
            if currency == 'CAD':
                is_likely_canadian = True
            elif currency == 'USD':
                is_likely_canadian = False
        except Exception:
            pass

    if any(key.endswith(suffix) for suffix in ['.TO', '.V', '.CN', '.NE']):
        # Has suffix - try with suffix first, then without
        variants_to_try = [key, key.rsplit('.', 1)[0]]
    elif is_likely_canadian:
        # Likely Canadian - try Canadian suffixes first
        variants_to_try = [f"{key}.TO", f"{key}.V", key]
    else:
        # Likely US - try US first, then Canadian as fallback
        variants_to_try = [key, f"{key}.TO", f"{key}.V"]

    try:
        import yfinance as yf
        import logging

        # Suppress all yfinance logging and warnings
        logging.getLogger("yfinance").setLevel(logging.CRITICAL)

        for variant in variants_to_try:
            try:
                stock = yf.Ticker(variant)
                info = stock.info

                # Check for valid company name
                if info and (info.get('longName') or info.get('shortName')):
                    candidate_name = info.get('longName') or info.get('shortName')
                    country = info.get('country', '')

                    # Make sure it's not just "N/A" or generic
                    if (candidate_name and
                        candidate_name != 'N/A' and
                        candidate_name != 'Unknown' and
                        len(candidate_name.strip()) > 3):  # Real names are longer than 3 chars

                        name = candidate_name.strip()
                        successful_ticker = variant
                        logger.debug(f"Found company name for {key}: {name} (using {variant}, country: {country})")
                        
                        # If this is a Canadian variant and we're looking for a Canadian ticker, use it
                        if is_likely_canadian and (variant.endswith('.TO') or variant.endswith('.V') or country == 'Canada'):
                            logger.debug(f"Using Canadian variant for {key}: {name}")
                            break
                        # If this is a US variant and we're looking for a US ticker, use it
                        elif not is_likely_canadian and not variant.endswith('.TO') and not variant.endswith('.V') and country != 'Canada':
                            logger.debug(f"Using US variant for {key}: {name}")
                            break
                        # If this is the first valid name we found, use it as fallback
                        elif name == 'Unknown':
                            logger.debug(f"Using fallback variant for {key}: {name}")
                            break

            except Exception as e:
                # Continue to next variant if this one fails
                logger.debug(f"Failed to get info for {variant}: {e}")
                continue

    except Exception as e:
        logger.debug(f"Error during company name lookup for {key}: {e}")

    # Persist to cache if available and we found a name
    try:
        if name != 'Unknown' and pc is not None:
            pc.cache_company_name(key, name)
            pc.save_persistent_cache()
            logger.debug(f"Cached company name for {key}: {name}")
    except Exception as e:
        logger.debug(f"Could not cache company name for {key}: {e}")

    return name
