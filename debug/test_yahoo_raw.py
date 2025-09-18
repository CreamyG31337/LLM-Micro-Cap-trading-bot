#!/usr/bin/env python3
"""
Test raw Yahoo Finance calls to see what data we're getting
"""

import yfinance as yf
import logging

# Suppress yfinance logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

def test_yahoo_raw():
    """Test raw Yahoo Finance calls to see what data we're getting."""
    
    print('Testing raw Yahoo Finance calls:')
    print('=' * 50)

    # Test SHOP vs SHOP.TO
    print('SHOP (US):')
    shop_us = yf.Ticker('SHOP')
    info_us = shop_us.info
    print(f'  Name: {info_us.get("longName", "Unknown")}')
    print(f'  Price: ${info_us.get("currentPrice", "Unknown")}')

    print('\nSHOP.TO (Canadian):')
    shop_ca = yf.Ticker('SHOP.TO')
    info_ca = shop_ca.info
    print(f'  Name: {info_ca.get("longName", "Unknown")}')
    print(f'  Price: ${info_ca.get("currentPrice", "Unknown")}')

    print('\n' + '=' * 50)
    print('Testing RY vs RY.TO:')
    print('=' * 50)

    print('RY (US):')
    ry_us = yf.Ticker('RY')
    info_us = ry_us.info
    print(f'  Name: {info_us.get("longName", "Unknown")}')
    print(f'  Price: ${info_us.get("currentPrice", "Unknown")}')

    print('\nRY.TO (Canadian):')
    ry_ca = yf.Ticker('RY.TO')
    info_ca = ry_ca.info
    print(f'  Name: {info_ca.get("longName", "Unknown")}')
    print(f'  Price: ${info_ca.get("currentPrice", "Unknown")}')

if __name__ == "__main__":
    test_yahoo_raw()
