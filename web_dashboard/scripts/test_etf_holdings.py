
import yfinance as yf
import logging

def check_holdings(ticker_symbol):
    print(f"--- Checking {ticker_symbol} ---")
    etf = yf.Ticker(ticker_symbol)
    
    # Try different methods to get holdings
    try:
        # Some versions use .holdings, others .get_holdings()
        print("Attempting .funds_data...")
        # yfinance often puts fund data in .funds_data or similar?
        # Check standard info first
        info = etf.info
        print(f"Name: {info.get('longName')}")
        print(f"Top Holdings (info): {info.get('holdings')}") # Usually None
    except Exception as e:
        print(f"Info Error: {e}")

    # Check if there's a holdings attribute directly
    # Note: yfinance has notoriously unstable holdings support
    print("This requires specific yfinance version support.")
    
if __name__ == "__main__":
    check_holdings("IWC") # Microcap
    check_holdings("ARKK") # ARK
