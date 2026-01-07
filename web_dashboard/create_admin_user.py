#!/usr/bin/env python3
"""
Create an admin user and assign them to all funds
This bypasses the normal auth flow for initial setup
"""

import os
import requests
import uuid
from dotenv import load_dotenv

load_dotenv()

def create_admin_user():
    """Create an admin user and assign them to all funds"""
    
    # Get available funds first
    print("🔍 Getting available funds...")
    funds_response = requests.get(
        f"{os.getenv('SUPABASE_URL')}/rest/v1/portfolio_positions",
        headers={
            "apikey": os.getenv("SUPABASE_ANON_KEY"),
            "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
            "Content-Type": "application/json"
        },
        params={"select": "fund"}
    )
    
    if funds_response.status_code != 200:
        print(f"❌ Failed to get funds: {funds_response.text}")
        return False
    
    available_funds = list(set(row["fund"] for row in funds_response.json()))
    print(f"💰 Available funds: {available_funds}")
    
    if not available_funds:
        print("❌ No funds found. Run migration first.")
        return False
    
    # Create a test user ID (this would normally come from Supabase Auth)
    user_id = str(uuid.uuid4())
    user_email = "admin@tradingbot.com"
    
    print(f"👤 Creating admin user: {user_email}")
    
    # Create user profile (this will fail due to RLS, but let's try)
    user_data = {
        "user_id": user_id,
        "email": user_email,
        "full_name": "Admin User",
        "role": "admin"
    }
    
    try:
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/user_profiles",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json=user_data
        )
        
        if response.status_code == 201:
            print("✅ User profile created")
        else:
            print(f"⚠️ User profile creation failed (RLS): {response.text}")
            print("This is expected - RLS is blocking the insert")
    except Exception as e:
        print(f"⚠️ User profile creation failed: {e}")
    
    # Assign user to all funds
    print("🔗 Assigning user to all funds...")
    success_count = 0
    
    for fund in available_funds:
        try:
            fund_data = {
                "user_id": user_id,
                "fund_name": fund
            }
            
            response = requests.post(
                f"{os.getenv('SUPABASE_URL')}/rest/v1/user_funds",
                headers={
                    "apikey": os.getenv("SUPABASE_ANON_KEY"),
                    "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                    "Content-Type": "application/json"
                },
                json=fund_data
            )
            
            if response.status_code == 201:
                print(f"✅ Assigned {fund}")
                success_count += 1
            else:
                print(f"❌ Failed to assign {fund}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error assigning {fund}: {e}")
    
    if success_count > 0:
        print(f"\n🎉 Successfully assigned {success_count}/{len(available_funds)} funds")
        print(f"User ID: {user_id}")
        print(f"Email: {user_email}")
        print("\nNote: You'll need to authenticate as this user in the web app")
        return True
    else:
        print("\n❌ Failed to assign any funds")
        return False

if __name__ == "__main__":
    print("🔐 Creating Admin User and Fund Assignments")
    print("=" * 50)
    create_admin_user()
