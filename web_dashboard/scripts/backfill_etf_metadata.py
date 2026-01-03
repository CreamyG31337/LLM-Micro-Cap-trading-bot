#!/usr/bin/env python3
"""
Backfill ETF metadata into securities table
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

# ETF Names
ETF_NAMES = {
    "ARKK": "ARK Innovation ETF",
    "ARKQ": "ARK Autonomous Technology & Robotics ETF",
    "ARKW": "ARK Next Generation Internet ETF",
    "ARKG": "ARK Genomic Revolution ETF",
    "ARKF": "ARK Fintech Innovation ETF",
    "ARKX": "ARK Space Exploration & Innovation ETF",
    "IZRL": "ARK Israel Innovative Technology ETF",
    "PRNT": "The 3D Printing ETF",
    "ARKSX": "ARK Venture Fund",
    "ARKVX": "ARK Venture Fund",
    "ARKUX": "ARK Venture Fund",
    "IVV": "iShares Core S&P 500 ETF",
    "IWM": "iShares Russell 2000 ETF",
    "IWC": "iShares Micro-Cap ETF",
    "IWO": "iShares Russell 2000 Growth ETF",
    "ARKB": "ARK 21Shares Bitcoin ETF",
    "ARKD": "ARK Transparency ETF",
    "ARKT": "ARK Venture Fund",
}

def backfill_etf_metadata():
    db = PostgresClient()
    
    # Get ETFs that exist in holdings log
    etfs_in_log = db.execute_query("SELECT DISTINCT etf_ticker FROM etf_holdings_log ORDER BY etf_ticker")
    
    if not etfs_in_log:
        print("No ETFs found in etf_holdings_log")
        return
    
    print(f"Found {len(etfs_in_log)} ETFs to backfill\n")
    
    upsert_query = """
        INSERT INTO securities (ticker, name, asset_class, first_detected_by, last_updated)
        VALUES (%s, %s, %s, %s, NOW())
        ON CONFLICT (ticker) DO UPDATE SET
            name = EXCLUDED.name,
            asset_class = COALESCE(EXCLUDED.asset_class, securities.asset_class),
            last_updated = NOW()
    """
    
    for row in etfs_in_log:
        etf_ticker = row['etf_ticker']
        etf_name = ETF_NAMES.get(etf_ticker, etf_ticker)
        
        try:
            db.execute_update(upsert_query, (etf_ticker, etf_name, 'ETF', 'ETF Watchtower Backfill'))
            print(f"✅ {etf_ticker}: {etf_name}")
        except Exception as e:
            print(f"❌ {etf_ticker}: Error - {e}")
    
    print("\n✅ Backfill complete!")

if __name__ == "__main__":
    backfill_etf_metadata()
