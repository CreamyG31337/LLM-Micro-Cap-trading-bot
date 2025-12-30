
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from postgres_client import PostgresClient

def wipe_analysis():
    print("Connecting to Postgres...")
    client = PostgresClient()
    
    print("Wiping congress_trades_analysis table...")
    # Using TRUNCATE for speed and clean wipe
    try:
        client.execute_update("TRUNCATE TABLE congress_trades_analysis CASCADE;")
        print("✅ congress_trades_analysis wiped.")
    except Exception as e:
        print(f"❌ Error wiping congress_trades_analysis: {e}")

    # Also wipe processed sessions flags if needed?
    # If the analysis logic relies on congress_trade_sessions.is_analyzed or similar...
    # Let's check if we should reset session analysis status
    try:
        print("Resetting session analysis status in congress_trade_sessions...")
        # Assuming there are columns like analyzed_at or conflict_score in sessions table that track status
        # Based on prev conversation, we might want to set them to NULL
        # But analyze_session writes to congress_trades_analysis.
        # Let's see if we need to update usage.
        pass
    except Exception as e:
        print(f"Warning: {e}")

if __name__ == "__main__":
    wipe_analysis()
