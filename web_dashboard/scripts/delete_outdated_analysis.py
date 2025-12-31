
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    # Fix for Windows Unicode output safely
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from supabase_client import SupabaseClient

def main():
    print("="*60)
    print("DELETING OUTDATED ANALYSIS")
    print("="*60)
    
    json_path = Path('web_dashboard/scripts/outdated_ids.json')
    if not json_path.exists():
        print(f"Error: {json_path} not found.")
        return
        
    with open(json_path, 'r') as f:
        ids_to_delete = json.load(f)
        
    if not ids_to_delete:
        print("No IDs to delete.")
        return
        
    print(f"Loaded {len(ids_to_delete)} IDs to delete.")
    
    client = SupabaseClient(use_service_role=True)
    
    # Batch delete
    batch_size = 500
    total_deleted = 0
    
    # Split into chunks
    chunks = [ids_to_delete[i:i + batch_size] for i in range(0, len(ids_to_delete), batch_size)]
    
    for idx, chunk in enumerate(chunks):
        try:
            print(f"Deleting chunk {idx+1}/{len(chunks)} ({len(chunk)} records)...")
            res = client.supabase.table('congress_trades_analysis')\
                .delete()\
                .in_('id', chunk)\
                .execute()
                
            # Supabase delete returns the deleted rows usually
            count = len(res.data) if res.data else 0
            total_deleted += count
            print(f"  Deleted chunk {idx+1}/{len(chunks)}: {count} records wiped.")
            
        except Exception as e:
            print(f"  [ERROR] Chunk {idx+1} failed: {e}")
            
    print("\n" + "="*60)
    print(f"COMPLETE. Total Deleted: {total_deleted}")

if __name__ == "__main__":
    main()
