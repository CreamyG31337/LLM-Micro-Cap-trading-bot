#!/usr/bin/env python3
"""
Test script to debug authentication issues
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_supabase_connection():
    """Test basic Supabase connection"""
    print("🔍 Testing Supabase connection...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    if not url or not key:
        print("❌ Missing SUPABASE_URL or SUPABASE_ANON_KEY")
        return False
    
    print(f"✅ URL: {url}")
    print(f"✅ Key: {key[:20]}...")
    
    # Test basic connection
    try:
        response = requests.get(
            f"{url}/rest/v1/",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}"
            }
        )
        print(f"✅ Connection test: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_auth_endpoints():
    """Test Supabase auth endpoints"""
    print("\n🔍 Testing Supabase auth endpoints...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    # Test auth endpoint
    try:
        response = requests.get(
            f"{url}/auth/v1/settings",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}"
            }
        )
        print(f"✅ Auth settings: {response.status_code}")
        if response.status_code == 200:
            settings = response.json()
            print(f"   - External email enabled: {settings.get('external', {}).get('email', {}).get('enabled', False)}")
            print(f"   - Email confirm enabled: {settings.get('email', {}).get('enable_signup', False)}")
    except Exception as e:
        print(f"❌ Auth settings failed: {e}")

def test_user_registration():
    """Test user registration"""
    print("\n🔍 Testing user registration...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    test_email = "test@example.com"
    test_password = "testpassword123"
    test_name = "Test User"
    
    try:
        response = requests.post(
            f"{url}/auth/v1/signup",
            headers={
                "apikey": key,
                "Content-Type": "application/json"
            },
            json={
                "email": test_email,
                "password": test_password,
                "user_metadata": {
                    "full_name": test_name
                }
            }
        )
        
        print(f"✅ Registration test: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - User ID: {data.get('user', {}).get('id', 'N/A')}")
            print(f"   - Email: {data.get('user', {}).get('email', 'N/A')}")
            return data.get('user', {}).get('id')
        else:
            print(f"   - Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return None

def test_user_login():
    """Test user login"""
    print("\n🔍 Testing user login...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    test_email = "test@example.com"
    test_password = "testpassword123"
    
    try:
        response = requests.post(
            f"{url}/auth/v1/token?grant_type=password",
            headers={
                "apikey": key,
                "Content-Type": "application/json"
            },
            json={
                "email": test_email,
                "password": test_password
            }
        )
        
        print(f"✅ Login test: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   - Access token: {data.get('access_token', 'N/A')[:20]}...")
            print(f"   - User ID: {data.get('user', {}).get('id', 'N/A')}")
            return data.get('access_token')
        else:
            print(f"   - Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return None

def test_database_schema():
    """Test if database schema exists"""
    print("\n🔍 Testing database schema...")
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    
    tables = ["user_profiles", "user_funds", "portfolio_positions", "trade_log"]
    
    for table in tables:
        try:
            response = requests.get(
                f"{url}/rest/v1/{table}",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}"
                },
                params={"select": "id", "limit": "1"}
            )
            print(f"✅ Table {table}: {response.status_code}")
        except Exception as e:
            print(f"❌ Table {table} failed: {e}")

if __name__ == "__main__":
    print("🧪 Portfolio Dashboard - Authentication Test")
    print("=" * 50)
    
    # Test connection
    if not test_supabase_connection():
        print("\n❌ Cannot proceed - Supabase connection failed")
        exit(1)
    
    # Test auth endpoints
    test_auth_endpoints()
    
    # Test database schema
    test_database_schema()
    
    # Test registration
    user_id = test_user_registration()
    
    # Test login
    if user_id:
        test_user_login()
    
    print("\n🎯 Test complete!")
    print("\nIf any tests failed, check:")
    print("1. Supabase project is active")
    print("2. Database schema is created (run schema/00_complete_setup.sql)")
    print("3. Environment variables are correct")
    print("4. Supabase auth is enabled in project settings")
