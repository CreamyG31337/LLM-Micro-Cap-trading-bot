
import sys
from pathlib import Path

# Add web_dashboard to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient

def remove_feed():
    try:
        db = PostgresClient()
        db.execute_update("DELETE FROM rss_feeds WHERE name = 'Fortune Finance'")
        print("✅ Removed Fortune Finance feed")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    remove_feed()
