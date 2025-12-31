
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
    
    query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'social_metrics'
    """
    
    try:
        results = pg.execute_query(query)
        columns = [r['column_name'] for r in results]
        print(f"Columns in social_metrics: {columns}")
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
