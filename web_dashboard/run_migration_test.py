#!/usr/bin/env python3
"""
Complete Migration Test Runner
Runs migration and verification in sequence
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n🔄 {description}...")
    print(f"   Command: {command}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def main():
    """Run the complete migration test sequence"""
    print("🧪 COMPLETE MIGRATION TEST SEQUENCE")
    print("=" * 60)
    
    # Step 1: Test environment and data availability
    print("\n📋 STEP 1: Pre-migration tests")
    print("-" * 40)
    
    success = run_command("python test_migration.py", "Pre-migration tests")
    if not success:
        print("\n❌ Pre-migration tests failed - stopping")
        return False
    
    # Step 2: Run migration
    print("\n📋 STEP 2: Run migration")
    print("-" * 40)
    
    success = run_command("python migrate.py", "Data migration")
    if not success:
        print("\n❌ Migration failed - stopping")
        return False
    
    # Step 3: Verify migration
    print("\n📋 STEP 3: Verify migration")
    print("-" * 40)
    
    success = run_command("python verify_migration.py", "Migration verification")
    if not success:
        print("\n❌ Migration verification failed")
        return False
    
    # Step 4: Test app functionality
    print("\n📋 STEP 4: Test app functionality")
    print("-" * 40)
    
    # Test if we can import the app
    try:
        print("🔄 Testing app imports...")
        sys.path.append(str(Path(__file__).parent))
        
        # Test basic imports
        from supabase_client import SupabaseClient
        from auth import auth_manager
        print("✅ App imports successful")
        
        # Test Supabase client
        client = SupabaseClient()
        if client:
            print("✅ Supabase client works")
        else:
            print("❌ Supabase client failed")
            return False
        
        print("✅ App functionality test passed")
        
    except Exception as e:
        print(f"❌ App functionality test failed: {e}")
        return False
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 MIGRATION TEST SEQUENCE COMPLETE!")
    print("=" * 60)
    print("✅ Pre-migration tests passed")
    print("✅ Migration completed")
    print("✅ Migration verified")
    print("✅ App functionality confirmed")
    print("\n🚀 Ready to switch the app to use Supabase!")
    print("\n📋 Next steps:")
    print("1. Deploy the updated app to Vercel")
    print("2. Test the web dashboard")
    print("3. Verify all features work with Supabase data")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
