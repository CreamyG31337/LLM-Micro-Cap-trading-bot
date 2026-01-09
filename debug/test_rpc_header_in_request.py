#!/usr/bin/env python3
"""Test if RPC calls actually send the Authorization header in the HTTP request"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"

def test_rpc_header_sent():
    """Test if RPC actually sends Authorization header"""
    print("=" * 80)
    print("TESTING IF RPC SENDS AUTHORIZATION HEADER")
    print("=" * 80)
    
    from supabase_client import SupabaseClient
    
    print("\n1. Creating client with token...")
    client = SupabaseClient(user_token=token)
    
    postgrest = client.supabase.postgrest
    session = postgrest.session
    
    print(f"   Session headers before RPC: {dict(session.headers)}")
    
    # Try to hook into the HTTP request to see what's actually sent
    print("\n2. Making RPC call...")
    import json as json_lib
    try:
        # Check if we can inspect the actual request
        # The postgrest client uses httpx, so we might be able to see the request
        result = client.supabase.rpc('set_user_preference', {
            'pref_key': 'test_header_sent',
            'pref_value': json_lib.dumps('test_value')
        }).execute()
        
        print(f"   RPC result: {repr(result.data)}")
        
        # Check if there's a way to see what headers were sent
        # The httpx client might have request history
        if hasattr(session, 'history'):
            print(f"\n3. Checking request history...")
            for request in session.history:
                print(f"   Request URL: {request.url}")
                print(f"   Request headers: {dict(request.headers)}")
                auth_header = request.headers.get('Authorization', 'NOT SET')
                print(f"   Authorization header in request: {auth_header[:50] if auth_header != 'NOT SET' else 'NOT SET'}...")
        
    except Exception as e:
        print(f"   [ERROR] {e}")
        import traceback
        traceback.print_exc()
    
    # Also test direct HTTP call to see the difference
    print("\n4. Testing direct HTTP call with explicit header...")
    import requests
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_anon_key = os.getenv('SUPABASE_PUBLISHABLE_KEY') or os.getenv('SUPABASE_ANON_KEY')
    
    response = requests.post(
        f"{supabase_url}/rest/v1/rpc/set_user_preference",
        headers={
            "apikey": supabase_anon_key,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "pref_key": "test_direct_http",
            "pref_value": json_lib.dumps("test_value")
        }
    )
    
    print(f"   Direct HTTP status: {response.status_code}")
    print(f"   Direct HTTP result: {response.json()}")
    if response.status_code == 200 and response.json() is True:
        print(f"   [SUCCESS] Direct HTTP with explicit header works!")
        print(f"   This proves auth.uid() CAN work if the header is sent correctly")

if __name__ == "__main__":
    test_rpc_header_sent()
