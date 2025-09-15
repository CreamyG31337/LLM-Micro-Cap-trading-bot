import pandas as pd
import yfinance as yf
from datetime import datetime

# Test the S&P 500 download and normalization
print("🔍 Debugging S&P 500 Baseline Issue")
print("=" * 50)

# Our portfolio dates
start_date = pd.Timestamp("2025-09-08")
end_date = pd.Timestamp("2025-09-14")

print(f"Portfolio date range: {start_date.date()} to {end_date.date()}")

# Download S&P 500 data like the script does
download_start = start_date - pd.Timedelta(days=5)
download_end = end_date + pd.Timedelta(days=5)

print(f"S&P 500 download range: {download_start.date()} to {download_end.date()}")

try:
    sp500 = yf.download("^GSPC", start=download_start, end=download_end, progress=False, auto_adjust=False)
    sp500 = sp500.reset_index()
    
    print(f"\n📈 Downloaded {len(sp500)} S&P 500 data points:")
    print(sp500[['Date', 'Close']].head(10))
    
    # Check the first close price (what we use as baseline)
    first_close = sp500["Close"].iloc[0]
    print(f"\n🎯 First close price (baseline): ${first_close:.2f}")
    
    # Calculate scaling factor
    scaling_factor = 100.0 / first_close
    print(f"📐 Scaling factor: {scaling_factor:.6f}")
    
    # Apply scaling
    sp500["SPX Value ($100 Invested)"] = sp500["Close"] * scaling_factor
    
    print(f"\n📊 Normalized S&P 500 values:")
    print(sp500[['Date', 'Close', 'SPX Value ($100 Invested)']].head(10))
    
    # Check what value corresponds to Sep 8th
    sp500['Date_Only'] = pd.to_datetime(sp500['Date']).dt.date
    portfolio_start_date = start_date.date()
    
    sep8_data = sp500[sp500['Date_Only'] == portfolio_start_date]
    if len(sep8_data) > 0:
        sep8_value = sep8_data['SPX Value ($100 Invested)'].iloc[0]
        print(f"\n🎯 S&P 500 value on Sep 8: {sep8_value:.2f}")
        print(f"❌ Problem: This should be 100.00, not {sep8_value:.2f}")
    else:
        print(f"\n⚠️ No S&P 500 data for Sep 8 (weekend?)")
        
        # Show what dates we have around Sep 8
        print("\nAvailable dates around Sep 8:")
        relevant_dates = sp500[sp500['Date_Only'].isin([
            pd.to_datetime("2025-09-06").date(),
            pd.to_datetime("2025-09-07").date(), 
            pd.to_datetime("2025-09-08").date(),
            pd.to_datetime("2025-09-09").date(),
            pd.to_datetime("2025-09-10").date()
        ])]
        print(relevant_dates[['Date_Only', 'SPX Value ($100 Invested)']])

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 50)
print("🎯 SOLUTION: We need to normalize S&P 500 to 100 on Sep 8th")
print("Not on the first available trading day in the download range!")