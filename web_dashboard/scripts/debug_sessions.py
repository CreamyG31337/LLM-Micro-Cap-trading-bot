
import sys
import os
from pathlib import Path

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from postgres_client import PostgresClient

def main():
    pg = PostgresClient()
    
    # Check schema column default (if possible via info schema)
    query_schema = """
        SELECT column_name, column_default, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'sentiment_sessions' 
          AND column_name = 'needs_ai_analysis'
    """
    
    # Check recent sessions data
    query_data = """
        SELECT id, ticker, needs_ai_analysis, created_at 
        FROM sentiment_sessions 
        ORDER BY created_at DESC 
        LIMIT 5
    """
    
    # Check updated metrics
    query_metrics = """
        SELECT count(*) 
        FROM social_metrics
        WHERE analysis_session_id IS NOT NULL
          AND created_at > NOW() - INTERVAL '1 hour'
    """
    
    try:
        print("--- Schema ---")
        schema = pg.execute_query(query_schema)
        for row in schema:
            print(row)
            
        print("\n--- Recent Sessions ---")
        data = pg.execute_query(query_data)
        for row in data:
            print(row)
            
        print("\n--- Updated Metrics ---")
        metrics = pg.execute_query(query_metrics)
        print(metrics)
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
