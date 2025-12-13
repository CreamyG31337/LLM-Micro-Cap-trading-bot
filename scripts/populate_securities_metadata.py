#!/usr/bin/env python3
"""
Populate Securities Metadata
=============================

Fetches sector, industry, and company metadata from yfinance for all tickers
in the securities table and updates the database.

Usage:
    python scripts/populate_securities_metadata.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Supabase client
try:
    from web_dashboard.supabase_client import SupabaseClient
except ImportError:
    logger.error("Could not import SupabaseClient. Make sure you're running from the project root.")
    sys.exit(1)


def fetch_ticker_metadata(ticker: str) -> dict:
    """Fetch metadata for a single ticker from yfinance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        return {
            'company_name': info.get('longName') or info.get('shortName', 'N/A'),
            'sector': info.get('sector', None),
            'industry': info.get('industry', None),
            'country': info.get('country', None),
            'market_cap': info.get('marketCap', None),
            'last_updated': datetime.now().isoformat()
        }
    except Exception as e:
        logger.warning(f"Failed to fetch data for {ticker}: {e}")
        return None


def populate_securities_metadata():
    """Main function to populate securities metadata"""
    logger.info("Starting securities metadata population...")
    
    # Initialize Supabase client
    client = SupabaseClient()
    
    # Fetch all tickers from securities table
    logger.info("Fetching tickers from securities table...")
    response = client.supabase.table('securities').select('ticker').execute()
    
    if not response.data:
        logger.error("No tickers found in securities table")
        return
    
    tickers = [row['ticker'] for row in response.data]
    logger.info(f"Found {len(tickers)} tickers to process")
    
    # Process each ticker
    success_count = 0
    error_count = 0
    
    for idx, ticker in enumerate(tickers, 1):
        logger.info(f"[{idx}/{len(tickers)}] Processing {ticker}...")
        
        metadata = fetch_ticker_metadata(ticker)
        
        if metadata:
            try:
                # Update securities table
                client.supabase.table('securities').update(metadata).eq('ticker', ticker).execute()
                success_count += 1
                logger.info(f"  ✓ Updated {ticker} - {metadata['company_name']}")
            except Exception as e:
                logger.error(f"  ✗ Failed to update {ticker}: {e}")
                error_count += 1
        else:
            error_count += 1
    
    # Summary
    logger.info("\n" + "="*50)
    logger.info("SUMMARY")
    logger.info("="*50)
    logger.info(f"Total tickers: {len(tickers)}")
    logger.info(f"Successfully updated: {success_count}")
    logger.info(f"Errors: {error_count}")
    logger.info("="*50)


if __name__ == "__main__":
    populate_securities_metadata()
