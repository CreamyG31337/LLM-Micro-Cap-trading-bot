
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def inspect_securities():
    db = PostgresClient()
    query = "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'securities' ORDER BY ordinal_position"
    results = db.execute_query(query)
    print("Columns for 'securities':")
    for row in results:
        print(f"- {row['column_name']} ({row['data_type']})")

if __name__ == "__main__":
    inspect_securities()
