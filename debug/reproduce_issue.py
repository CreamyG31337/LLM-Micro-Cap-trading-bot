
import os
import sys
import json
from dotenv import load_dotenv

# Add web_dashboard to path to find utils
current_dir = os.getcwd()
sys.path.append(os.path.join(current_dir, 'web_dashboard'))

# Mock streamlit
import unittest.mock
sys.modules['streamlit'] = unittest.mock.MagicMock()

def check_contributions():
    load_dotenv()
    
    try:
        from supabase_client import get_supabase_client
        client = get_supabase_client()
    except Exception as e:
        print(f"Import error: {e}")
        try:
             # Fallback
             import supabase
             url = os.environ.get("SUPABASE_URL")
             key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY")
             client = supabase.create_client(url, key)
             class MockClient:
                 def __init__(self, s): self.supabase = s
             client = MockClient(client)
        except Exception as e2:
             print(f"Fallback failed: {e2}")
             return

    if not client:
        print("Failed to initialize Supabase client")
        return

    print("Supabase client initialized.")
    
    target_email = 'lance.colton@gmail.com'
    print(f"\nChecking user_profiles for {target_email}...")
    try:
        res = client.supabase.table("user_profiles").select("user_id, email, role").ilike('email', target_email).execute()
        users = res.data
        if users:
            print(f"Found user: {users[0]}")
            user_id = users[0]['user_id']
            
            # Check user_funds
            print(f"\nChecking user_funds for user_id {user_id}...")
            res_funds = client.supabase.table("user_funds").select("*").eq("user_id", user_id).execute()
            funds = res_funds.data
            print(f"Found {len(funds)} assigned funds in user_funds:")
            for f in funds:
                print(f" - {f.get('fund_name')}")

            # Check contributor_access
            print(f"\nChecking contributor_access for user_id {user_id}...")
            try:
                res_access = client.supabase.table("contributor_access").select("*, contributors(fund)").eq("user_id", user_id).execute()
                print(f"Found {len(res_access.data)} access records.")
                for a in res_access.data:
                    print(a)
            except Exception as e:
                print(f"Error querying contributor_access: {e}")

        else:
            print("User not found in user_profiles.")
    except Exception as e:
        print(f"Error checking user info: {e}")

if __name__ == "__main__":
    check_contributions()
