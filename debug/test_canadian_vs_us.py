#!/usr/bin/env python3
"""
Test Canadian vs US prices to understand the currency issue
"""

import yfinance as yf
import logging

# Suppress yfinance logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def test_canadian_vs_us():
    """Test Canadian vs US prices to understand the currency issue."""
    
    print('Testing what Canadian prices should actually be:')
    print('=' * 50)

    # Test SHOP.TO vs SHOP
    print('SHOP (US):')
    shop_us = yf.Ticker('SHOP')
    info_us = shop_us.info
    print(f'  Name: {info_us.get("longName", "Unknown")}')
    print(f'  Price: ${info_us.get("currentPrice", "Unknown")}')

    print('\nSHOP.TO (should be Canadian):')
    shop_ca = yf.Ticker('SHOP.TO')
    info_ca = shop_ca.info
    print(f'  Name: {info_ca.get("longName", "Unknown")}')
    print(f'  Price: ${info_ca.get("currentPrice", "Unknown")}')

    # Check if SHOP.TO is actually returning Canadian prices
    print('\nChecking if SHOP.TO is actually Canadian:')
    print(f'  Currency: {info_ca.get("currency", "Unknown")}')
    print(f'  Exchange: {info_ca.get("exchange", "Unknown")}')
    
    print('\n' + '=' * 50)
    print('Testing RY vs RY.TO:')
    print('=' * 50)
    
    print('RY (US):')
    ry_us = yf.Ticker('RY')
    info_us = ry_us.info
    print(f'  Name: {info_us.get("longName", "Unknown")}')
    print(f'  Price: ${info_us.get("currentPrice", "Unknown")}')

    print('\nRY.TO (should be Canadian):')
    ry_ca = yf.Ticker('RY.TO')
    info_ca = ry_ca.info
    print(f'  Name: {info_ca.get("longName", "Unknown")}')
    print(f'  Price: ${info_ca.get("currentPrice", "Unknown")}')
    print(f'  Currency: {info_ca.get("currency", "Unknown")}')
    print(f'  Exchange: {info_ca.get("exchange", "Unknown")}')

if __name__ == "__main__":
    test_canadian_vs_us()
