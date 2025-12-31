
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
    
    # Check for social_posts with valid URLs created in last hour
    query = """
        SELECT count(*) 
        FROM social_posts 
        WHERE url IS NOT NULL 
          AND posted_at > NOW() - INTERVAL '4 hours'
    """
    
    try:
        results = pg.execute_query(query)
        count = results[0]['count']
        print(f"Found {count} social posts with URLs from recent data.")
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
