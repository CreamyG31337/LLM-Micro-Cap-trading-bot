
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def check_etf_data():
    db = PostgresClient()
    
    # Check all ETFs
    query = """
    SELECT etf_ticker, COUNT(*) as holdings_count, MAX(date) as latest_date
    FROM etf_holdings_log
    WHERE date = '2026-01-03'
    GROUP BY etf_ticker
    ORDER BY etf_ticker
    """
    
    results = db.execute_query(query)
    
    print("ETF data for 2026-01-03:")
    print("\nARK ETFs:")
    for row in results:
        if row['etf_ticker'].startswith('ARK'):
            print(f"  {row['etf_ticker']}: {row['holdings_count']} holdings")
    
    print("\niShares ETFs:")
    for row in results:
        if row['etf_ticker'].startswith('I'):
            print(f"  {row['etf_ticker']}: {row['holdings_count']} holdings")
    
    # Sample a few holdings from ARKK to see the data
    print("\nSample ARKK holdings:")
    sample_query = """
    SELECT holding_ticker, holding_name, shares_held, weight_percent
    FROM etf_holdings_log
    WHERE etf_ticker = 'ARKK' AND date = '2026-01-03'
    ORDER BY shares_held DESC NULLS LAST
    LIMIT 5
    """
    
    sample = db.execute_query(sample_query)
    for row in sample:
        print(f"  {row['holding_ticker']}: {row['shares_held']} shares, {row['weight_percent']}%")

if __name__ == "__main__":
    check_etf_data()
