#!/usr/bin/env python3
"""
Clean the corrupted database using service role key to bypass RLS
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# Service role key from environment variable (bypasses RLS)
SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

def clean_database():
    """Clean all corrupted data using service role key"""
    if not SERVICE_ROLE_KEY:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY environment variable not set!")
        print("Please add it to your .env file:")
        print("SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here")
        return
    
    print("Cleaning corrupted database with service role key...")
    
    # Tables to clean
    tables = ['portfolio_positions', 'trade_log', 'cash_balances', 'performance_metrics']
    
    for table in tables:
        try:
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/{table}"
            headers = {
                "apikey": SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
                "Content-Type": "application/json"
            }
            
            # Delete all records (WHERE clause required)
            response = requests.delete(url + "?id=not.is.null", headers=headers)
            print(f"  {table}: {response.status_code}")
            
            if response.status_code == 204:
                print(f"    Successfully cleared {table}")
            else:
                print(f"    Error clearing {table}: {response.text}")
                
        except Exception as e:
            print(f"  Error clearing {table}: {e}")

def verify_clean_database():
    """Verify the database is clean"""
    print("\nVerifying database is clean...")
    
    tables = ['portfolio_positions', 'trade_log', 'cash_balances']
    
    for table in tables:
        try:
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/{table}"
            headers = {
                "apikey": SERVICE_ROLE_KEY,
                "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"  {table}: {len(data)} records")
            else:
                print(f"  {table}: Error {response.status_code}")
                
        except Exception as e:
            print(f"  Error checking {table}: {e}")

if __name__ == "__main__":
    print("Database Cleanup with Service Role")
    print("=" * 40)
    
    clean_database()
    verify_clean_database()
    
    print("\nDatabase cleaned! Now run the clean migration script.")
