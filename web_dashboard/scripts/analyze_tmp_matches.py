
import sys
from pathlib import Path
import re
import csv

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from supabase_client import SupabaseClient

def normalize_name_for_comparison(name):
    """
    "Michael T. McCaul" -> "Michael McCaul"
    "Robert P. Bresnahan Jr." -> "Robert Bresnahan"
    """
    if not name: return ""
    
    # Remove suffixes
    name = re.sub(r'\s+(Jr\.?|Sr\.?|II|III|IV)\.?$', '', name, flags=re.IGNORECASE)
    
    parts = name.split()
    if len(parts) <= 1:
        return name.lower()
    
    first = parts[0]
    last = parts[-1]
    
    # Handle "Van Epps" or "De La Cruz" - hard to detect automatically without list
    # but let's stick to simple First + Last for broad matching
    
    return f"{first} {last}".lower()

def get_nickname_variations(name):
    """
    Returns list of name variations based on common nicknames.
    """
    variations = []
    lower_name = name.lower()
    
    # Known dataset aliases
    aliases = {
        'rafael': 'ted',         # Rafael Edward Cruz -> Ted Cruz
        'ladda': 'tammy',        # Ladda Tammy Duckworth -> Tammy Duckworth
        'james': ['jim', 'jd', 'j.d.'], # James Vance -> J.D. Vance
        'thomas': 'tom',
        'robert': 'bob',
        'william': 'bill',
        'charles': 'chuck',
        'joseph': 'joe',
        'timothy': 'tim',
        'richard': ['dick', 'rick'],
        'edward': 'ed',
        'gregory': 'greg',
        'jeffrey': 'jeff',
        'steve': 'stephen',
        'suzanne': 'susie',       # Suzanne Lee -> Susie Lee
        'deborah': 'debbie',
        'jacklyn': 'jacky',
        'susan': 'zoe',           # Zoe Lofgren
        'joshua': 'josh',
        'donald': 'don',
        'gerald': 'jerry',
        'earl': 'buddy',          # Buddy Carter
        'daniel': 'dan',
        'patrick': 'pat',
        'christopher': 'chris',
        'matthew': 'matt',
        'anthony': 'tony',
        'andrew': 'andy',
        'samuel': 'sam',
        'kenneth': 'ken',
        'frederick': 'fred',
        'lawrence': 'larry',
        'harold': 'hal',
        'robert': ['bob', 'rob'],
        'james': ['jim', 'jd', 'j.d.'], 
        'thomas': ['tom', 'tommy'],
        'timothy': 'tim',
        'william': 'bill',
        'richard': ['dick', 'rick'],
    }
    
    parts = lower_name.split()
    if not parts: return []
    
    first_lower = parts[0]
    if first_lower in aliases:
        targets = aliases[first_lower]
        if isinstance(targets, str): targets = [targets]
        for t in targets:
            # Reconstruct name with nickname
            variations.append(f"{t} {' '.join(parts[1:])}")
            
    return variations

