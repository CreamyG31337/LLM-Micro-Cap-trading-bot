#!/usr/bin/env python3
"""
Fix the corrupted database by clearing and re-migrating data
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def clear_database():
    """Clear all data from the database"""
    print("Clearing corrupted data...")
    
    # Clear all tables
    tables = ['portfolio_positions', 'trade_log', 'cash_balances', 'performance_metrics']
    
    for table in tables:
        try:
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/{table}"
            headers = {
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
                "Content-Type": "application/json"
            }
            
            # Delete all records
            response = requests.delete(url, headers=headers)
            print(f"  {table}: {response.status_code}")
            
        except Exception as e:
            print(f"  Error clearing {table}: {e}")

def verify_clean_database():
    """Verify the database is clean"""
    print("Verifying database is clean...")
    
    tables = ['portfolio_positions', 'trade_log', 'cash_balances']
    
    for table in tables:
        try:
            url = f"{os.getenv('SUPABASE_URL')}/rest/v1/{table}"
            headers = {
                "apikey": os.getenv("SUPABASE_ANON_KEY"),
                "Authorization": f"Bearer {os.getenv('SUPABASE_ANON_KEY')}",
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
    print("Database Fix Script")
    print("=" * 40)
    
    clear_database()
    verify_clean_database()
    
    print("\nDatabase cleared!")
    print("Next step: Re-run the migration script to populate with correct data")
