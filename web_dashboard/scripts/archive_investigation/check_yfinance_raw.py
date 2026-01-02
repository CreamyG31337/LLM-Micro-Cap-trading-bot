import yfinance as yf
import pandas as pd

def check_ticker(symbol):
    print(f"\n--- Checking {symbol} ---")
    tk = yf.Ticker(symbol)
    
    print("\n1. Dividends (Index is usually Ex-Date):")
    try:
        divs = tk.dividends
        if not divs.empty:
            print(divs.tail(3))
            print(f"Index name: {divs.index.name}")
        else:
            print("No dividends found.")
    except Exception as e:
        print(f"Error getting dividends: {e}")

    print("\n2. Actions (Splits + Dividends):")
    try:
        actions = tk.actions
        if not actions.empty:
            print(actions.tail(3))
        else:
            print("No actions found.")
    except Exception as e:
        print(f"Error getting actions: {e}")

    print("\n3. Calendar:")
    try:
        cal = tk.calendar
        if cal is not None and not cal.empty:
            print(cal)
        else:
            print("No calendar found.")
    except Exception as e:
        print(f"Error getting calendar: {e}")

if __name__ == "__main__":
    check_ticker("AAPL")
    check_ticker("FTS.TO")
