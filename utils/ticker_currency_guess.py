"""
Ticker-Based Currency Guessing Utilities

⚠️ WARNING: THESE FUNCTIONS ARE FOR DEBUGGING AND IMPORT SCRIPTS ONLY ⚠️

These functions GUESS currency from ticker symbols, which is unreliable and should
NEVER be used in production portfolio calculations. They caused a 12% portfolio
inflation bug when used in the main trading system.

For production code, ALWAYS use the 'currency' field from position data:
    if position.currency == 'USD':
        # Convert USD to CAD
    else:
        # Already in CAD

These functions are kept only for:
- Webull import scripts (where currency data might be missing)
- Debug utilities (where guessing is acceptable)
- Data migration tools (as a fallback when no currency field exists)

DO NOT import these functions in production trading code!
"""

import logging

logger = logging.getLogger(__name__)

def guess_currency_from_ticker_UNSAFE(ticker: str) -> str:
    """
    ⚠️ UNSAFE: Guess currency from ticker symbol (unreliable).
    
    This function attempts to guess whether a ticker is USD or CAD based on
    ticker patterns. It's unreliable and should NEVER be used in production.
    
    Args:
        ticker: Ticker symbol to analyze
        
    Returns:
        'USD' or 'CAD' (best guess only)
        
    ⚠️ WARNING: This is a GUESS and may be wrong! Use position.currency in production.
    """
    ticker = ticker.upper().strip()
    
    # Canadian tickers with explicit suffixes
    canadian_suffixes = ['.TO', '.V', '.CN', '.TSX']
    if any(ticker.endswith(suffix) for suffix in canadian_suffixes):
        return 'CAD'
    
    # Index tickers or other non-US markets
    if ticker.startswith('^') or ticker.endswith('.L'):
        return 'CAD'  # Default to CAD for non-US
    
    # Otherwise, guess USD (this is where the bug was!)
    # Many Canadian tickers don't have suffixes and get misclassified here
    return 'USD'


def is_us_ticker_GUESS_ONLY(ticker: str) -> bool:
    """
    ⚠️ GUESS ONLY: Determine if ticker appears to be US-based (unreliable).
    
    ⚠️ WARNING: This caused the 12% portfolio inflation bug!
    Use only for debugging and import scripts, never in production.
    
    Args:
        ticker: Ticker symbol to check
        
    Returns:
        True if ticker appears to be US-based (GUESS ONLY)
        
    ⚠️ Use position.currency == 'USD' in production instead!
    """
    return guess_currency_from_ticker_UNSAFE(ticker) == 'USD'


def is_canadian_ticker_GUESS_ONLY(ticker: str) -> bool:
    """
    ⚠️ GUESS ONLY: Determine if ticker appears to be Canadian (unreliable).
    
    ⚠️ WARNING: This is unreliable guessing!
    Use only for debugging and import scripts, never in production.
    
    Args:
        ticker: Ticker symbol to check
        
    Returns:
        True if ticker appears to be Canadian (GUESS ONLY)
        
    ⚠️ Use position.currency == 'CAD' in production instead!
    """
    return guess_currency_from_ticker_UNSAFE(ticker) == 'CAD'


def log_currency_guess_warning(ticker: str, guessed_currency: str) -> None:
    """Log a warning when currency is guessed from ticker."""
    logger.warning(
        f"Currency guessed from ticker {ticker} -> {guessed_currency}. "
        f"This is unreliable! Use position.currency field in production."
    )


# Example usage for import/debug scripts:
if __name__ == "__main__":
    test_tickers = ['VFV', 'XIC', 'AAPL', 'MSFT', 'SHOP.TO', 'RY']
    
    print("⚠️ Currency guessing examples (FOR DEBUGGING ONLY):")
    print("-" * 60)
    
    for ticker in test_tickers:
        guessed = guess_currency_from_ticker_UNSAFE(ticker)
        print(f"{ticker:10s} -> {guessed} (GUESS ONLY)")
        log_currency_guess_warning(ticker, guessed)
    
    print("\n⚠️ WARNING: These are unreliable guesses!")
    print("Production code should use position.currency field instead.")