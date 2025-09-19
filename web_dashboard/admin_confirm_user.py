#!/usr/bin/env python3
"""
Admin script to manually confirm users for testing
This bypasses email confirmation for development
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def confirm_user_email(user_email: str):
    """Manually confirm a user's email"""
    try:
        # First, get the user ID by email
        response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/auth.users",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            params={"email": f"eq.{user_email}"}
        )
        
        if response.status_code != 200 or not response.json():
            print(f"❌ User {user_email} not found")
            return False
        
        user_data = response.json()[0]
        user_id = user_data["id"]
        
        # Update user to confirm email
        update_response = requests.patch(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/auth.users",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "email_confirmed_at": "2025-09-19T10:00:00Z",
                "email_verified": True
            },
            params={"id": f"eq.{user_id}"}
        )
        
        if update_response.status_code == 200:
            print(f"✅ Email confirmed for {user_email}")
            return True
        else:
            print(f"❌ Failed to confirm email: {update_response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error confirming user: {e}")
        return False

def list_unconfirmed_users():
    """List users with unconfirmed emails"""
    try:
        response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/auth.users",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            users = response.json()
            unconfirmed = [u for u in users if not u.get("email_confirmed_at")]
            print("📋 Unconfirmed Users:")
            for user in unconfirmed:
                print(f"  - {user['email']} (ID: {user['id']})")
            return unconfirmed
        else:
            print(f"❌ Failed to get users: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return []

if __name__ == "__main__":
    print("🔐 Portfolio Dashboard - User Confirmation Admin")
    print("=" * 50)
    
    # List unconfirmed users
    unconfirmed = list_unconfirmed_users()
    
    if not unconfirmed:
        print("✅ All users are confirmed!")
        exit(0)
    
    print(f"\n📝 To confirm a user, run:")
    print(f"python admin_confirm_user.py confirm <user_email>")
    print(f"\nExample:")
    print(f"python admin_confirm_user.py confirm testuser123@gmail.com")
    
    # Check for command line arguments
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "confirm":
        user_email = sys.argv[2]
        confirm_user_email(user_email)
