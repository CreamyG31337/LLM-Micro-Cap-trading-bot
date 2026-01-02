"""
Targeted test for URNJ dividend.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

# Setup paths
web_dashboard_path = str(Path(__file__).resolve().parent / "web_dashboard")
if web_dashboard_path not in sys.path:
    # Append to look elsewhere if needed, but we used insert(0) before.
    # Let's stick to the pattern we know works for imports, 
    # but respecting the import order fix I made in jobs_dividends (Root then WebDashboard)
    pass

# We need root path for utils
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if web_dashboard_path not in sys.path:
    sys.path.insert(0, web_dashboard_path)


from scheduler.jobs_dividends import fetch_dividend_data, fetch_dividends_nasdaq, fetch_dividends_yahooquery, fetch_dividends_yfinance

ticker = "URNJ"
print(f"🔍 Inspecting {ticker} dividends...")

print("\n--- Layer 1: Nasdaq ---")
try:
    events = fetch_dividends_nasdaq(ticker)
    for e in events:
        print(f"  {e}")
except Exception as e:
    print(f"  Error: {e}")

print("\n--- Layer 2: YahooQuery ---")
try:
    events = fetch_dividends_yahooquery(ticker)
    for e in events:
        print(f"  {e}")
except Exception as e:
    print(f"  Error: {e}")

print("\n--- Layer 3: Yfinance ---")
try:
    events = fetch_dividends_yfinance(ticker)
    # Sort by date desc
    events.sort(key=lambda x: x.ex_date, reverse=True)
    for e in events[:5]: # Show top 5
        print(f"  {e}")
except Exception as e:
    print(f"  Error: {e}")
