#!/usr/bin/env python3
"""Fix ALL incorrect company names in Supabase database."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using system environment variables only.")

from supabase import create_client

def fix_all_company_names():
    """Fix ALL incorrect company names in the database."""
    print("🔧 Fixing ALL Company Names in Supabase...")
    
    # Initialize Supabase client
    supabase = create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_ANON_KEY"]
    )
    
    print("✅ Connected to Supabase")
    
    # Define corrections: wrong_name -> correct_name
    corrections = {
        "XTM Inc": "iShares S&P/TSX Capped Materials Index ETF",
        "DRI Healthcare Trust": "ADF Group Inc.",
        "Veeva Systems Inc": "Vanguard FTSE Emerging Markets All Cap Index ETF",
        "Core & Main": "Citi Trends, Inc."
    }
    
    total_updated = 0
    
    for wrong_name, correct_name in corrections.items():
        print(f"\n🔍 Fixing: '{wrong_name}' → '{correct_name}'")
        
        # Find all positions with the wrong company name
        result = supabase.table("portfolio_positions") \
            .select("id, ticker, company, fund") \
            .eq("fund", "TEST") \
            .eq("company", wrong_name) \
            .execute()
        
        if result.data:
            print(f"   Found {len(result.data)} records to fix")
            
            # Update each record
            for record in result.data:
                try:
                    supabase.table("portfolio_positions") \
                        .update({"company": correct_name}) \
                        .eq("id", record["id"]) \
                        .execute()
                    total_updated += 1
                except Exception as e:
                    print(f"   ❌ Failed to update record {record['id']}: {e}")
            
            print(f"   ✅ Updated {len(result.data)} records")
        else:
            print(f"   No records found with wrong name")
    
    print(f"\n✅ Total records updated: {total_updated}")
    
    # Verify the changes
    print("\n🔍 Verifying changes...")
    for wrong_name in corrections.keys():
        result = supabase.table("portfolio_positions") \
            .select("id") \
            .eq("fund", "TEST") \
            .eq("company", wrong_name) \
            .execute()
        
        if result.data:
            print(f"   ❌ Still found {len(result.data)} records with '{wrong_name}'")
        else:
            print(f"   ✅ No more records with '{wrong_name}'")

if __name__ == "__main__":
    fix_all_company_names()
