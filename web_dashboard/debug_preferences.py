#!/usr/bin/env python3
"""
Debug script for testing user preferences RPC calls
Run this to see what the RPC functions are actually returning
"""

import os
import sys
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add web_dashboard to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_preferences():
    """Test preference get/set functions"""
    try:
        from user_preferences import (
            get_user_preference,
            get_all_user_preferences,
            set_user_preference,
            get_user_timezone,
            get_user_currency,
            get_user_theme
        )
        from auth_utils import is_authenticated, get_user_email
        
        print("=" * 80)
        print("USER PREFERENCES DEBUG TEST")
        print("=" * 80)
        
        # Check authentication
        if not is_authenticated():
            print("ERROR: User not authenticated!")
            print("Attempting to use direct Supabase connection...")
            # Try to get token from environment or cookies
            try:
                import os
                from supabase_client import SupabaseClient
                # Try to create client without auth first
                client = SupabaseClient()
                print("Using Supabase client without explicit auth")
            except Exception as e:
                print(f"ERROR: Could not create Supabase client: {e}")
                print("Please run this from within a Streamlit session or provide auth token")
                return
        else:
            user_email = get_user_email()
            print(f"\nAuthenticated as: {user_email}")
        
        # Test 1: Get all preferences
        print("\n" + "=" * 80)
        print("TEST 1: get_all_user_preferences()")
        print("=" * 80)
        all_prefs = get_all_user_preferences()
        print(f"Result type: {type(all_prefs).__name__}")
        print(f"Result: {json.dumps(all_prefs, indent=2, default=str)}")
        
        # Test 2: Get individual preferences via get_user_preference
        print("\n" + "=" * 80)
        print("TEST 2: get_user_preference() for each key")
        print("=" * 80)
        
        test_keys = ['timezone', 'currency', 'theme', 'v2_enabled', 'ai_model', 'selected_fund']
        
        for key in test_keys:
            print(f"\n--- Testing key: '{key}' ---")
            value = get_user_preference(key, default=None)
            print(f"  Result: {repr(value)}")
            print(f"  Type: {type(value).__name__}")
            
            # Compare with all_prefs
            if isinstance(all_prefs, dict) and key in all_prefs:
                all_prefs_value = all_prefs[key]
                print(f"  From get_all_user_preferences(): {repr(all_prefs_value)} (type: {type(all_prefs_value).__name__})")
                if value != all_prefs_value:
                    print(f"  WARNING: MISMATCH! Values don't match!")
            else:
                print(f"  WARNING: Key not found in get_all_user_preferences()")
        
        # Test 3: Test helper functions
        print("\n" + "=" * 80)
        print("TEST 3: Helper functions")
        print("=" * 80)
        
        timezone = get_user_timezone()
        print(f"get_user_timezone(): {repr(timezone)} (type: {type(timezone).__name__})")
        
        currency = get_user_currency()
        print(f"get_user_currency(): {repr(currency)} (type: {type(currency).__name__})")
        
        theme = get_user_theme()
        print(f"get_user_theme(): {repr(theme)} (type: {type(theme).__name__})")
        
        # Test 4: Direct RPC call to see raw response
        print("\n" + "=" * 80)
        print("TEST 4: Direct RPC call (raw response)")
        print("=" * 80)
        
        try:
            from streamlit_utils import get_supabase_client
            from auth_utils import get_user_token
            
            user_token = get_user_token()
            client = get_supabase_client(user_token=user_token)
            
            for key in ['timezone', 'v2_enabled']:
                print(f"\n--- Direct RPC call for '{key}' ---")
                result = client.supabase.rpc('get_user_preference', {'pref_key': key}).execute()
                print(f"  result.data: {repr(result.data)}")
                print(f"  result.data type: {type(result.data).__name__}")
                if isinstance(result.data, list):
                    print(f"  result.data[0]: {repr(result.data[0]) if len(result.data) > 0 else 'empty list'}")
                    if len(result.data) > 0:
                        print(f"  result.data[0] type: {type(result.data[0]).__name__}")
        except Exception as e:
            print(f"  ERROR: Error calling RPC directly: {e}")
            import traceback
            traceback.print_exc()
        
        # Test 5: Test setting a preference
        print("\n" + "=" * 80)
        print("TEST 5: Test setting a preference")
        print("=" * 80)
        
        test_value = "test_value_from_debug_script"
        print(f"Attempting to set 'test_key' = '{test_value}'")
        result = set_user_preference('test_key', test_value)
        print(f"set_user_preference returned: {result} (type: {type(result).__name__})")
        
        if result:
            # Try to read it back
            read_back = get_user_preference('test_key')
            print(f"Read back value: {repr(read_back)}")
            if read_back == test_value:
                print("SUCCESS: Set and read back successful!")
            else:
                print(f"WARNING: Value mismatch! Expected '{test_value}', got {repr(read_back)}")
        else:
            print("ERROR: Failed to set preference - check logs above for error details")
        
        print("\n" + "=" * 80)
        print("DEBUG TEST COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_preferences()
