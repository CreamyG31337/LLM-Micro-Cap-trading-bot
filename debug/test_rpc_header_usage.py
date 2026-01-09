#!/usr/bin/env python3
"""Test if RPC calls actually use the Authorization header from session"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"

def test_rpc_header():
    """Test if RPC uses Authorization header"""
    print("=" * 80)
    print("TESTING IF RPC CALLS USE AUTHORIZATION HEADER")
    print("=" * 80)
    
    from supabase_client import SupabaseClient
    
    print("\n1. Creating client with token...")
    client = SupabaseClient(user_token=token)
    
    postgrest = client.supabase.postgrest
    session = postgrest.session
    
    print("\n2. Checking Authorization header before RPC...")
    auth_before = session.headers.get('Authorization', '')
    print(f"   Authorization header: {auth_before[:50] if auth_before else 'NOT SET'}...")
    
    # Try to inspect how RPC calls are made
    print("\n3. Inspecting RPC method...")
    rpc_method = client.supabase.rpc
    print(f"   RPC method type: {type(rpc_method)}")
    
    # Check if we can see how it makes requests
    print("\n4. Making RPC call and checking if header is used...")
    try:
        # Get user_id from token
        import base64
        token_parts = token.split('.')
        payload = token_parts[1]
        payload += '=' * (4 - len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        user_data = json.loads(decoded)
        user_id = user_data.get('sub')
        
        print(f"   User ID from token: {user_id}")
        
        # Make RPC call
        result = client.supabase.rpc('set_user_preference', {
            'pref_key': 'test_header_check',
            'pref_value': json.dumps('test_value')
        }).execute()
        
        print(f"   RPC result: {repr(result.data)}")
        
        # Check header after
        auth_after = session.headers.get('Authorization', '')
        print(f"\n5. Authorization header after RPC: {auth_after[:50] if auth_after else 'NOT SET'}...")
        
        if result.data is True or (isinstance(result.data, list) and len(result.data) > 0 and result.data[0] is True):
            print(f"   [SUCCESS] RPC worked - header was used correctly")
        else:
            print(f"   [FAIL] RPC returned False")
            print(f"   This means auth.uid() returned NULL in the function")
            print(f"   Even though Authorization header is set: {bool(auth_before)}")
            
    except Exception as e:
        print(f"   [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_rpc_header()
