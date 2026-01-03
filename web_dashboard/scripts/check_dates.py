
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def check_available_dates():
    db = PostgresClient()
    
    # Check what dates we have data for
    query = """
    SELECT DISTINCT date, COUNT(*) as holdings_count
    FROM etf_holdings_log
    GROUP BY date
    ORDER BY date DESC
    LIMIT 10
    """
    
    results = db.execute_query(query)
    
    print("Available dates in etf_holdings_log:")
    for row in results:
        print(f"  {row['date']}: {row['holdings_count']} holdings")
    
    # Check for ARKK specifically
    print("\nARKK data availability:")
    arkk_query = """
    SELECT date, COUNT(*) as holdings_count
    FROM etf_holdings_log
    WHERE etf_ticker = 'ARKK'
    GROUP BY date
    ORDER BY date DESC
    LIMIT 5
    """
    
    arkk_results = db.execute_query(arkk_query)
    for row in arkk_results:
        print(f"  {row['date']}: {row['holdings_count']} holdings")

if __name__ == "__main__":
    check_available_dates()
