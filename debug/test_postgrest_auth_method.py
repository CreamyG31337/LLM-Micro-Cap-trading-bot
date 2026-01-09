#!/usr/bin/env python3
"""Test if postgrest.auth() actually works or if we need to set headers directly"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"

def test_auth_method():
    """Test if postgrest.auth() works"""
    print("=" * 80)
    print("TESTING postgrest.auth() METHOD")
    print("=" * 80)
    
    from supabase_client import SupabaseClient
    
    # Create client WITHOUT token first
    print("\n1. Creating client WITHOUT token...")
    client = SupabaseClient()
    postgrest = client.supabase.postgrest
    session = postgrest.session
    
    print(f"   Authorization header before: {session.headers.get('Authorization', 'NOT SET')}")
    
    # Try calling auth() method
    print("\n2. Calling postgrest.auth(token)...")
    try:
        postgrest.auth(token)
        print(f"   [OK] postgrest.auth() call succeeded")
        
        auth_after = session.headers.get('Authorization', '')
        if auth_after:
            print(f"   Authorization header after: {auth_after[:50]}...")
        else:
            print(f"   [FAIL] Authorization header still NOT SET after auth() call")
    except Exception as e:
        print(f"   [ERROR] postgrest.auth() failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Try setting directly
    print("\n3. Setting header directly on session.headers...")
    try:
        session.headers['Authorization'] = f'Bearer {token}'
        auth_direct = session.headers.get('Authorization', '')
        if auth_direct:
            print(f"   [OK] Direct header setting worked: {auth_direct[:50]}...")
        else:
            print(f"   [FAIL] Direct header setting did NOT work")
    except Exception as e:
        print(f"   [ERROR] Direct header setting failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test RPC with both methods
    print("\n4. Testing RPC call...")
    import json
    try:
        result = client.supabase.rpc('set_user_preference', {
            'pref_key': 'test_auth_method',
            'pref_value': json.dumps('test_value')
        }).execute()
        
        print(f"   RPC result: {repr(result.data)}")
        if result.data is True or (isinstance(result.data, list) and len(result.data) > 0 and result.data[0] is True):
            print(f"   [SUCCESS] RPC worked!")
        else:
            print(f"   [FAIL] RPC returned False")
    except Exception as e:
        print(f"   [ERROR] RPC call failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth_method()
