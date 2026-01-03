
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient
import pandas as pd

def investigate_zero_shares():
    db = PostgresClient()
    
    # Query for holdings with 0 shares in the latest snapshot for each ETF
    query = """
    WITH latest_dates AS (
        SELECT etf_ticker, MAX(date) as max_date
        FROM etf_holdings_log
        GROUP BY etf_ticker
    )
    SELECT 
        t.etf_ticker,
        t.holding_ticker,
        t.holding_name,
        t.shares_held,
        t.weight_percent,
        t.market_value
    FROM etf_holdings_log t
    JOIN latest_dates ld ON t.etf_ticker = ld.etf_ticker AND t.date = ld.max_date
    WHERE t.shares_held = 0 OR t.shares_held IS NULL
    ORDER BY t.etf_ticker, t.weight_percent DESC;
    """
    
    results = db.execute_query(query)
    
    if not results:
        print("No 0-share holdings found in latest snapshots.")
        return

    print(f"Found {len(results)} holdings with 0 shares:\n")
    
    df = pd.DataFrame(results)
    
    # Group by ETF to see what's what
    for etf, group in df.groupby('etf_ticker'):
        print(f"--- {etf} ({len(group)} items) ---")
        print(group[['holding_ticker', 'holding_name', 'shares_held', 'weight_percent']].head(20).to_string(index=False))
        if len(group) > 20:
            print(f"... and {len(group)-20} more ...")
        print("\n")

if __name__ == "__main__":
    investigate_zero_shares()
