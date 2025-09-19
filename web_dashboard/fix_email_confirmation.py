#!/usr/bin/env python3
"""
Fix email confirmation by updating Supabase settings
or manually confirming users
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def update_supabase_settings():
    """Update Supabase auth settings to use production URL"""
    print("🔧 Updating Supabase auth settings...")
    
    # This would require admin API access, which we don't have
    # So we'll provide instructions instead
    print("""
    📋 Manual Steps Required:
    
    1. Go to your Supabase project dashboard
    2. Navigate to Authentication → Settings
    3. Update these settings:
       - Site URL: https://webdashboard-hazel.vercel.app
       - Redirect URLs: https://webdashboard-hazel.vercel.app/**
    4. Save changes
    
    This will fix the email confirmation links to point to your production URL.
    """)

def create_test_user_without_confirmation():
    """Create a test user that bypasses email confirmation"""
    print("\n🧪 Creating test user without email confirmation...")
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    # Try to create a user with a confirmed email directly
    test_email = "testuser@example.com"
    test_password = "testpassword123"
    
    try:
        # First, try to register
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
                    "full_name": "Test User"
                }
            }
        )
        
        print(f"Registration status: {response.status_code}")
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data["id"]
            print(f"✅ User created: {user_id}")
            
            # Now try to assign funds
            print("\n💰 Assigning funds to test user...")
            funds = ["Project Chimera", "RRSP Lance Webull", "TFSA"]
            
            for fund in funds:
                fund_response = requests.post(
                    f"{url}/rest/v1/user_funds",
                    headers={
                        "apikey": key,
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "user_id": user_id,
                        "fund_name": fund
                    }
                )
                print(f"  {fund}: {fund_response.status_code}")
            
            print(f"\n✅ Test user setup complete!")
            print(f"Email: {test_email}")
            print(f"Password: {test_password}")
            print("\n⚠️  Note: You may still need to confirm the email in Supabase dashboard")
            
        else:
            print(f"❌ Registration failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def disable_email_confirmation_instructions():
    """Provide instructions to disable email confirmation"""
    print("""
    🚫 Disable Email Confirmation (Quick Fix):
    
    1. Go to your Supabase project dashboard
    2. Navigate to Authentication → Settings
    3. Under "Email" section, find "Enable email confirmations"
    4. Toggle it OFF
    5. Save changes
    
    This will allow users to login immediately after registration.
    """)

if __name__ == "__main__":
    print("🔐 Email Confirmation Fix Tool")
    print("=" * 40)
    
    print("\n🎯 The issue: Email confirmation links point to localhost")
    print("🎯 The solution: Update Supabase settings to use your production URL")
    
    update_supabase_settings()
    disable_email_confirmation_instructions()
    
    print("\n" + "=" * 40)
    print("📋 Choose one of the above solutions")
    print("💡 Recommended: Update Site URL in Supabase settings")
