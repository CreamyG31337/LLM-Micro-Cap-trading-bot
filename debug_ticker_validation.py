#!/usr/bin/env python3
"""
Debug script to test ticker validation for NXTG.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from utils.price_ticker_validator import PriceTickerValidator

def test_nxtg_validation():
    """Test NXTG ticker validation."""

    validator = PriceTickerValidator()

    # Test NXTG with the trade price and date
    ticker = "NXTG"
    trade_price = 13.797
    trade_date = "2025-08-25 09:30:06 EDT"
    currency = "USD"  # NXTG is likely USD

    print(f"🔍 Testing NXTG validation:")
    print(f"   Trade price: ${trade_price}")
    print(f"   Trade date: {trade_date}")
    print(f"   Currency: {currency}")

    # Test different variants manually
    variants_to_test = ["NXTG", "NXTG.TO", "NXTG.V"]

    for variant in variants_to_test:
        try:
            import yfinance as yf
            import logging
            logging.getLogger("yfinance").setLevel(logging.CRITICAL)

            stock = yf.Ticker(variant)
            info = stock.info

            if info and info.get('symbol') and info.get('symbol') != 'N/A':
                exchange = info.get('exchange', '')
                name = info.get('longName', info.get('shortName', ''))

                print(f"\n📊 {variant}:")
                print(f"   Symbol: {info.get('symbol')}")
                print(f"   Name: {name}")
                print(f"   Exchange: {exchange}")

                # Get historical price
                hist = stock.history(start="2025-08-25", end="2025-08-26")
                if not hist.empty and 'Close' in hist.columns:
                    hist_price = float(hist['Close'].iloc[0])
                    print(f"   Historical price: ${hist_price:.2f}")
                    price_diff = abs(hist_price - trade_price) / trade_price
                    print(f"   Price difference: {price_diff:.1%}")
                else:
                    print(f"   No historical data available")

        except Exception as e:
            print(f"❌ Error testing {variant}: {e}")

    # Now test the validator
    print(f"\n🔍 Running validator...")
    corrected_ticker, is_valid = validator.validate_ticker_with_price(
        ticker, trade_price, trade_date, currency
    )

    print(f"Validator result: {corrected_ticker} (valid: {is_valid})")

if __name__ == "__main__":
    test_nxtg_validation()
