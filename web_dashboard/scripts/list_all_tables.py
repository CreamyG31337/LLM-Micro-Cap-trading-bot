import sys
sys.path.append('web_dashboard')
from postgres_client import PostgresClient

db = PostgresClient()
tables = db.execute_query("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
print("All tables:")
for t in tables:
    print(f"  {t['table_name']}")