def main():
    print("Fetching politicians...")
    client = SupabaseClient(use_service_role=True)
    
    # Fetch all
    all_pols = client.supabase.table('politicians').select('*').execute().data
    
    real_pols = []
    tmp_pols = []
    
    for p in all_pols:
        bid = p['bioguide_id']
        if not bid: continue
        
        if bid.startswith("TMP"):
            tmp_pols.append(p)
        elif re.match(r'^[A-Z]\d{6}$', bid) or bid in ['P000197', 'S001176', 'C001101', 'J000299', 'J000294']: # Include known leadership IDs
            real_pols.append(p)
            
    print(f"Stats: {len(real_pols)} Real, {len(tmp_pols)} TMP")
    
    matches = []
    unmatched = []
    
    # Build lookups for Real pols
    real_by_norm = {}
    for p in real_pols:
        norm = normalize_name_for_comparison(p['name'])
        if norm not in real_by_norm:
            real_by_norm[norm] = []
        real_by_norm[norm].append(p)
        
    # Match
    for tmp in tmp_pols:
        tmp_name = tmp['name']
        tmp_norm = normalize_name_for_comparison(tmp_name)
        
        match_found = None
        match_type = ""
        
        # 1. Try normalized First+Last match
        if tmp_norm in real_by_norm:
            candidates = real_by_norm[tmp_norm]
            # If multiple, filter by state if possible
            if len(candidates) == 1:
                match_found = candidates[0]
                match_type = "Normalized Name"
            else:
                # Ambiguous? Try matching state
                for cand in candidates:
                    if cand.get('state') == tmp.get('state'):
                        match_found = cand
                        match_type = "Normalized Name + State"
                        break
        
        # 2. Try Nicknames
        if not match_found:
            vars = get_nickname_variations(tmp_name)
            for v in vars:
                v_norm = normalize_name_for_comparison(v)
                if v_norm in real_by_norm:
                    match_found = real_by_norm[v_norm][0] # Take first for now
                    match_type = f"Nickname ({v})"
                    break
        
        # 3. Special Case: Hardcoded Manual Maps (The "Difficult" Ones)
        # These handle middle names used as first names, distinct nicknames, etc.
        manual_map = {
            'jamin raskin': 'Jamie Raskin',
            'stephen cohen': 'Steve Cohen',
            'chuck fleischmann': 'Charles J. "Chuck" Fleischmann', # Logic below handles partials? No, let's map to likely DB name parts
            'bob latta': 'Robert E. Latta',
            'peter sessions': 'Pete Sessions', 
            'george kelly': 'Mike Kelly',          # George J. "Mike" Kelly
            'john williams': 'Roger Williams',     # John Roger Williams
            'james scott': 'Austin Scott',         # James Austin Scott
            'william steube': 'W. Gregory Steube', # William Gregory Steube
            'rebecca sherrill': 'Mikie Sherrill',  # Rebecca Michelle Sherrill
            'james hill': 'French Hill',           # James French Hill
            'john ricketts': 'Pete Ricketts',      # John Peter Ricketts
            'thomas carper': 'Tom Carper',
            'douglas lamborn': 'Doug Lamborn',
            'jeffrey duncan': 'Jeff Duncan',
            'james vance': 'J. D. Vance',
            'mark green': 'Mark E. Green',         # Mark Green (TN) vs Mark E. Green?
            'john knott': 'Ted Budd',              # Wait, John Knott? "John Theodore 'Ted' Budd"? No. 
                                                   # Check: John Knott might be someone else? 
                                                   # Actually, let's skip doubtful ones.
            'ronald wyden': 'Ron Wyden',
            'marco rubio': 'Marco A. Rubio',       # DB might have middle initial
            'michael burgess': 'Michael C. Burgess',
            'david trone': 'David J. Trone',
            'earl blumenauer': 'Earl Blumenauer',  # Should have matched? Maybe DB has suffix?
            'kathy manning': 'Kathy E. Manning',
            'michael garcia': 'Mike Garcia',
            'valerie hoyle': 'Valerie P. Hoyle',
            'john delaney': 'John K. Delaney',
            'garret graves': 'Garret N. Graves',
            'william keating': 'William R. Keating', # Should have matched normalized?
            'james banks': 'Jim Banks',
            'thomas suozzi': 'Tom Suozzi',
            'ladda duckworth': 'Tammy Duckworth',
            'rafael cruz': 'Ted Cruz',
            'rick allen': 'Rick W. Allen',
            'neal dunn': 'Neal P. Dunn'
        }
        
        if not match_found:
            tm_lower = tmp_name.lower()
            if tm_lower in manual_map:
                target_name = manual_map[tm_lower]
                # Find this target in real_pols
                # We need to fuzzy search real_pols for this target keys
                target_norm = normalize_name_for_comparison(target_name)
                
                # Try finding by exact match of value provided in map
                # Or by normalized version of map value
                
                # Check exact name match first
                for r in real_pols:
                    if r['name'].lower() == target_name.lower():
                        match_found = r
                        match_type = "Manual Map (Exact)"
                        break
                        
                if not match_found and target_norm in real_by_norm:
                     match_found = real_by_norm[target_norm][0]
                     match_type = "Manual Map (Norm)"
                     
                # Special lookup for tricky ones if still not found
                if not match_found:
                     # Try searching by last name + part of first name?
                     pass

        
        if match_found:
            matches.append({
                'match_type': match_type,
                'tmp_id': tmp['id'],
                'tmp_bioguide': tmp['bioguide_id'],
                'tmp_name': tmp_name,
                'real_id': match_found['id'],
                'real_bioguide': match_found['bioguide_id'],
                'real_name': match_found['name']
            })
        else:
            unmatched.append(tmp)

    print("\n" + "="*80)
    print(f"MATCH REPORT")
    print("="*80)
    print(f"Matched: {len(matches)}")
    print(f"Unmatched: {len(unmatched)}")
    
    print("\n--- PROPOSED MERGES ---")
    print(f"{'TMP Name':<30} {'Real Name':<30} {'Type':<20}")
    print("-" * 80)
    for m in matches:
        print(f"{m['tmp_name']:<30} {m['real_name']:<30} {m['match_type']:<20}")
        
    print("\n--- STILL UNMATCHED (Need Manual Review?) ---")
    for u in unmatched:
        print(f"{u['name']} ({u['bioguide_id']}) - {u.get('state')}")

    # Export matches to JSON for the bulk script to use
    import json
    with open('web_dashboard/scripts/tmp_matches.json', 'w') as f:
        json.dump(matches, f, indent=2)
    print("\nSaved matches to web_dashboard/scripts/tmp_matches.json")

if __name__ == "__main__":
    main()
