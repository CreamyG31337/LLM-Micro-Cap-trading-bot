#!/usr/bin/env python3
"""Test setting auth header and making RPC call"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

def test_auth_header():
    """Test setting auth header correctly"""
    print("=" * 80)
    print("TESTING AUTH HEADER SETTING")
    print("=" * 80)
    
    # Token from user
    token = os.getenv('AUTH_TOKEN') or "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"
    
    if not token:
        print("\nERROR: No token available")
        return
    
    print(f"\n1. Token: {token[:50]}... (length: {len(token)})")
    
    try:
        from supabase_client import SupabaseClient
        
        print("\n2. Creating SupabaseClient with token...")
        client = SupabaseClient(user_token=token)
        
        # Check postgrest structure
        postgrest = client.supabase.postgrest
        session = postgrest.session
        
        print("\n3. Checking Authorization header...")
        # httpx.Headers is a case-insensitive dict-like object
        auth_header = session.headers.get('Authorization', '')
        if auth_header:
            print(f"   [OK] Authorization header IS set: {auth_header[:50]}...")
        else:
            print(f"   [FAIL] Authorization header NOT set")
            print(f"   Current headers: {dict(session.headers)}")
            
            # Try to set it
            print("\n4. Attempting to set Authorization header...")
            try:
                # httpx.Headers can be set like a dict
                session.headers['Authorization'] = f'Bearer {token}'
                print(f"   [OK] Set header via session.headers['Authorization']")
                
                # Verify
                auth_header = session.headers.get('Authorization', '')
                if auth_header:
                    print(f"   [OK] Verified header is set: {auth_header[:50]}...")
                else:
                    print(f"   [FAIL] Header still not set after assignment")
            except Exception as e:
                print(f"   [FAIL] Error setting header: {e}")
                import traceback
                traceback.print_exc()
        
        # Test RPC call
        print("\n5. Testing RPC call...")
        try:
            # Get user_id from token
            import base64
            token_parts = token.split('.')
            payload = token_parts[1]
            payload += '=' * (4 - len(payload) % 4)
            decoded = base64.urlsafe_b64decode(payload)
            user_data = json.loads(decoded)
            user_id = user_data.get('sub') or user_data.get('user_id')
            
            print(f"   User ID from token: {user_id}")
            
            # Check if profile exists
            profile = client.supabase.table('user_profiles').select('user_id, email').eq('user_id', user_id).execute()
            if profile.data:
                print(f"   [OK] Profile exists: {profile.data[0].get('email')}")
            else:
                print(f"   [FAIL] Profile does not exist!")
                return
            
            # Test RPC
            test_value = "test_from_auth_header_script"
            result = client.supabase.rpc('set_user_preference', {
                'pref_key': 'test_key_auth_header',
                'pref_value': json.dumps(test_value)
            }).execute()
            
            print(f"   RPC result: {repr(result.data)}")
            if result.data is True or (isinstance(result.data, list) and len(result.data) > 0 and result.data[0] is True):
                print(f"   [SUCCESS] RPC returned True!")
            else:
                print(f"   [FAIL] RPC returned False")
                print(f"   This means auth.uid() is NULL in the function")
                print(f"   Check Supabase logs for WARNING messages")
                
        except Exception as e:
            print(f"   [ERROR] RPC call failed: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth_header()
