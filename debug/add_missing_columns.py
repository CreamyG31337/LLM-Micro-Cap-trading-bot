#!/usr/bin/env python3
"""
Add missing columns to Supabase database
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
load_dotenv('web_dashboard/.env')

from display.console_output import print_success, print_error, print_info

def add_missing_columns():
    """Add missing columns to Supabase database"""
    print_info("🔧 Adding missing columns to Supabase database...")
    
    # Check Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not supabase_key:
        print_error("❌ Missing Supabase credentials")
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        print_success("✅ Connected to Supabase")
        
        # Add current_price column to portfolio_positions
        print_info("📋 Adding current_price column to portfolio_positions...")
        try:
            supabase.rpc('execute_sql', {
                'sql_query': 'ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS current_price DECIMAL(10, 2) DEFAULT NULL;'
            }).execute()
            print_success("✅ Added current_price column")
        except Exception as e:
            print_error(f"❌ Failed to add current_price column: {e}")
            return False
        
        # Add avg_price column to portfolio_positions
        print_info("📋 Adding avg_price column to portfolio_positions...")
        try:
            supabase.rpc('execute_sql', {
                'sql_query': 'ALTER TABLE portfolio_positions ADD COLUMN IF NOT EXISTS avg_price DECIMAL(10, 2) GENERATED ALWAYS AS (cost_basis / NULLIF(shares, 0)) STORED;'
            }).execute()
            print_success("✅ Added avg_price column")
        except Exception as e:
            print_error(f"❌ Failed to add avg_price column: {e}")
            return False
        
        print_success("✅ All missing columns added successfully!")
        return True
        
    except Exception as e:
        print_error(f"❌ Failed to add missing columns: {e}")
        return False

if __name__ == "__main__":
    if add_missing_columns():
        print_success("\n🎉 Database schema updated successfully!")
    else:
        print_error("\n❌ Database schema update failed!")
