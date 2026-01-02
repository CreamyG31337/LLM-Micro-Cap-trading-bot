"""
Test script for dividend processing job (3-Layer Strategy).
"""

import sys
import logging
from pathlib import Path
from decimal import Decimal

# Configure logging
logging.basicConfig(level=logging.INFO)

# Add project root to path
current_dir = Path(__file__).resolve().parent
if current_dir.name == 'scheduler':
    project_root = current_dir.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

web_dashboard_path = str(Path(__file__).resolve().parent.parent)
if web_dashboard_path not in sys.path:
    sys.path.insert(0, web_dashboard_path)

from scheduler.jobs_dividends import (
    fetch_dividends_nasdaq,
    fetch_dividends_yahooquery,
    fetch_dividends_yfinance,
    fetch_dividend_data,
    calculate_withholding_tax
)

def test_nasdaq_fetching():
    print("\n--- Testing Nasdaq API (Layer 1) ---")
    tickers = ["AAPL", "MSFT"]
    for t in tickers:
        events = fetch_dividends_nasdaq(t)
        if events:
            print(f"✅ {t}: Found {len(events)} events (Top: {events[0]})")
        else:
            print(f"❌ {t}: No events found")

def test_yahooquery_fetching():
    print("\n--- Testing YahooQuery (Layer 2) ---")
    tickers = ["AAPL", "FTS.TO"] 
    for t in tickers:
        events = fetch_dividends_yahooquery(t)
        if events:
            print(f"✅ {t}: Found {len(events)} events (Top: {events[0]})")
        else:
            print(f"⚠️ {t}: No events found (Normal if no upcoming divs)")

def test_yfinance_fetching():
    print("\n--- Testing Yfinance (Layer 3 Fallback) ---")
    tickers = ["AAPL", "FTS.TO"]
    for t in tickers:
        events = fetch_dividends_yfinance(t)
        if events:
            print(f"✅ {t}: Found {len(events)} events (Top: {events[0]})")
        else:
            print(f"❌ {t}: No events found")

def test_tax_calc():
    print("\n--- Testing Tax Calculation ---")
    # US Stock in TFSA = 15%
    tax = calculate_withholding_tax(Decimal('100'), 'tfsa', 'AAPL')
    assert tax == Decimal('15'), f"Expected 15, got {tax}"
    print("✅ US/TFSA: 15% tax correct")
    
    # Canadian Stock = 0%
    tax = calculate_withholding_tax(Decimal('100'), 'tfsa', 'FTS.TO')
    assert tax == Decimal('0'), f"Expected 0, got {tax}"
    print("✅ Canadian: 0% tax correct")

if __name__ == "__main__":
    test_nasdaq_fetching()
    test_yahooquery_fetching()
    test_yfinance_fetching()
    test_tax_calc()
    print("\n✅ All Tests Completed")

