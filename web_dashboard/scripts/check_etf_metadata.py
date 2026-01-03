
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def check_etf_metadata():
    db = PostgresClient()
    
    # Check which ETFs exist in etf_holdings_log
    print("ETFs in etf_holdings_log:")
    etfs_in_log = db.execute_query("SELECT DISTINCT etf_ticker FROM etf_holdings_log ORDER BY etf_ticker")
    for row in etfs_in_log:
        print(f"  - {row['etf_ticker']}")
    
    print("\nETFs in securities table:")
    etfs_in_securities = db.execute_query("""
        SELECT ticker, name 
        FROM securities 
        WHERE ticker IN (SELECT DISTINCT etf_ticker FROM etf_holdings_log)
        ORDER BY ticker
    """)
    
    if etfs_in_securities:
        for row in etfs_in_securities:
            print(f"  - {row['ticker']}: {row['name']}")
    else:
        print("  (none found)")
    
    print("\nMissing ETF metadata:")
    missing = db.execute_query("""
        SELECT DISTINCT etf_ticker 
        FROM etf_holdings_log 
        WHERE etf_ticker NOT IN (SELECT ticker FROM securities)
        ORDER BY etf_ticker
    """)
    
    if missing:
        for row in missing:
            print(f"  - {row['etf_ticker']}")
    else:
        print("  (all ETFs have metadata)")

if __name__ == "__main__":
    check_etf_metadata()
