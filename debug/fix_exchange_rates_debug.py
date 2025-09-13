#!/usr/bin/env python3
"""
Debug script to fix exchange rates CSV file.

This script will:
1. Fetch current USD/CAD exchange rate from API
2. Add missing entries for yesterday and today
3. Update the exchange_rates.csv file with proper timezone formatting
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import requests
import pandas as pd

# Add parent directory to path to import project modules
sys.path.append(str(Path(__file__).parent.parent))

from utils.timezone_utils import get_trading_timezone, format_timestamp_for_csv

def get_current_exchange_rate() -> float:
    """Fetch current USD/CAD exchange rate from API."""
    try:
        print("Fetching current USD/CAD exchange rate...")
        response = requests.get('https://api.exchangerate-api.com/v4/latest/USD', timeout=10)
        response.raise_for_status()
        data = response.json()
        rate = data['rates']['CAD']
        print(f"✅ Current USD/CAD rate: {rate}")
        return rate
    except Exception as e:
        print(f"❌ Error fetching live rate: {e}")
        print("Using fallback rate: 1.38")
        return 1.38

def load_exchange_rates_csv(file_path: Path) -> pd.DataFrame:
    """Load existing exchange rates CSV file."""
    if not file_path.exists():
        print(f"📄 Creating new exchange rates file: {file_path}")
        return pd.DataFrame(columns=['Date', 'USD_CAD_Rate'])
    
    try:
        df = pd.read_csv(file_path)
        print(f"📄 Loaded existing exchange rates file with {len(df)} entries")
        return df
    except Exception as e:
        print(f"❌ Error loading CSV file: {e}")
        return pd.DataFrame(columns=['Date', 'USD_CAD_Rate'])

def add_missing_dates(df: pd.DataFrame, current_rate: float) -> pd.DataFrame:
    """Add missing dates to the exchange rates CSV."""
    import pytz
    trading_tz = pytz.timezone('America/Los_Angeles')
    now = datetime.now(trading_tz)
    
    # Get the last date in the CSV
    if not df.empty and 'Date' in df.columns:
        # Parse existing dates - handle timezone abbreviations
        df_copy = df.copy()
        df_copy['Date'] = df_copy['Date'].astype(str)
        # Extract just the date part for comparison
        df_copy['Date_Only'] = df_copy['Date'].str.split(' ').str[0]
        last_date_str = df_copy['Date_Only'].max()
        if last_date_str and last_date_str != 'nan':
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d').date()
        else:
            last_date = now.date() - timedelta(days=3)  # Default to 3 days ago
    else:
        last_date = now.date() - timedelta(days=3)  # Default to 3 days ago
    
    print(f"📅 Last entry in CSV: {last_date}")
    print(f"📅 Current date: {now.date()}")
    
    # Add missing dates
    missing_dates = []
    current_date = last_date + timedelta(days=1)
    
    while current_date <= now.date():
        # Create timestamp for 6:30 AM PDT (market open time)
        timestamp = trading_tz.localize(
            datetime.combine(current_date, datetime.min.time().replace(hour=6, minute=30))
        )
        
        missing_dates.append({
            'Date': format_timestamp_for_csv(timestamp),
            'USD_CAD_Rate': f'{current_rate:.4f}'  # Format to 4 decimal places like existing entries
        })
        
        print(f"➕ Adding entry for {current_date}: {current_rate}")
        current_date += timedelta(days=1)
    
    if missing_dates:
        new_df = pd.DataFrame(missing_dates)
        df = pd.concat([df, new_df], ignore_index=True)
        print(f"✅ Added {len(missing_dates)} missing entries")
    else:
        print("✅ No missing dates to add")
    
    return df

def save_exchange_rates_csv(df: pd.DataFrame, file_path: Path) -> None:
    """Save the updated exchange rates CSV file."""
    try:
        # Ensure proper column order
        df = df[['Date', 'USD_CAD_Rate']]
        
        # Remove any duplicate dates (keep the last one)
        df = df.drop_duplicates(subset=['Date'], keep='last')
        
        # Sort by date
        df = df.sort_values('Date')
        
        # Save to CSV
        df.to_csv(file_path, index=False)
        print(f"💾 Saved updated exchange rates to: {file_path}")
        print(f"📊 Total entries: {len(df)}")
        
        # Show last few entries
        if len(df) > 0:
            print("\n📋 Last 5 entries:")
            print(df.tail().to_string(index=False))
            
    except Exception as e:
        print(f"❌ Error saving CSV file: {e}")
        raise

def main():
    """Main function to fix exchange rates CSV."""
    print("🔧 Exchange Rates CSV Fix Script")
    print("=" * 50)
    
    # Determine data directory
    data_dir = Path("my trading")
    if not data_dir.exists():
        data_dir = Path("test_data")
        print(f"⚠️  Using test data directory: {data_dir}")
    
    exchange_rates_file = data_dir / "exchange_rates.csv"
    print(f"📁 Exchange rates file: {exchange_rates_file}")
    
    try:
        # Step 1: Get current exchange rate
        current_rate = get_current_exchange_rate()
        
        # Step 2: Load existing CSV
        df = load_exchange_rates_csv(exchange_rates_file)
        
        # Step 3: Add missing dates
        df = add_missing_dates(df, current_rate)
        
        # Step 4: Save updated CSV
        save_exchange_rates_csv(df, exchange_rates_file)
        
        print("\n✅ Exchange rates CSV fix completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
