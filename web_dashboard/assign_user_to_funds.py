#!/usr/bin/env python3
"""
Quick script to assign your user to all available funds
"""
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def assign_user_to_funds(user_email, funds):
    """Assign user to multiple funds"""
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json"
    }
    
    for fund in funds:
        print(f"Assigning {user_email} to {fund}...")
        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/rpc/assign_fund_to_user",
            headers=headers,
            json={
                "user_email": user_email,
                "fund_name": fund
            }
        )
        
        if response.status_code == 200:
            print(f"  ✓ Success!")
        else:
            print(f"  ✗ Error: {response.text}")

if __name__ == "__main__":
    # Get your email
    user_email = input("Enter your email address: ")
    
    # Available funds
    funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
    
    print(f"\nAssigning {user_email} to all funds...")
    assign_user_to_funds(user_email, funds)
    print("\nDone!")
