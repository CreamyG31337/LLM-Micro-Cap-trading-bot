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
        with open(rates_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                date_str = row.get('Date', '')
                rate_str = row.get('USD_CAD_Rate', '')
                if date_str and rate_str:
                    try:
                        exchange_rates[date_str] = Decimal(rate_str)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Invalid exchange rate data: {date_str}={rate_str}, error: {e}")
    except Exception as e:
        logger.error(f"Failed to load exchange rates: {e}")
    
    return exchange_rates


def get_exchange_rate_for_date(exchange_rates: Dict[str, Decimal],
                              target_date: Optional[datetime] = None) -> Decimal:
    """
    Get the USD to CAD exchange rate for a specific date.

    Args:
        exchange_rates: Dictionary of exchange rates by date
        target_date: Date to get rate for (uses latest if None)

    Returns:
        USD to CAD exchange rate as Decimal (1 USD = X CAD)
    """
    if not exchange_rates:
        logger.warning("No exchange rates available, using default rate 1.35")
        return Decimal('1.35')

    if target_date is None:
        # Use the latest available rate
        latest_date = max(exchange_rates.keys())
        rate = exchange_rates[latest_date]
        # Exchange rates in the CSV are already in USD->CAD format (1 USD = X CAD)
        return rate

    # Find the closest date to target_date
    target_date_str = target_date.strftime('%Y-%m-%d')

    # First try exact match
    if target_date_str in exchange_rates:
        rate = exchange_rates[target_date_str]
        # Exchange rates in the CSV are already in USD->CAD format (1 USD = X CAD)
        return rate

    # Find the closest previous date
    available_dates = sorted(exchange_rates.keys())
    for date_str in reversed(available_dates):
        if date_str <= target_date_str:
            rate = exchange_rates[date_str]
            # Exchange rates in the CSV are already in USD->CAD format (1 USD = X CAD)
            return rate

    # If no previous date found, use the earliest available
    earliest_date = min(exchange_rates.keys())
    rate = exchange_rates[earliest_date]
    # Exchange rates in the CSV are already in USD->CAD format (1 USD = X CAD)
    logger.warning(f"No exchange rate found for {target_date_str}, using {earliest_date} with rate {rate}")
    return rate


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
