#!/usr/bin/env python3
"""
Clean up duplicate portfolio snapshots from CSV file.

This script removes duplicate portfolio snapshots, keeping only the latest
snapshot for each trading day. It preserves the most recent data for each day
while removing all the duplicates that were created by the bug.
"""

import pandas as pd
import shutil
from pathlib import Path
import sys
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def clean_duplicate_snapshots(csv_file_path: str) -> None:
    """
    Clean up duplicate portfolio snapshots from CSV file.
    
    Args:
        csv_file_path: Path to the CSV file to clean
    """
    csv_path = Path(csv_file_path)
    
    if not csv_path.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    # Create backup
    backup_dir = csv_path.parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{csv_path.stem}.backup_{timestamp}.csv"
    logger.info(f"Creating backup: {backup_path}")
    shutil.copy2(csv_path, backup_path)
    csv_path.unlink()  # Remove original file
    
    try:
        # Load the CSV file
        logger.info(f"Loading CSV file: {csv_path}")
        df = pd.read_csv(backup_path)
        
        logger.info(f"Original data: {len(df)} rows, {df['Date'].nunique()} unique dates")
        
        # Parse dates properly - handle mixed timezone formats
        def parse_date(date_str):
            try:
                # Handle timezone-aware dates
                if ' PST' in str(date_str) or ' PDT' in str(date_str):
                    # Remove timezone suffix and parse as naive datetime
                    clean_date = str(date_str).replace(' PST', '').replace(' PDT', '')
                    return pd.to_datetime(clean_date)
                else:
                    return pd.to_datetime(date_str)
            except:
                return pd.NaT
        
        df['Date'] = df['Date'].apply(parse_date)
        df = df.dropna(subset=['Date'])
        
        # Convert all dates to naive datetime for consistency
        df['Date'] = pd.to_datetime(df['Date'], utc=True).dt.tz_localize(None)
        
        # Convert to date-only for grouping
        df['Date_Only'] = df['Date'].dt.date
        
        # Group by date and keep only the latest snapshot for each day
        logger.info("Removing duplicates by keeping latest snapshot per day...")
        
        # Sort by date to ensure we get the latest timestamp for each day
        df_sorted = df.sort_values('Date')
        
        # Group by date and ticker, keep the last (most recent) entry for each combination
        cleaned_df = df_sorted.groupby(['Date_Only', 'Ticker']).last().reset_index()
        
        # Remove the helper column
        cleaned_df = cleaned_df.drop('Date_Only', axis=1)
        
        # Sort by date and ticker for consistency
        cleaned_df = cleaned_df.sort_values(['Date', 'Ticker']).reset_index(drop=True)
        
        logger.info(f"Cleaned data: {len(cleaned_df)} rows, {cleaned_df['Date'].nunique()} unique dates")
        logger.info(f"Removed {len(df) - len(cleaned_df)} duplicate rows")
        
        # Save the cleaned data
        cleaned_df.to_csv(csv_path, index=False)
        logger.info(f"Saved cleaned data to: {csv_path}")
        
        # Show summary by date
        logger.info("Summary by date:")
        date_counts = cleaned_df.groupby(cleaned_df['Date'].dt.date).size()
        for date, count in date_counts.items():
            logger.info(f"  {date}: {count} positions")
        
    except Exception as e:
        logger.error(f"Error cleaning CSV file: {e}")
        # Restore backup on error
        logger.info("Restoring backup due to error...")
        backup_path.rename(csv_path)
        raise

def main():
    """Main function to clean duplicate snapshots."""
    if len(sys.argv) != 2:
        print("Usage: python clean_duplicate_snapshots.py <csv_file_path>")
        print("Example: python clean_duplicate_snapshots.py trading_data/funds/TEST/llm_portfolio_update.csv")
        sys.exit(1)
    
    csv_file_path = sys.argv[1]
    clean_duplicate_snapshots(csv_file_path)

if __name__ == "__main__":
    main()
