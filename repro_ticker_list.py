
import sys
import os
from pathlib import Path

# Add web_dashboard to path to allow imports
sys.path.append(os.path.abspath("web_dashboard"))

from web_dashboard.ticker_utils import get_all_unique_tickers
from web_dashboard.supabase_client import SupabaseClient
from web_dashboard.postgres_client import PostgresClient

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tickers():
    print("Testing get_all_unique_tickers() ...")
    try:
        # Test 1: With explicit clients
        print("1. Testing with explicit clients:")
        sb = SupabaseClient(use_service_role=True)
        pg = PostgresClient()
        tickers = get_all_unique_tickers(sb, pg)
        print(f"Found {len(tickers)} tickers explicitly")
        if 'ROBO' in tickers:
            print("  ROBO found in explicit list")
        else:
            print("  ROBO NOT found in explicit list")
            
        # Test 2: Implicit clients (as called in app.py)
        print("\n2. Testing with implicit clients (like app.py):")
        tickers_implicit = get_all_unique_tickers()
        print(f"Found {len(tickers_implicit)} tickers implicitly")
        if 'ROBO' in tickers_implicit:
            print("  ROBO found in implicit list")
        else:
            print("  ROBO NOT found in implicit list")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tickers()
