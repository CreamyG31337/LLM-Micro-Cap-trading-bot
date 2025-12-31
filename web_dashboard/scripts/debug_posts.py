
import sys
import os
from pathlib import Path
import json

# Setup path
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent
sys.path.insert(0, str(project_root))

from postgres_client import PostgresClient

def main():
    pg = PostgresClient()
    
    # Get recent social posts
    query = """
        SELECT sp.id, sp.url, sp.platform, sp.posted_at, sp.metric_id
        FROM social_posts sp
        WHERE sp.posted_at > NOW() - INTERVAL '2 hours'
        LIMIT 5
    """
    
    try:
        results = pg.execute_query(query)
        if not results:
            print("No recent social posts found.")
        else:
            for row in results:
                print(f"Post ID: {row['id']}")
                print(f"URL: {row['url']}")
                print(f"Platform: {row['platform']}")
                print(f"Metric ID: {row['metric_id']}")
                print("-" * 20)
                
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
