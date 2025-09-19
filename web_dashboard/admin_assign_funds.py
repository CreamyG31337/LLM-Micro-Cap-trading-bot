#!/usr/bin/env python3
"""
Admin script to assign funds to users
Run this after users register to give them access to specific funds
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def assign_fund_to_user(user_email: str, fund_name: str):
    """Assign a fund to a user"""
    try:
        # First, get the user ID by email
        response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/user_profiles",
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
        
        user_id = response.json()[0]["user_id"]
        
        # Assign the fund
        response = requests.post(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/user_funds",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "user_id": user_id,
                "fund_name": fund_name
            }
        )
        
        if response.status_code == 201:
            print(f"✅ Assigned {fund_name} to {user_email}")
            return True
        else:
            print(f"❌ Failed to assign {fund_name} to {user_email}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error assigning fund: {e}")
        return False

def list_users():
    """List all registered users"""
    try:
        response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/user_profiles",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            users = response.json()
            print("📋 Registered Users:")
            for user in users:
                print(f"  - {user['email']} ({user.get('full_name', 'No name')})")
            return users
        else:
            print(f"❌ Failed to get users: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return []

def list_funds():
    """List all available funds"""
    try:
        response = requests.get(
            f"{os.getenv('SUPABASE_URL')}/rest/v1/portfolio_positions",
            headers={
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            },
            params={"select": "fund"}
        )
        
        if response.status_code == 200:
            funds = list(set(row["fund"] for row in response.json()))
            print("💰 Available Funds:")
            for fund in sorted(funds):
                print(f"  - {fund}")
            return funds
        else:
            print(f"❌ Failed to get funds: {response.text}")
            return []
    except Exception as e:
        print(f"❌ Error getting funds: {e}")
        return []

if __name__ == "__main__":
    print("🔐 Portfolio Dashboard - Fund Assignment Admin")
    print("=" * 50)
    
    # List users and funds
    users = list_users()
    funds = list_funds()
    
    if not users:
        print("\n❌ No users found. Users need to register first.")
        exit(1)
    
    if not funds:
        print("\n❌ No funds found. Run migration first.")
        exit(1)
    
    print(f"\n📝 To assign funds to users, run:")
    print(f"python admin_assign_funds.py assign <user_email> <fund_name>")
    print(f"\nExample:")
    print(f"python admin_assign_funds.py assign user@example.com 'Project Chimera'")
    print(f"python admin_assign_funds.py assign user@example.com 'RRSP Lance Webull'")
    
    # Check for command line arguments
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "assign":
        user_email = sys.argv[2]
        fund_name = sys.argv[3]
        assign_fund_to_user(user_email, fund_name)
