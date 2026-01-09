#!/usr/bin/env python3
"""Test the actual user_preferences.set_user_preference function"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web_dashboard'))

from dotenv import load_dotenv
load_dotenv()

def test_user_preferences_function():
    """Test the actual set_user_preference function"""
    print("=" * 80)
    print("TESTING user_preferences.set_user_preference FUNCTION")
    print("=" * 80)
    
    # Simulate Flask request context
    from flask import Flask, request
    from user_preferences import set_user_preference, get_user_preference
    
    app = Flask(__name__)
    
    # Token from user
    token = "eyJhbGciOiJIUzI1NiIsImtpZCI6InAxeUFDbE1hcXpaRmlGVVIiLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2luanFieGRxeXhmdmFubnlnYWR0LnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiJjNGQ5YTk2Mi02YjZlLTQ2MDktYWQ4ZS03ZWUwYjM1ZWY2YTIiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzY3OTIxOTc2LCJpYXQiOjE3Njc5MTgzNzYsImVtYWlsIjoibGFuY2UuY29sdG9uQGdtYWlsLmNvbSIsInBob25lIjoiIiwiYXBwX21ldGFkYXRhIjp7InByb3ZpZGVyIjoiZW1haWwiLCJwcm92aWRlcnMiOlsiZW1haWwiXX0sInVzZXJfbWV0YWRhdGEiOnsiZW1haWwiOiJsYW5jZS5jb2x0b25AZ21haWwuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwic3ViIjoiYzRkOWE5NjItNmI2ZS00NjA5LWFkOGUtN2VlMGIzNWVmNmEyIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoicGFzc3dvcmQiLCJ0aW1lc3RhbXAiOjE3Njc4NjI4Nzl9XSwic2Vzc2lvbl9pZCI6Ijc4NWNjZTA0LTk3YjktNDRmZS05ZTlmLTYxMDkyOGZlZDk0OCIsImlzX2Fub255bW91cyI6ZmFsc2V9.nYgwj0JxAvcUd9sgp9RAeuNICuiFiAxM3En8-Bz3duM"
    
    with app.test_request_context(headers={'Cookie': f'auth_token={token}'}):
        print("\n1. Testing set_user_preference('test_key_func', 'test_value_func')...")
        result = set_user_preference('test_key_func', 'test_value_func')
        print(f"   Function returned: {result}")
        
        if result:
            print(f"   [SUCCESS] Function returned True!")
            
            print("\n2. Verifying value was saved...")
            read_back = get_user_preference('test_key_func')
            print(f"   Read back value: {repr(read_back)}")
            if read_back == 'test_value_func':
                print(f"   [SUCCESS] Value matches!")
            else:
                print(f"   [WARNING] Value mismatch! Expected 'test_value_func', got {repr(read_back)}")
        else:
            print(f"   [FAIL] Function returned False")
            print(f"   Check the logs above for error details")

if __name__ == "__main__":
    test_user_preferences_function()
