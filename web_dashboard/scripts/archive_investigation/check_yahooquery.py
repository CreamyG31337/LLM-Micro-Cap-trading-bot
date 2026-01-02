from yahooquery import Ticker
import time

def check_yq(symbol):
    print(f"\n--- Checking YahooQuery for {symbol} ---")
    tk = Ticker(symbol)
    
    print("1. Calendar Events (Next Pay Date?):")
    try:
        cal = tk.calendar_events
        print(cal)
    except Exception as e:
        print(f"Error: {e}")

    print("\n2. Summary Detail (Current div info):")
    try:
        # summary_detail often has 'exDividendDate' and 'dividendRate'
        summary = tk.summary_detail
        if isinstance(summary, dict) and symbol in summary:
            print(f"Ex-Date: {summary[symbol].get('exDividendDate')}")
            print(f"Div Rate: {summary[symbol].get('dividendRate')}")
            print(f"Div Yield: {summary[symbol].get('dividendYield')}")
        else:
            print(summary)
    except Exception as e:
        print(f"Error: {e}")

    print("\n3. Dividend History (Index check):")
    try:
        # history(period='1y', interval='1d') includes divs
        hist = tk.history(period='1y')
        if 'dividends' in hist.columns:
            divs = hist[hist['dividends'] > 0]
            if not divs.empty:
                print(divs['dividends'].tail(3))
            else:
                print("No recent dividends in history.")
        else:
            print("No dividend column in history.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_yq("AAPL")
    check_yq("FTS.TO") # Fortis Inc (Canadian)
