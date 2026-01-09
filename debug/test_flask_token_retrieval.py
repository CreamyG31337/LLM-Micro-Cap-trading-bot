#!/usr/bin/env python3
"""Test how Flask retrieves token from cookies"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

def test_flask_token():
    """Test Flask token retrieval"""
    print("=" * 80)
    print("TESTING FLASK TOKEN RETRIEVAL")
    print("=" * 80)
    
    # Simulate Flask request context with cookie
    from flask import Flask, request
    from flask_auth_utils import get_auth_token, get_user_id_flask
    
    app = Flask(__name__)
    
    # Token from user
    token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"
    
    with app.test_request_context(headers={'Cookie': f'auth_token={token}'}):
        print("\n1. Testing get_auth_token()...")
        flask_token = get_auth_token()
        if flask_token:
            print(f"   [OK] Token retrieved: {flask_token[:50]}... (length: {len(flask_token)})")
            print(f"   Token matches: {flask_token == token}")
        else:
            print(f"   [FAIL] No token retrieved!")
            return
        
        print("\n2. Testing get_user_id_flask()...")
        user_id = get_user_id_flask()
        if user_id:
            print(f"   [OK] User ID: {user_id}")
        else:
            print(f"   [FAIL] No user ID!")
            return
        
        print("\n3. Creating SupabaseClient with Flask token...")
        from supabase_client import SupabaseClient
        client = SupabaseClient(user_token=flask_token)
        
        # Check if header is set
        postgrest = client.supabase.postgrest
        session = postgrest.session
        auth_header = session.headers.get('Authorization', '')
        
        if auth_header:
            print(f"   [OK] Authorization header IS set: {auth_header[:50]}...")
        else:
            print(f"   [FAIL] Authorization header NOT set!")
            return
        
        print("\n4. Testing RPC call with Flask token...")
        import json
        test_value = "test_from_flask_token_script"
        result = client.supabase.rpc('set_user_preference', {
            'pref_key': 'test_key_flask_token',
            'pref_value': json.dumps(test_value)
        }).execute()
        
        print(f"   RPC result: {repr(result.data)}")
        if result.data is True or (isinstance(result.data, list) and len(result.data) > 0 and result.data[0] is True):
            print(f"   [SUCCESS] RPC returned True!")
        else:
            print(f"   [FAIL] RPC returned False")
            print(f"   This means auth.uid() is NULL in the function")

if __name__ == "__main__":
    test_flask_token()
