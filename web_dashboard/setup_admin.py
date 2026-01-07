#!/usr/bin/env python3
"""
Setup admin user and assign funds
Uses SERVICE_ROLE_KEY to bypass RLS
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SERVICE_ROLE_KEY:
    print("❌ Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    print("Add them to your .env file")
    sys.exit(1)

# Create client with service role key (bypasses RLS)
supabase: Client = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

def make_user_admin(email: str):
    """Make a user an admin"""
    try:
        # Get user by email
        result = supabase.table("user_profiles").select("*").eq("email", email).execute()
        
        if not result.data:
            print(f"❌ User {email} not found")
            print("Make sure they've logged in at least once")
            return False
        
        user_profile = result.data[0]
        
        # Update role to admin
        supabase.table("user_profiles").update({"role": "admin"}).eq("email", email).execute()
        print(f"✅ {email} is now an admin!")
        return True
        
    except Exception as e:
        print(f"❌ Error making user admin: {e}")
        return False

def assign_all_funds(email: str):
    """Assign all available funds to a user"""
    try:
        # Get user ID
        result = supabase.table("user_profiles").select("user_id").eq("email", email).execute()
        
        if not result.data:
            print(f"❌ User {email} not found")
            return False
        
        user_id = result.data[0]["user_id"]
        
        # Get all available funds from portfolio_positions
        funds_result = supabase.table("portfolio_positions").select("fund").execute()
        funds = list(set([row["fund"] for row in funds_result.data if row.get("fund")]))
        
        if not funds:
            print("⚠️  No funds found in database")
            funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
            print(f"   Using default funds: {funds}")
        
        # Assign each fund
        for fund in funds:
            try:
                # Check if already assigned
                existing = supabase.table("user_funds").select("*").eq("user_id", user_id).eq("fund_name", fund).execute()
                
                if existing.data:
                    print(f"   ⏭️  {fund} - already assigned")
                else:
                    supabase.table("user_funds").insert({
                        "user_id": user_id,
                        "fund_name": fund
                    }).execute()
                    print(f"   ✅ {fund} - assigned")
                    
            except Exception as e:
                print(f"   ❌ {fund} - error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error assigning funds: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ADMIN SETUP SCRIPT")
    print("=" * 60)
    
    email = input("\nEnter your email address: ").strip()
    
    if not email:
        print("❌ Email is required")
        sys.exit(1)
    
    print(f"\nSetting up admin for: {email}")
    print("-" * 60)
    
    # Make admin
    print("\n1. Making user admin...")
    if make_user_admin(email):
        # Assign funds
        print("\n2. Assigning all funds...")
        assign_all_funds(email)
    
    print("\n" + "=" * 60)
    print("DONE! You can now log in and access all features.")
    print("=" * 60)
