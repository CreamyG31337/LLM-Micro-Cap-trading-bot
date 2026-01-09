#!/usr/bin/env python3
"""Inspect postgrest client structure to see how to set auth header"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

def inspect_postgrest():
    """Inspect the postgrest client structure"""
    print("=" * 80)
    print("INSPECTING POSTGREST CLIENT STRUCTURE")
    print("=" * 80)
    
    try:
        from supabase_client import SupabaseClient
        
        # Create client without token first
        print("\n1. Creating SupabaseClient without token...")
        client = SupabaseClient()
        
        if hasattr(client, 'supabase'):
            print("   [OK] client.supabase exists")
            supabase = client.supabase
            
            if hasattr(supabase, 'postgrest'):
                print("   [OK] client.supabase.postgrest exists")
                postgrest = supabase.postgrest
                
                print(f"\n2. Postgrest type: {type(postgrest)}")
                print(f"   Postgrest attributes: {[a for a in dir(postgrest) if not a.startswith('_')]}")
                
                # Check for session
                if hasattr(postgrest, 'session'):
                    print(f"\n3. postgrest.session exists")
                    session = postgrest.session
                    print(f"   Session type: {type(session)}")
                    print(f"   Session attributes: {[a for a in dir(session) if not a.startswith('_')]}")
                    
                    if hasattr(session, 'headers'):
                        print(f"   [OK] session.headers exists")
                        headers = session.headers
                        print(f"   Headers type: {type(headers)}")
                        print(f"   Current headers: {dict(headers) if isinstance(headers, dict) else 'Not a dict'}")
                    else:
                        print(f"   [FAIL] session.headers does NOT exist")
                else:
                    print(f"\n3. postgrest.session does NOT exist")
                
                # Check for auth method
                if hasattr(postgrest, 'auth'):
                    print(f"\n4. postgrest.auth() method exists")
                    print(f"   auth type: {type(postgrest.auth)}")
                    if callable(postgrest.auth):
                        print(f"   auth is callable")
                    else:
                        print(f"   auth is NOT callable (it's a property)")
                else:
                    print(f"\n4. postgrest.auth() method does NOT exist")
                
                # Check for _client
                if hasattr(postgrest, '_client'):
                    print(f"\n5. postgrest._client exists")
                    _client = postgrest._client
                    print(f"   _client type: {type(_client)}")
                    print(f"   _client attributes: {[a for a in dir(_client) if not a.startswith('__')][:20]}")
                else:
                    print(f"\n5. postgrest._client does NOT exist")
                
                # Try to see how RPC calls work
                print(f"\n6. Testing RPC call structure...")
                try:
                    # Just inspect, don't actually call
                    rpc_method = getattr(supabase, 'rpc', None)
                    if rpc_method:
                        print(f"   supabase.rpc exists: {type(rpc_method)}")
                        # See if we can inspect how it sets headers
                        print(f"   This is how RPC calls are made")
                except Exception as e:
                    print(f"   Error inspecting RPC: {e}")
                
            else:
                print("   [FAIL] client.supabase.postgrest does NOT exist")
        else:
            print("   [FAIL] client.supabase does NOT exist")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_postgrest()
