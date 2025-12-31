
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from postgres_client import PostgresClient

def main():
    print("LISTING TRIGGERS ON congress_trades")
    
    # Initialize PostgresClient
    # It attempts to load env vars. We hope RESEARCH_DATABASE_URL matches the Supabase one or the local DB one 
    # where the issue is.
    try:
        pg = PostgresClient()
    except Exception as e:
        print(f"Failed to init PostgresClient: {e}")
        return

    query = """
    SELECT event_object_table AS table_name, trigger_name, action_statement
    FROM information_schema.triggers
    WHERE event_object_table = 'congress_trades';
    """
    
    try:
        triggers = pg.execute_query(query)
        if not triggers:
            print("No triggers found on congress_trades.")
        else:
            print(f"Found {len(triggers)} triggers:")
            for t in triggers:
                print(f"  - {t['trigger_name']} (Action: {t['action_statement'][:50]}...)")
                
    except Exception as e:
        print(f"Query failed: {e}")

if __name__ == "__main__":
    main()
