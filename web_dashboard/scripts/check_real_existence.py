
import sys
from pathlib import Path
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from supabase_client import SupabaseClient

def main():
    client = SupabaseClient(use_service_role=True)
    
    # List of "Real" names we expect to exist for the unmatched TMPs
    targets = [
        "French Hill", "J. D. Vance", "Terri Sewell", "Earl Blumenauer", 
        "Marco Rubio", "Jeffrey Duncan", "Mark Green", "Michael Burgess",
        "Thomas Carper", "Kathy Manning", "Gilbert Cisneros", "Valerie Hoyle"
    ]
    
    print(f"Checking for existence of {len(targets)} 'Real' politicians in DB...")
    
    found_count = 0
    missing = []
    
    for name in targets:
        # Search by name (ilike)
        res = client.supabase.table('politicians').select('*').ilike('name', f'%{name}%').not_.ilike('bioguide_id', 'TMP%').execute()
        
        if res.data:
            rec = res.data[0]
            print(f"[FOUND] '{name}' -> ID: {rec['id']}, Name: '{rec['name']}', Bio: {rec['bioguide_id']}")
            found_count += 1
        else:
            print(f"[MISSING] '{name}' - No real record found.")
            missing.append(name)
            
    print("\nSummary:")
    print(f"Found: {found_count}")
    print(f"Missing (Need Bioguide to Import): {len(missing)}")

if __name__ == "__main__":
    main()
