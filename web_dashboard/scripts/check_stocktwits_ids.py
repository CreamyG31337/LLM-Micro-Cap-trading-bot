
import sys
import os
import logging
from pathlib import Path

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from postgres_client import PostgresClient

def main():
    pg = PostgresClient()
    
    # Check for StockTwits metrics with 'id' in raw_data created in last hour
    query = """
        SELECT count(*) 
        FROM social_metrics 
        WHERE platform = 'stocktwits' 
          AND raw_data::text LIKE '%"id":%' 
          AND created_at > NOW() - INTERVAL '1 hour'
    """
    
    try:
        results = pg.execute_query(query)
        count = results[0]['count']
        print(f"Found {count} StockTwits metrics with captured IDs from the last hour.")
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
