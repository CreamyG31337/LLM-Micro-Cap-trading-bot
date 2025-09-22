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

def get_historical_exchange_rate(date_str: str) -> float:
    """Fetch historical USD/CAD exchange rate for a specific date."""
    try:
        print(f"Fetching historical USD/CAD rate for {date_str}...")
        # Use Bank of Canada API for historical rates
        url = f"https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date={date_str}&end_date={date_str}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if 'observations' in data and data['observations']:
            latest = data['observations'][-1]
            if 'FXUSDCAD' in latest and 'v' in latest['FXUSDCAD']:
                rate = float(latest['FXUSDCAD']['v'])
                print(f"✅ Historical USD/CAD rate for {date_str}: {rate}")
                return rate
        else:
            print(f"⚠️  No data found for {date_str}, trying exchangerate-api.com...")
    except Exception as e:
        print(f"❌ Bank of Canada API failed for {date_str}: {e}")

    # Fallback to exchangerate-api.com (may not have historical data)
    try:
        response = requests.get('https://api.exchangerate-api.com/v4/history/USD/2025/01/01', timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'rates' in data and date_str in data['rates']:
            rate = data['rates'][date_str]['CAD']
            print(f"✅ exchangerate-api.com rate for {date_str}: {rate}")
            return rate
    except Exception as e:
        print(f"❌ exchangerate-api.com failed for {date_str}: {e}")

    print(f"❌ Could not fetch rate for {date_str}, using fallback: 1.38")
    return 1.38

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

def backfill_historical_rates(df: pd.DataFrame, start_date: str, end_date: str) -> pd.DataFrame:
    """Backfill historical exchange rates for a date range."""
    from datetime import datetime, timedelta
    import pytz

    trading_tz = pytz.timezone('America/Los_Angeles')

    # Parse start and end dates
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    print(f"📅 Backfilling rates from {start} to {end}")

    # Get existing dates to avoid duplicates
    existing_dates = set()
    if not df.empty and 'Date' in df.columns:
        df_copy = df.copy()
        df_copy['Date_Only'] = df_copy['Date'].str.split(' ').str[0]
        existing_dates = set(df_copy['Date_Only'].values)

    new_entries = []
    current_date = start

    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')

        # Skip if we already have this date
        if date_str in existing_dates:
            print(f"⏭️  Skipping {date_str} (already exists)")
            current_date += timedelta(days=1)
            continue

        # Fetch historical rate for this date
        rate = get_historical_exchange_rate(date_str)
        if rate is None:
            print(f"⚠️  Could not fetch rate for {date_str}, skipping")
            current_date += timedelta(days=1)
            continue

        # Create timestamp for 6:30 AM PDT
        timestamp = trading_tz.localize(
            datetime.combine(current_date, datetime.min.time().replace(hour=6, minute=30))
        )

        new_entries.append({
            'Date': format_timestamp_for_csv(timestamp),
            'USD_CAD_Rate': f'{rate:.4f}'
        })

        print(f"➕ Added entry for {date_str}: {rate}")
        current_date += timedelta(days=1)

    if new_entries:
        new_df = pd.DataFrame(new_entries)
        df = pd.concat([df, new_df], ignore_index=True)
        print(f"✅ Added {len(new_entries)} historical entries")
    else:
        print("✅ No new entries to add")

    return df

def main():
    """Main function to fix exchange rates CSV."""
    print("🔧 Exchange Rates CSV Historical Backfill Script")
    print("=" * 50)

    # Determine data directory - use TEST directory for now
    data_dir = Path("trading_data/funds/TEST")
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return 1

    exchange_rates_file = data_dir / "exchange_rates.csv"
    print(f"📁 Exchange rates file: {exchange_rates_file}")

    try:
        # Step 1: Load existing CSV
        df = load_exchange_rates_csv(exchange_rates_file)

        # Step 2: Backfill historical rates for August 25 to September 19, 2025
        df = backfill_historical_rates(df, '2025-08-25', '2025-09-19')

        # Step 3: Add current rate if needed
        current_rate = get_current_exchange_rate()
        df = add_missing_dates(df, current_rate)

        # Step 4: Save updated CSV
        save_exchange_rates_csv(df, exchange_rates_file)

        print("\n✅ Exchange rates CSV historical backfill completed successfully!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
