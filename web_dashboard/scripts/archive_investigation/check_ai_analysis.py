import sys
sys.path.insert(0, 'web_dashboard')
from supabase_client import SupabaseClient

client = SupabaseClient(use_service_role=True)

# Check for conflict_score in production
result = client.supabase.table('congress_trades')\
    .select('id,politician,ticker,transaction_date,conflict_score,notes')\
    .not_.is_('conflict_score', 'null')\
    .limit(10)\
    .execute()

print(f"Trades with conflict_score in Supabase: {len(result.data)}")

if result.data:
    print("\nSample analyzed trades:")
    for t in result.data[:5]:
        score = t.get('conflict_score', 'NULL')
        notes_preview = (t.get('notes', '')[:50] + '...') if t.get('notes') else 'NULL'
        print(f"  {t['politician']:25s} | {t['ticker']:6s} | Score: {score} | Notes: {notes_preview}")
