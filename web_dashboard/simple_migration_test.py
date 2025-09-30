#!/usr/bin/env python3
"""
Simple Migration Test
Tests CSV to Supabase migration without emojis for Windows compatibility
"""

import os
import sys
import pandas as pd
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent))

def test_csv_files():
    """Test that CSV files exist"""
    print("Testing CSV files...")
    
    csv_files = [
        "trading_data/funds/Project Chimera/llm_portfolio_update.csv",
        "trading_data/funds/Project Chimera/llm_trade_log.csv"
    ]
    
    found_files = 0
    for csv_file in csv_files:
        if os.path.exists(csv_file):
            try:
                df = pd.read_csv(csv_file)
                print(f"  OK: {csv_file} - {len(df)} rows")
                found_files += 1
            except Exception as e:
                print(f"  ERROR: {csv_file} - {e}")
        else:
            print(f"  MISSING: {csv_file}")
    
    return found_files > 0

def test_environment():
    """Test environment variables"""
    print("Testing environment variables...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  OK: {var} is set")
        else:
            print(f"  MISSING: {var}")
            all_good = False
    
    return all_good

def test_supabase_connection():
    """Test Supabase connection"""
    print("Testing Supabase connection...")
    
    try:
        from supabase_client import SupabaseClient
        
        client = SupabaseClient()
        if not client:
            print("  ERROR: Supabase client creation failed")
            return False
        
        # Test basic query
        result = client.supabase.table("portfolio_positions").select("id").limit(1).execute()
        print("  OK: Supabase connection successful")
        return True
        
    except Exception as e:
        print(f"  ERROR: Supabase connection failed - {e}")
        return False

def test_migration_script():
    """Test that migration script exists and can be imported"""
    print("Testing migration script...")
    
    try:
        import migrate
        print("  OK: Migration script can be imported")
        return True
    except Exception as e:
        print(f"  ERROR: Migration script import failed - {e}")
        return False

def main():
    """Run all tests"""
    print("MIGRATION TEST")
    print("=" * 40)
    
    tests = [
        ("CSV Files", test_csv_files),
        ("Environment", test_environment),
        ("Supabase Connection", test_supabase_connection),
        ("Migration Script", test_migration_script)
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        results[test_name] = test_func()
    
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    
    all_passed = True
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\nALL TESTS PASSED - Ready for migration!")
        print("Next steps:")
        print("1. Run: python migrate.py")
        print("2. Run: python verify_migration.py")
    else:
        print("\nSOME TESTS FAILED - Fix issues above")
    
    return all_passed

if __name__ == "__main__":
    main()
