"""
Currency conversion utility for portfolio calculations.

This module provides functions to convert between USD and CAD using
historical exchange rates from the exchange_rates.csv file.
"""

import csv
import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)


def load_exchange_rates(data_dir: Path) -> Dict[str, Decimal]:
    """
    Load exchange rates from exchange_rates.csv file.
    
    Args:
        data_dir: Directory containing the exchange_rates.csv file
        
    Returns:
        Dictionary mapping date strings to USD_CAD_Rate values
    """
    exchange_rates = {}
    rates_file = data_dir / "exchange_rates.csv"
    
    if not rates_file.exists():
        logger.warning(f"Exchange rates file not found: {rates_file}")
        return exchange_rates
    
    try:
        rates_df = pd.read_csv(rates_file)
    except Exception as e:
        logger.error(f"Failed to load exchange rates: {e}")
        return exchange_rates

    if not rates_df.empty:
        rates_df = rates_df.set_index('Date')
        # Convert index to datetime if it's not already
        if not isinstance(rates_df.index, pd.DatetimeIndex):
            rates_df.index = pd.to_datetime(rates_df.index)
        
        # Create a full date range from the first to the last available date
        full_date_range = pd.date_range(start=rates_df.index.min(), end=rates_df.index.max(), freq='D')
        
        # Reindex the DataFrame to include all dates in the range, then forward-fill missing values
        rates_df = rates_df.reindex(full_date_range).ffill()
        
        # Convert back to dictionary with 'YYYY-MM-DD' format, ensuring values are Decimal
        exchange_rates = {
            date.strftime('%Y-%m-%d'): Decimal(str(rate))
            for date, rate in rates_df['USD_CAD_Rate'].to_dict().items()
        }
        
    return exchange_rates


def get_exchange_rate_for_date(exchange_rates: Dict[str, Decimal],
                              target_date: Optional[datetime] = None) -> Decimal:
    """
    Get the USD to CAD exchange rate for a specific date.
    Finds the most recent rate on or before the target date.

    Args:
        exchange_rates: Dictionary of exchange rates by date.
        target_date: The date for which to get the rate. Uses the latest available if None.

    Returns:
        USD to CAD exchange rate as a Decimal.

    Raises:
        ValueError: If no exchange rate is available on or before the target date.
    """
    if not exchange_rates:
        raise ValueError("Exchange rates data is empty. Cannot determine rate.")

    sorted_dates = sorted(exchange_rates.keys())

    if target_date is None:
        # Use the latest available rate if no date is specified.
        latest_date = sorted_dates[-1]
        return exchange_rates[latest_date]

    target_date_str = target_date.strftime('%Y-%m-%d')

    # Find the most recent rate on or before the target date.
    best_date = None
    for date_str in sorted_dates:
        if date_str <= target_date_str:
            best_date = date_str
        else:
            break  # Stop checking once we pass the target date.

    if best_date:
        return exchange_rates[best_date]
    else:
        # This is the critical failure case: the history doesn't go back far enough.
        earliest_available = sorted_dates[0]
        raise ValueError(
            f"Missing historical exchange rate data. "
            f"Cannot find rate for '{target_date_str}'. "
            f"Earliest available rate is on '{earliest_available}'."
        )


def convert_usd_to_cad(usd_amount: Decimal, 
                      exchange_rates: Dict[str, Decimal], 
                      target_date: Optional[datetime] = None) -> Decimal:
    """
    Convert USD amount to CAD using historical exchange rates.
    
    Args:
        usd_amount: Amount in USD to convert
        exchange_rates: Dictionary of exchange rates by date
        target_date: Date to use for conversion (uses latest if None)
        
    Returns:
        Amount in CAD as Decimal
    """
    if usd_amount == 0:
        return Decimal('0')
    
    rate = get_exchange_rate_for_date(exchange_rates, target_date)
    cad_amount = (usd_amount * rate).quantize(Decimal('0.01'))
    
    logger.debug(f"Converted ${usd_amount} USD to ${cad_amount} CAD (rate: {rate})")
    return cad_amount


def convert_cad_to_usd(cad_amount: Decimal, 
                      exchange_rates: Dict[str, Decimal], 
                      target_date: Optional[datetime] = None) -> Decimal:
    """
    Convert CAD amount to USD using historical exchange rates.
    
    Args:
        cad_amount: Amount in CAD to convert
        exchange_rates: Dictionary of exchange rates by date
        target_date: Date to use for conversion (uses latest if None)
        
    Returns:
        Amount in USD as Decimal
    """
    if cad_amount == 0:
        return Decimal('0')
    
    rate = get_exchange_rate_for_date(exchange_rates, target_date)
    usd_amount = (cad_amount / rate).quantize(Decimal('0.01'))
    
    logger.debug(f"Converted ${cad_amount} CAD to ${usd_amount} USD (rate: {rate})")
    return usd_amount


# REMOVED: is_us_ticker() and is_canadian_ticker() functions from production code.
# These functions caused a 12% portfolio inflation bug by incorrectly classifying tickers.
# 
# For production code: Use pos.currency field from position data instead of guessing.
# For debugging/import scripts: See utils/ticker_currency_guess.py for guessing functions.
