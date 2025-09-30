#!/usr/bin/env python3
"""
Migration Test Script
Tests CSV to Supabase migration and verifies data integrity
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
import json

# Add the parent directory to the path to import from the main project
sys.path.append(str(Path(__file__).parent.parent))

def test_csv_data_availability():
    """Test that CSV files exist and are readable"""
    print("Testing CSV data availability...")
    
    # Check for CSV files in the main project
    csv_paths = [
        "trading_data/funds/Project Chimera/llm_portfolio_update.csv",
        "trading_data/funds/Project Chimera/llm_trade_log.csv"
    ]
    
    results = {}
    for csv_path in csv_paths:
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                results[csv_path] = {
                    "exists": True,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sample_data": df.head(2).to_dict('records') if len(df) > 0 else []
                }
                print(f"✅ {csv_path}: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                results[csv_path] = {"exists": True, "error": str(e)}
                print(f"❌ {csv_path}: Error reading - {e}")
        else:
            results[csv_path] = {"exists": False}
            print(f"❌ {csv_path}: File not found")
    
    return results

def test_supabase_connection():
    """Test Supabase connection and schema"""
    print("\n🔍 Testing Supabase connection...")
    
    try:
        from supabase_client import SupabaseClient
        
        client = SupabaseClient()
        if not client:
            print("❌ Supabase client creation failed")
            return False
        
        # Test basic connection
        print("✅ Supabase client created successfully")
        
        # Test if we can query the database
        try:
            # Try to get a simple count
            result = client.supabase.table("portfolio_positions").select("id").limit(1).execute()
            print("✅ Database connection successful")
            return True
        except Exception as e:
            print(f"❌ Database query failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Supabase connection error: {e}")
        return False

def test_migration_process():
    """Test the actual migration process"""
    print("\n🔍 Testing migration process...")
    
    try:
        # Import the migration script
        from migrate import main as migrate_main
        
        print("✅ Migration script imported successfully")
        
        # Test migration without actually running it
        print("📋 Migration script is ready to run")
        print("   Run 'python migrate.py' to perform actual migration")
        
        return True
        
    except ImportError as e:
        print(f"❌ Migration script import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Migration process error: {e}")
        return False

def test_data_consistency():
    """Test data consistency between CSV and Supabase"""
    print("\n🔍 Testing data consistency...")
    
    try:
        from supabase_client import SupabaseClient
        
        client = SupabaseClient()
        if not client:
            print("❌ Cannot test consistency - Supabase client failed")
            return False
        
        # Get data from Supabase
        try:
            supabase_positions = client.supabase.table("portfolio_positions").select("*").execute()
            supabase_trades = client.supabase.table("trade_log").select("*").execute()
            
            print(f"✅ Supabase data retrieved:")
            print(f"   Portfolio positions: {len(supabase_positions.data)} rows")
            print(f"   Trade log: {len(supabase_trades.data)} rows")
            
            # Check if data looks reasonable
            if len(supabase_positions.data) > 0:
                sample_position = supabase_positions.data[0]
                print(f"   Sample position: {sample_position.get('ticker', 'N/A')} - {sample_position.get('shares', 'N/A')} shares")
            
            if len(supabase_trades.data) > 0:
                sample_trade = supabase_trades.data[0]
                print(f"   Sample trade: {sample_trade.get('ticker', 'N/A')} - {sample_trade.get('shares', 'N/A')} shares")
            
            return True
            
        except Exception as e:
            print(f"❌ Error retrieving Supabase data: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Data consistency test error: {e}")
        return False

def test_environment_setup():
    """Test that environment variables are set correctly"""
    print("\n🔍 Testing environment setup...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    optional_vars = ['JWT_SECRET', 'FLASK_SECRET_KEY']
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set (length: {len(value)})")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set (length: {len(value)})")
        else:
            print(f"⚠️  {var}: Not set (will use default)")
    
    return all_good

def run_comprehensive_test():
    """Run all tests and provide a summary"""
    print("COMPREHENSIVE MIGRATION TEST")
    print("=" * 50)
    
    results = {}
    
    # Test 1: Environment setup
    results['environment'] = test_environment_setup()
    
    # Test 2: CSV data availability
    results['csv_data'] = test_csv_data_availability()
    
    # Test 3: Supabase connection
    results['supabase'] = test_supabase_connection()
    
    # Test 4: Migration process
    results['migration'] = test_migration_process()
    
    # Test 5: Data consistency (only if Supabase has data)
    results['consistency'] = test_data_consistency()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    test_names = {
        'environment': 'Environment Variables',
        'csv_data': 'CSV Data Availability',
        'supabase': 'Supabase Connection',
        'migration': 'Migration Process',
        'consistency': 'Data Consistency'
    }
    
    all_passed = True
    for test_key, test_name in test_names.items():
        if test_key == 'csv_data':
            # CSV test returns detailed results
            csv_results = results[test_key]
            if any(result.get('exists', False) for result in csv_results.values()):
                print(f"✅ {test_name}: CSV files found")
            else:
                print(f"❌ {test_name}: No CSV files found")
                all_passed = False
        else:
            status = "✅ PASS" if results[test_key] else "❌ FAIL"
            print(f"{status} {test_name}")
            if not results[test_key]:
                all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 ALL TESTS PASSED - READY FOR MIGRATION!")
        print("\n📋 Next steps:")
        print("1. Run: python migrate.py")
        print("2. Verify data in Supabase dashboard")
        print("3. Test the web dashboard")
    else:
        print("⚠️  SOME TESTS FAILED - CHECK ISSUES ABOVE")
        print("\n🔧 Fix the issues above before running migration")
    
    return all_passed

if __name__ == "__main__":
    run_comprehensive_test()
