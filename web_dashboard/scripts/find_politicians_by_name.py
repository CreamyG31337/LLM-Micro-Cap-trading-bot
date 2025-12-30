#!/usr/bin/env python3
"""
Find politicians by name to see if they exist with different IDs
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

from supabase_client import SupabaseClient

# Politician names from the debug output
politician_names = [
    "Joshua Gottheimer", "Thomas Kean Jr", "William Keating", "Michael Burgess",
    "Earl Blumenauer", "Valerie Hoyle", "Thomas Carper", "Peter Sessions",
    "Lisa McClain", "Kathy Manning", "Jonathan Jackson", "Mark Green",
    "Stephen Lynch", "James Hill", "David Joyce", "John Curtis",
    "Rick Allen", "Robert Wittman", "Bob Latta", "Deborah Dingell",
    "Neal Dunn", "Stephen Cohen", "Gregory Landsman", "Laurel Lee",
    "Thomas Suozzi", "Gary Peters", "Gerry Connolly", "Suzanne Lee",
    "Ronald Wyden", "George Kelly", "Jennifer McClellan", "Katherine Clark",
    "Garret Graves", "Jamin Raskin", "Deborah Wasserman Schultz", "Suzan DelBene",
    "John Knott", "Gus Bilirakis", "James Scott", "John McGuire III",
    "John Neely Kennedy", "Gerald Moran", "John Hickenlooper", "Robert Aderholt"
]

def main():
    print("Searching for politicians by name...")
    print("=" * 70)
    
    supabase = SupabaseClient()
    
    found_politicians = {}
    not_found = []
    
    for name in politician_names:
        # Try exact match first
        result = supabase.supabase.table('politicians')\
            .select('id, name, bioguide_id')\
            .ilike('name', f'%{name}%')\
            .execute()
        
        if result.data:
            # Take first match
            pol = result.data[0]
            found_politicians[name] = pol
            print(f"[FOUND] {name} -> ID: {pol['id']}, Name: {pol['name']}, Bioguide: {pol.get('bioguide_id', 'N/A')}")
        else:
            not_found.append(name)
            print(f"[NOT FOUND] {name}")
    
    print("\n" + "=" * 70)
    print(f"Summary: Found {len(found_politicians)}, Not Found {len(not_found)}")
    
    if not_found:
        print("\nPoliticians not found in database:")
        for name in not_found:
            print(f"  - {name}")

if __name__ == "__main__":
    main()

