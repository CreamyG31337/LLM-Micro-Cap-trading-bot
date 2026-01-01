
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
    
    # Check for recent analysis
    query = """
        SELECT count(*) 
        FROM social_sentiment_analysis 
        WHERE analyzed_at > NOW() - INTERVAL '1 hour'
    """
    
    try:
        results = pg.execute_query(query)
        count = results[0]['count']
        print(f"Found {count} new AI analyses from the last hour.")
        
        if count > 0:
            # Show a sample
            sample_query = """
                SELECT ticker, sentiment_label, sentiment_score, model_used 
                FROM social_sentiment_analysis 
                ORDER BY analyzed_at DESC 
                LIMIT 3
            """
            samples = pg.execute_query(sample_query)
            print("Samples:", samples)
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    main()
