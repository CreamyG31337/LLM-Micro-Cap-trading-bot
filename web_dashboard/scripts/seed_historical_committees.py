
import sys
from pathlib import Path
from datetime import datetime
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

# Hardcoded historical assignments based on research
# Format: Bioguide -> [Committee Code, ...]
# Codes are standard (e.g., HSAS = House Armed Services, SSFI = Senate Finance)
# We map typical names to codes below.
HISTORICAL_COMMITTEES = {
    'C001124': ['HSAS', 'HSSM'], # Gilbert Cisneros: Armed Services, Small Business
    'C000174': ['SSEV', 'SSFI', 'SSGA'], # Thomas Carper: Environment (Chair), Finance, Homeland Security
    'B001248': ['HSBU', 'HSIF', 'HSRU'], # Michael Burgess: Budget, Energy & Commerce, Rules
    'B001227': ['HSWM', 'HSBU'], # Earl Blumenauer: Ways & Means, Budget
    'G000590': ['HSHM', 'HSFA'], # Mark Green: Homeland Security (Chair), Foreign Affairs
    'D000620': ['HSBA', 'HSEC'], # John Delaney: Financial Services, JEC (Economic)
    'L000564': ['HSAS', 'HSII'], # Douglas Lamborn: Armed Services, Natural Resources
    'R000595': ['SSFR', 'SSIN', 'SSAP', 'SSSB'], # Marco Rubio: Foreign Relations, Intelligence, Appropriations, Small Business
    'G000577': ['HSTB', 'HSZZ'], # Garret Graves: Transportation, Select Modernization (mapped to general/misc)
    'S001176': ['HSIF'], # Steve Scalise: Energy & Commerce (technically House Leadership mostly)
    'P000197': [], # Nancy Pelosi: Speaker/Leadership (usually no committees)
    'C001101': ['HSAP'], # Katherine Clark: Appropriations (before leadership)
    'T000486': ['HSAP', 'HSBU'], # David Trone: Appropriations, Budget
    'V000137': ['SSBK', 'SSCM', 'SSSE'], # JD Vance: Banking, Commerce, Aging
}

# Mapping of codes to names for insertion if missing they act as fallbacks 
# (though we prefer linking to existing committee table records)
COMMITTEE_METADATA = {
    'HSAS': 'House Committee on Armed Services',
    'HSSM': 'House Committee on Small Business',
    'SSEV': 'Senate Committee on Environment and Public Works',
    'SSFI': 'Senate Committee on Finance',
    'SSGA': 'Senate Committee on Homeland Security and Governmental Affairs',
    'HSBU': 'House Committee on the Budget',
    'HSIF': 'House Committee on Energy and Commerce',
    'HSRU': 'House Committee on Rules',
    'HSWM': 'House Committee on Ways and Means',
    'HSHM': 'House Committee on Homeland Security',
    'HSFA': 'House Committee on Foreign Affairs',
    'HSBA': 'House Committee on Financial Services',
    'HSEC': 'Joint Economic Committee',
    'HSII': 'House Committee on Natural Resources',
    'SSFR': 'Senate Committee on Foreign Relations',
    'SSIN': 'Senate Select Committee on Intelligence',
    'SSAP': 'Senate Committee on Appropriations',
    'SSSB': 'Senate Committee on Small Business and Entrepreneurship',
    'HSTB': 'House Committee on Transportation and Infrastructure',
    'HSAP': 'House Committee on Appropriations',
    'SSBK': 'Senate Committee on Banking, Housing, and Urban Affairs',
    'SSCM': 'Senate Committee on Commerce, Science, and Transportation',
    'SSSE': 'Senate Special Committee on Aging',
    'HSZZ': 'Select Committee on the Modernization of Congress'
}

def main():
    print("="*60)
    print("SEEDING HISTORICAL COMMITTEES")
    print("="*60)
    client = SupabaseClient(use_service_role=True)
    
    # 1. Fetch relevant politicians to get IDs
    print("\nFetching politician IDs...")
    bioguides = list(HISTORICAL_COMMITTEES.keys())
    pols = client.supabase.table('politicians').select('id, name, bioguide_id').in_('bioguide_id', bioguides).execute()
    
    pol_map = {p['bioguide_id']: {'id': p['id'], 'name': p['name']} for p in pols.data}
    print(f"  Found {len(pol_map)}/{len(bioguides)} politicians in DB.")
    
    # 2. Iterate and Insert Assignments
    count = 0
    for bg, committees in HISTORICAL_COMMITTEES.items():
        if bg not in pol_map:
            print(f"  [SKIP] Politician not found for {bg}")
            continue
            
        pid = pol_map[bg]['id']
        pname = pol_map[bg]['name']
        print(f"\nProcessing {pname} ({bg})")
        
        for code in committees:
            # Check if committee exists in 'committees' table, if not, try to insert?
            # For now, let's assume standard codes connect to existing committees or we insert assignments by code directly?
            # Creating assignment usually requires a committee_id.
            
            # Find committee_id for this code
            # Note: DB schema for 'committees' table usually has 'id' and 'code' or 'name'.
            # Let's check matching by code or name using ilike
            
            # Try finding committee by name mapping
            cname = COMMITTEE_METADATA.get(code, code)
            
            # Try strict code match first (if table has code) -> My knowledge says table has 'code' ?
            # Let's try matching by name derived from code map
            
            comm_res = client.supabase.table('committees').select('id, name').ilike('name', cname).execute()
            
            if not comm_res.data:
                # Fallback: try fuzzier match
                comm_res = client.supabase.table('committees').select('id, name').ilike('name', f"%{cname.replace('Committee on ', '')}%").execute()
            
            if comm_res.data:
                cid = comm_res.data[0]['id']
                actual_name = comm_res.data[0]['name']
                
                # Upsert assignment
                assignment_data = {
                    'politician_id': pid,
                    'committee_id': cid,
                    # 'role': 'Member' # Default
                }
                
                try:
                    # Check existing
                    exist = client.supabase.table('committee_assignments')\
                        .select('*')\
                        .eq('politician_id', pid)\
                        .eq('committee_id', cid)\
                        .execute()
                        
                    if not exist.data:
                        client.supabase.table('committee_assignments').insert(assignment_data).execute()
                        print(f"  [ADDED] {actual_name} ({code})")
                        count += 1
                    else:
                        print(f"  [EXIST] {actual_name}")
                except Exception as e:
                    print(f"  [ERROR] {e}")
            else:
                print(f"  [MISSING COMMITTEE] Could not find '{cname}' in DB")
                
    print("\n" + "="*60)
    print(f"COMPLETE. Assignments Added: {count}")

if __name__ == "__main__":
    main()
