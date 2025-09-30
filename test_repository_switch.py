#!/usr/bin/env python3
"""
Test Repository Switch
Demonstrates switching between CSV and Supabase repositories
"""

import os
import sys
from pathlib import Path

def test_csv_repository():
    """Test CSV repository."""
    print("🧪 Testing CSV Repository")
    print("-" * 30)
    
    try:
        from data.repositories.repository_factory import RepositoryFactory
        
        # Create CSV repository
        repository = RepositoryFactory.create_repository(
            "csv", 
            data_directory="trading_data/funds/Project Chimera"
        )
        
        print(f"✅ CSV Repository created: {type(repository).__name__}")
        
        # Test basic operations
        print("   Testing portfolio data retrieval...")
        portfolio_data = repository.get_portfolio_data()
        print(f"   Found {len(portfolio_data)} portfolio snapshots")
        
        print("   Testing trade history retrieval...")
        trade_data = repository.get_trade_history()
        print(f"   Found {len(trade_data)} trades")
        
        print("✅ CSV Repository test passed")
        return True
        
    except Exception as e:
        print(f"❌ CSV Repository test failed: {e}")
        return False

def test_supabase_repository():
    """Test Supabase repository."""
    print("\n🧪 Testing Supabase Repository")
    print("-" * 30)
    
    try:
        from data.repositories.repository_factory import RepositoryFactory
        
        # Check environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            print("❌ Supabase environment variables not set")
            print("   Set SUPABASE_URL and SUPABASE_ANON_KEY")
            return False
        
        # Create Supabase repository
        repository = RepositoryFactory.create_repository(
            "supabase",
            supabase_url=supabase_url,
            supabase_key=supabase_key
        )
        
        print(f"✅ Supabase Repository created: {type(repository).__name__}")
        
        # Test basic operations
        print("   Testing Supabase connection...")
        try:
            result = repository.supabase.table("portfolio_positions").select("id").limit(1).execute()
            print(f"   ✅ Supabase connection successful")
        except Exception as e:
            print(f"   ❌ Supabase connection failed: {e}")
            return False
        
        print("   Testing portfolio data retrieval...")
        portfolio_data = repository.get_portfolio_data()
        print(f"   Found {len(portfolio_data)} portfolio snapshots")
        
        print("   Testing trade history retrieval...")
        trade_data = repository.get_trade_history()
        print(f"   Found {len(trade_data)} trades")
        
        print("✅ Supabase Repository test passed")
        return True
        
    except Exception as e:
        print(f"❌ Supabase Repository test failed: {e}")
        return False

def test_repository_switch():
    """Test switching between repositories."""
    print("\n🔄 Testing Repository Switch")
    print("-" * 30)
    
    try:
        # Test CSV switch
        print("1. Switching to CSV...")
        from switch_repository import switch_to_csv
        csv_config = switch_to_csv()
        
        # Test Supabase switch
        print("\n2. Switching to Supabase...")
        from switch_repository import switch_to_supabase
        supabase_config = switch_to_supabase()
        
        if supabase_config:
            print("✅ Repository switch test passed")
            return True
        else:
            print("❌ Repository switch test failed")
            return False
            
    except Exception as e:
        print(f"❌ Repository switch test failed: {e}")
        return False

def main():
    """Main test function."""
    print("🧪 REPOSITORY SWITCH TEST")
    print("=" * 40)
    
    # Test CSV repository
    csv_success = test_csv_repository()
    
    # Test Supabase repository
    supabase_success = test_supabase_repository()
    
    # Test repository switching
    switch_success = test_repository_switch()
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    print(f"CSV Repository: {'✅ PASS' if csv_success else '❌ FAIL'}")
    print(f"Supabase Repository: {'✅ PASS' if supabase_success else '❌ FAIL'}")
    print(f"Repository Switch: {'✅ PASS' if switch_success else '❌ FAIL'}")
    
    if csv_success and supabase_success and switch_success:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Repository pattern is working correctly")
        print("✅ You can switch between CSV and Supabase")
        print("✅ Business logic is separated from data access")
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("❌ Check the issues above")
    
    return csv_success and supabase_success and switch_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
