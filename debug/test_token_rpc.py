#!/usr/bin/env python3
"""Test token and RPC call to see what's happening"""

import os
import sys
import json
import base64

# Add web_dashboard to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

def test_token_and_rpc():
    """Test the token and RPC call"""
    print("=" * 80)
    print("TESTING TOKEN AND RPC CALL")
    print("=" * 80)
    
    # Get token from environment
    token = os.getenv('AUTH_TOKEN')
    if not token:
        print("\nERROR: Set AUTH_TOKEN environment variable")
        print("   PowerShell: $env:AUTH_TOKEN='your-token-here'")
        print("   Or get it from browser cookies after logging in")
        return
    
    print(f"\n1. Token received (length: {len(token)})")
    print(f"   First 50 chars: {token[:50]}...")
    
    # Decode token to see what's in it
    try:
        token_parts = token.split('.')
        if len(token_parts) >= 2:
            payload = token_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            user_data = json.loads(decoded)
            user_id = user_data.get('sub') or user_data.get('user_id')
            email = user_data.get('email')
            exp = user_data.get('exp', 0)
            print(f"\n2. Token decoded:")
            print(f"   user_id: {user_id}")
            print(f"   email: {email}")
            print(f"   exp: {exp}")
    except Exception as e:
        print(f"\n2. ERROR decoding token: {e}")
        return
    
    # Create Supabase client
    print(f"\n3. Creating SupabaseClient...")
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient(user_token=token)
        print(f"   Client created")
        
        # Check if postgrest exists and what its structure is
        if hasattr(client, 'supabase'):
            print(f"   client.supabase exists")
            if hasattr(client.supabase, 'postgrest'):
                print(f"   client.supabase.postgrest exists")
                postgrest = client.supabase.postgrest
                
                # Check session
                if hasattr(postgrest, 'session'):
                    print(f"   postgrest.session exists")
                    session = postgrest.session
                    if hasattr(session, 'headers'):
                        headers = session.headers
                        print(f"   postgrest.session.headers exists: {type(headers)}")
                        auth_header = headers.get('Authorization', '')
                        if auth_header:
                            print(f"   Authorization header IS set: {auth_header[:50]}...")
                        else:
                            print(f"   Authorization header NOT set!")
                            print(f"   Available headers: {list(headers.keys())}")
                    else:
                        print(f"   postgrest.session.headers does NOT exist")
                        print(f"   session attributes: {dir(session)}")
                else:
                    print(f"   postgrest.session does NOT exist")
                    print(f"   postgrest attributes: {dir(postgrest)}")
                
                # Check if auth method exists
                if hasattr(postgrest, 'auth'):
                    print(f"   postgrest.auth() method exists")
                else:
                    print(f"   postgrest.auth() method does NOT exist")
            else:
                print(f"   client.supabase.postgrest does NOT exist")
        else:
            print(f"   client.supabase does NOT exist")
    except Exception as e:
        print(f"   ERROR creating client: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check if profile exists
    print(f"\n4. Checking if user profile exists...")
    try:
        profile_result = client.supabase.table('user_profiles').select('user_id, email').eq('user_id', user_id).execute()
        print(f"   Found {len(profile_result.data) if profile_result.data else 0} profile(s)")
        if profile_result.data:
            print(f"   Email: {profile_result.data[0].get('email')}")
        else:
            print(f"   ERROR: Profile does not exist!")
            return
    except Exception as e:
        print(f"   ERROR checking profile: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test RPC call
    print(f"\n5. Testing RPC set_user_preference...")
    test_value = "test_from_script"
    try:
        rpc_result = client.supabase.rpc('set_user_preference', {
            'pref_key': 'test_key_script',
            'pref_value': json.dumps(test_value)
        }).execute()
        
        print(f"   RPC result: {repr(rpc_result.data)}")
        print(f"   Type: {type(rpc_result.data).__name__}")
        
        if rpc_result.data is True or (isinstance(rpc_result.data, list) and len(rpc_result.data) > 0 and rpc_result.data[0] is True):
            print(f"   SUCCESS: RPC returned True")
        else:
            print(f"   FAILED: RPC returned False")
            print(f"   This means the UPDATE matched 0 rows")
            print(f"   Check Supabase logs for WARNING messages from the function")
    except Exception as e:
        print(f"   ERROR calling RPC: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_token_and_rpc()
