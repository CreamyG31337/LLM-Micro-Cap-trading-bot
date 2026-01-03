
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def list_tables():
    db = PostgresClient()
    query = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    results = db.execute_query(query)
    print("Tables found:")
    for row in results:
        print(f"- {row['table_name']}")

if __name__ == "__main__":
    list_tables()
