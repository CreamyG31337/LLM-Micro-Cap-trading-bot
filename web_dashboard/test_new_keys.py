#!/usr/bin/env python3
"""
Test the new Supabase API keys
"""

import os
import requests
from dotenv import load_dotenv

# New API keys
NEW_ANON_KEY = "SUPABASE_PUBLISHABLE_KEY_REDACTED"
NEW_SERVICE_KEY = "SUPABASE_SECRET_KEY_REDACTED"

def test_anon_key():
    """Test the new anon key"""
    print("Testing new anon key...")
    
    url = "https://injqbxdqyxfvannygadt.supabase.co/rest/v1/portfolio_positions"
    headers = {
        "apikey": NEW_ANON_KEY,
        "Authorization": f"Bearer {NEW_ANON_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Records: {len(data)}")
            print("  Anon key works!")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def test_service_key():
    """Test the new service role key"""
    print("Testing new service role key...")
    
    url = "https://injqbxdqyxfvannygadt.supabase.co/rest/v1/portfolio_positions"
    headers = {
        "apikey": NEW_SERVICE_KEY,
        "Authorization": f"Bearer {NEW_SERVICE_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Records: {len(data)}")
            print("  Service key works!")
            return True
        else:
            print(f"  Error: {response.text}")
            return False
    except Exception as e:
        print(f"  Exception: {e}")
        return False

def update_env_file():
    """Update the .env file with new keys"""
    print("Updating .env file...")
    
    env_content = f"""SUPABASE_URL=https://injqbxdqyxfvannygadt.supabase.co
SUPABASE_ANON_KEY={NEW_ANON_KEY}
SUPABASE_SERVICE_ROLE_KEY={NEW_SERVICE_KEY}
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
FLASK_SECRET_KEY=your-flask-secret-key-change-this-in-production
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("  .env file updated!")
        return True
    except Exception as e:
        print(f"  Error updating .env: {e}")
        return False

if __name__ == "__main__":
    print("Testing New Supabase API Keys")
    print("=" * 40)
    
    # Test the keys
    anon_works = test_anon_key()
    service_works = test_service_key()
    
    if anon_works and service_works:
        print("\nBoth keys work! Updating configuration...")
        update_env_file()
        print("\nConfiguration updated successfully!")
        print("Next step: Update Vercel environment variables")
    else:
        print("\nSome keys failed. Please check the Supabase dashboard.")
