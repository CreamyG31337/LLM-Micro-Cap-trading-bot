
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Setup path to import from web_dashboard
current_dir = os.getcwd()
# Script is now in /debug, so we need to go up one level to find web_dashboard
project_root = os.path.dirname(current_dir)
sys.path.append(os.path.join(project_root, 'web_dashboard'))
sys.path.append(project_root)

# Mock streamlit 
import unittest.mock
sys.modules['streamlit'] = unittest.mock.MagicMock()

def get_client_direct():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("Missing SUPABASE env vars")
        return None
        
    try:
        from supabase import create_client
        return create_client(url, key)
    except ImportError:
        print("Could not import supabase package")
        return None

def debug_metrics():
    # Try multiple paths for .env
    env_path = os.path.join(project_root, 'web_dashboard', '.env')
    if not os.path.exists(env_path):
        env_path = os.path.join(project_root, '.env')
        
    print(f"Loading env from {env_path}")
    load_dotenv(env_path, override=True)
    
    # Debug env vars
    supabase_keys = [k for k in os.environ.keys() if 'SUPABASE' in k]
    print(f"Found SUPABASE keys: {supabase_keys}")
    
    client = get_client_direct()
    if not client:
        print("Failed to init client")
        return

    # Hardcoded test values
    fund = "Project Chimera" 
    user_email = "lance.colton@gmail.com"
    
    print(f"DEBUG: Testing for Fund='{fund}', Email='{user_email}'")
    
    # 1. Check RLS/Data Visibility
    print("\n1. Checking fund_contributions visibility...")
    try:
        res = client.table("fund_contributions").select("*").eq("fund", fund).execute()
        data = res.data
        print(f"Found {len(data)} rows in fund_contributions.")
        
        user_contribs = []
        if data:
            user_contribs = [r for r in data if str(r.get('email', '')).lower() == user_email.lower()]
            print(f"rows matching email: {len(user_contribs)}")
        
        if not user_contribs:
            print("!! NO MATCHING CONTRIBUTIONS FOUND FOR USER !!")
            if data:
                print("Sample emails in DB:", [r.get('email') for r in data[:5]])
                
            # Check user profile
            print("\nChecking user profile:")
            prof = client.table("user_profiles").select("*").ilike("email", user_email).execute()
            if prof.data:
                print(f"User profile: {prof.data[0]}")
            else:
                 print("User profile NOT FOUND")
            return
        else:
            print("User contributions FOUND (RLS OK or Service Role used).")
            # If we are using service role, we bypass RLS. 
            # Ideally we want to test AS the user, but we can't easily auth as them here without password.
            # But the Fact that we see data means the data exists. 
            # If the UI doesn't see it, it implies RLS is blocking the USER specifically.
            
    except Exception as e:
        print(f"Error checking contributions: {e}")
        return

    # 3. Simulate NAV Logic (Simplified)
    print("\n3. Simulating NAV logic...")
    
    all_contributions = data
    
    # Parse timestamps
    contributions = []
    for record in all_contributions:
        ts = record.get('timestamp')
        if isinstance(ts, str):
            try:
                ts = ts.replace('Z', '+00:00')
                ts = datetime.fromisoformat(ts)
            except:
                pass
        
        contributions.append({
            'contributor': record.get('contributor'),
            'email': record.get('email'),
            'amount': float(record.get('amount', 0)),
            'type': record.get('contribution_type', 'CONTRIBUTION').lower(),
            'timestamp': ts or datetime.min
        })
        
    contributions.sort(key=lambda x: x['timestamp'])
    print(f"Processed {len(contributions)} contributions")
    
    contributor_units = {}
    total_units = 0.0
    
    for c in contributions:
        nav = 1.0 # Mock
        amount = c['amount']
        
        if c['contributor'] not in contributor_units:
            contributor_units[c['contributor']] = 0.0
            
        if c['type'] == 'withdrawal':
            if total_units > 0:
                units = amount / nav
                contributor_units[c['contributor']] -= units
                total_units -= units
        else:
            units = amount / nav
            contributor_units[c['contributor']] += units
            total_units += units
            
    print(f"\nTotal Units: {total_units}")
    print("Contributor Units:")
    for k, v in contributor_units.items():
        if 'lance' in str(k).lower():
             print(f" -> {k}: {v}")

    user_email_lower = user_email.lower()
    match_found = False
    for c in contributions:
        if str(c.get('email', '')).lower() == user_email_lower:
            match_found = True
            break
            
    if not match_found:
        print("!! Logic Break: User email not found in contributions loop !!")
    else:
        print("User email found in contributions.")

if __name__ == "__main__":
    debug_metrics()
