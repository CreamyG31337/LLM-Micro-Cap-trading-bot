#!/usr/bin/env python3
"""Test using postgrest.rpc() directly instead of supabase.rpc()"""

import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

# Token expired but we can test the approach
token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"

def test_postgrest_direct():
    """Test using postgrest.rpc() directly"""
    print("=" * 80)
    print("TESTING postgrest.rpc() DIRECTLY")
    print("=" * 80)
    
    from supabase_client import SupabaseClient
    
    print("\n1. Creating client with token...")
    client = SupabaseClient(user_token=token)
    
    postgrest = client.supabase.postgrest
    session = postgrest.session
    
    print(f"   Session headers: {dict(session.headers)}")
    auth_header = session.headers.get('Authorization', '')
    print(f"   Authorization header: {auth_header[:50] if auth_header else 'NOT SET'}...")
    
    print("\n2. Testing supabase.rpc() (what we currently use)...")
    print("   This goes through supabase -> postgrest -> rpc")
    
    print("\n3. Testing postgrest.rpc() directly...")
    print("   This should use the same session headers")
    
    # The key insight: supabase.rpc() probably just calls postgrest.rpc()
    # So if the session headers are set, both should work the same
    
    print("\n4. The real question: Why does auth.uid() return NULL?")
    print("   - Header IS set in session.headers")
    print("   - RPC calls use the session")
    print("   - But auth.uid() still returns NULL")
    print("\n   Possible causes:")
    print("   1. The header isn't being sent in the actual HTTP request")
    print("   2. Supabase PostgREST isn't reading the header correctly")
    print("   3. The header format is wrong (should be 'Bearer {token}')")
    print("   4. There's a timing issue - header gets cleared before request")
    
    print("\n5. Solution: Use direct HTTP call with explicit header")
    print("   This is what the HTTP fallback does, and it should work")
    print("   But we want the RPC client to work too")

if __name__ == "__main__":
    test_postgrest_direct()
