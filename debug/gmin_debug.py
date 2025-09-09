#!/usr/bin/env python3
"""
Quick debug for GMIN.TO
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def debug_gmin():
    print("🔍 Debugging GMIN.TO price data")
    print("=" * 50)
    
    try:
        stock = yf.Ticker("GMIN.TO")
        
        # Get last 3 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)
        
        hist = stock.history(start=start_date, end=end_date)
        
        if not hist.empty:
            print("📊 Recent GMIN.TO Data:")
            for date, row in hist.tail(3).iterrows():
                print(f"📅 {date.strftime('%Y-%m-%d')}")
                print(f"   Open:  ${row['Open']:.2f}")
                print(f"   High:  ${row['High']:.2f}")
                print(f"   Low:   ${row['Low']:.2f}")
                print(f"   Close: ${row['Close']:.2f}")
                print()
        
        # Get current info
        info = stock.info
        print("📈 Current Info:")
        print(f"Previous Close: ${info.get('previousClose', 'N/A')}")
        print(f"Open: ${info.get('open', 'N/A')}")
        print(f"Current Price: ${info.get('currentPrice', 'N/A')}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    debug_gmin()
