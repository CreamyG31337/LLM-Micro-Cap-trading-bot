
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
    
    # Check total pending count
    query_count = """
        SELECT count(*) 
        FROM sentiment_sessions 
        WHERE needs_ai_analysis = TRUE
    """
    
    # Check oldest 5 pending
    query_oldest = """
        SELECT id, ticker, created_at 
        FROM sentiment_sessions 
        WHERE needs_ai_analysis = TRUE 
        ORDER BY created_at ASC 
        LIMIT 5
    """
    
    try:
        count_res = pg.execute_query(query_count)
        print(f"Total pending sessions: {count_res[0]['count']}")
        
        print("\nOldest pending sessions:")
        oldest_res = pg.execute_query(query_oldest)
        for row in oldest_res:
            print(row)
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
