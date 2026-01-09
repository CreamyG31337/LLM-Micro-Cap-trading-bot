#!/usr/bin/env python3
"""Test how client is created in Flask context vs our tests"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"

def test_flask_client_creation():
    """Test client creation exactly like user_preferences.py does it"""
    print("=" * 80)
    print("TESTING CLIENT CREATION LIKE user_preferences.py")
    print("=" * 80)
    
    from flask import Flask, request
    from flask_auth_utils import get_auth_token
    from supabase_client import SupabaseClient
    
    app = Flask(__name__)
    
    with app.test_request_context(headers={'Cookie': f'auth_token={token}'}):
        print("\n1. Getting token from Flask cookies...")
        flask_token = get_auth_token()
        print(f"   Token retrieved: {bool(flask_token)}, length: {len(flask_token) if flask_token else 0}")
        print(f"   Token matches: {flask_token == token}")
        
        if not flask_token:
            print("   [FAIL] No token from Flask!")
            return
        
        print("\n2. Creating SupabaseClient exactly like user_preferences.py...")
        client = SupabaseClient(user_token=flask_token)
        
        # Check if header is set
        postgrest = client.supabase.postgrest
        session = postgrest.session
        auth_header = session.headers.get('Authorization', '')
        
        print(f"   Authorization header set: {bool(auth_header)}")
        if auth_header:
            print(f"   Header value: {auth_header[:50]}...")
        else:
            print(f"   [FAIL] Header NOT set!")
            return
        
        print("\n3. Testing RPC call...")
        import json as json_lib
        result = client.supabase.rpc('set_user_preference', {
            'pref_key': 'test_flask_client',
            'pref_value': json_lib.dumps('test_value')
        }).execute()
        
        print(f"   RPC result: {repr(result.data)}")
        if result.data is True or (isinstance(result.data, list) and len(result.data) > 0 and result.data[0] is True):
            print(f"   [SUCCESS] RPC worked - auth.uid() should work!")
        else:
            print(f"   [FAIL] RPC returned False")
            print(f"   This means auth.uid() is NULL even though header is set")
            print(f"   This is the actual problem we need to fix")

if __name__ == "__main__":
    test_flask_client_creation()
