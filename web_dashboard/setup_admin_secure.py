#!/usr/bin/env python3
"""
Secure admin setup script - uses environment variables
No hardcoded emails or passwords
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def setup_admin_from_env():
    """Setup admin using environment variables"""
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    admin_name = os.getenv("ADMIN_NAME", "Admin User")
    
    if not admin_email:
        print("❌ ADMIN_EMAIL environment variable not set")
        print("💡 Add ADMIN_EMAIL=your-email@example.com to your .env file")
        return False
    
    if not admin_password:
        print("❌ ADMIN_PASSWORD environment variable not set")
        print("💡 Add ADMIN_PASSWORD=your-secure-password to your .env file")
        return False
    
    print(f"🔧 Setting up admin: {admin_email}")
    
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        return False
    
    try:
        # Check if user already exists
        response = requests.get(
            f"{url}/rest/v1/user_profiles",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            params={"email": f"eq.{admin_email}"}
        )
        
        if response.status_code == 200 and response.json():
            print(f"✅ User {admin_email} already exists")
            user_id = response.json()[0]['user_id']
        else:
            # Create user
            print(f"👤 Creating user: {admin_email}")
            create_response = requests.post(
                f"{url}/auth/v1/signup",
                headers={
                    "apikey": key,
                    "Content-Type": "application/json"
                },
                json={
                    "email": admin_email,
                    "password": admin_password,
                    "user_metadata": {
                        "full_name": admin_name
                    }
                }
            )
            
            if create_response.status_code != 200:
                print(f"❌ Error creating user: {create_response.text}")
                return False
            
            user_data = create_response.json()
            user_id = user_data["id"]
            print(f"✅ User created: {user_id}")
        
        # Make user admin
        print(f"👑 Making {admin_email} an admin...")
        admin_response = requests.patch(
            f"{url}/rest/v1/user_profiles",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            params={"user_id": f"eq.{user_id}"},
            json={"role": "admin"}
        )
        
        if admin_response.status_code not in [200, 204]:
            print(f"❌ Error making user admin: {admin_response.text}")
            return False
        
        print(f"✅ {admin_email} is now an admin!")
        
        # Assign all funds
        print(f"💰 Assigning funds to {admin_email}...")
        funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
        
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
            
            if fund_response.status_code in [200, 201]:
                print(f"  ✅ Assigned {fund}")
            elif "duplicate key value violates unique constraint" in fund_response.text:
                print(f"  ⚠️  {fund} already assigned")
            else:
                print(f"  ❌ Error assigning {fund}: {fund_response.text}")
        
        print("\n🎉 Admin setup complete!")
        print(f"📧 Admin email: {admin_email}")
        print("🔗 Admin dashboard: https://webdashboard-hazel.vercel.app/admin")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔐 Secure Admin Setup")
    print("=" * 30)
    print("💡 This script uses environment variables from .env file")
    print("💡 Make sure ADMIN_EMAIL and ADMIN_PASSWORD are set")
    print("=" * 30)
    
    setup_admin_from_env()
