
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient
from datetime import date

def test_query():
    db = PostgresClient()
    
    # Test the current query for ARKK
    query = """
        SELECT 
            t.date as date,
            t.etf_ticker,
            t.holding_ticker,
            t.holding_name,
            t.shares_held as current_shares,
            t.weight_percent,
            COALESCE(SUM(p.quantity), 0) as user_shares
        FROM etf_holdings_log t
        LEFT JOIN portfolio_positions p 
            ON t.holding_ticker = p.ticker 
            AND p.date = (SELECT MAX(date) FROM portfolio_positions)
        WHERE t.date = %s
          AND t.etf_ticker = %s
          AND COALESCE(t.shares_held, 0) > 0
        GROUP BY t.date, t.etf_ticker, t.holding_ticker, t.holding_name, t.shares_held, t.weight_percent
        ORDER BY t.weight_percent DESC NULLS LAST, t.shares_held DESC
    """
    
    result = db.execute_query(query, (date(2026, 1, 3), 'ARKK'))
    
    print(f"Query returned {len(result) if result else 0} rows")
    
    if result:
        print("\nFirst 5 rows:")
        for row in result[:5]:
            print(f"  {row['holding_ticker']}: {row['current_shares']} shares, user: {row['user_shares']}")
    else:
        print("No results!")
        
        # Try without the JOIN
        simple_query = """
            SELECT COUNT(*) as cnt
            FROM etf_holdings_log t
            WHERE t.date = %s
              AND t.etf_ticker = %s
              AND COALESCE(t.shares_held, 0) > 0
        """
        simple_result = db.execute_query(simple_query, (date(2026, 1, 3), 'ARKK'))
        print(f"\nSimple query (no JOIN) returned: {simple_result[0]['cnt']} rows")

if __name__ == "__main__":
    test_query()
