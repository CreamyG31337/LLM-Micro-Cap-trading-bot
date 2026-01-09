#!/usr/bin/env python3
"""Test what headers are actually sent with RPC requests"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"

def test_actual_request():
    """Test what's actually sent in the HTTP request"""
    print("=" * 80)
    print("TESTING ACTUAL HTTP REQUEST HEADERS")
    print("=" * 80)
    
    from supabase_client import SupabaseClient
    
    # Create client
    client = SupabaseClient(user_token=token)
    
    # Check header is set
    postgrest = client.supabase.postgrest
    session = postgrest.session
    print(f"\n1. Session headers: {dict(session.headers)}")
    
    # Try to intercept the actual request
    print("\n2. Making RPC call and checking what's sent...")
    
    # The postgrest client uses httpx, which has event hooks
    # Let's see if we can hook into the request
    original_request = session.request
    
    captured_headers = None
    
    def capture_request(*args, **kwargs):
        nonlocal captured_headers
        # Get the headers from kwargs or args
        if 'headers' in kwargs:
            captured_headers = kwargs['headers']
        elif len(args) > 1 and isinstance(args[1], dict):
            captured_headers = args[1].get('headers', {})
        return original_request(*args, **kwargs)
    
    # Try to monkey-patch (might not work with httpx)
    try:
        session.request = capture_request
    except:
        pass
    
    import json as json_lib
    result = client.supabase.rpc('set_user_preference', {
        'pref_key': 'test_capture',
        'pref_value': json_lib.dumps('test_value')
    }).execute()
    
    print(f"   RPC result: {repr(result.data)}")
    
    if captured_headers:
        print(f"\n3. Captured headers from request: {captured_headers}")
        auth_header = captured_headers.get('Authorization', 'NOT SET')
        print(f"   Authorization in request: {auth_header[:50] if auth_header != 'NOT SET' else 'NOT SET'}...")
    else:
        print(f"\n3. Could not capture headers from request")
        print(f"   But RPC result: {repr(result.data)}")
        if result.data is True:
            print(f"   [SUCCESS] RPC worked, so header WAS sent correctly")
        else:
            print(f"   [FAIL] RPC returned False, header might not have been sent")
    
    # Also test by checking the postgrest RPC method directly
    print("\n4. Inspecting postgrest.rpc method...")
    rpc_method = postgrest.rpc
    print(f"   RPC method: {rpc_method}")
    print(f"   RPC method type: {type(rpc_method)}")
    
    # Check if postgrest has a way to see what it's sending
    if hasattr(postgrest, 'session'):
        print(f"   Session type: {type(postgrest.session)}")
        print(f"   Session has headers: {hasattr(postgrest.session, 'headers')}")

if __name__ == "__main__":
    test_actual_request()
