#!/usr/bin/env python3
"""
Quick Deployment Test Script
Tests the deployment locally to identify issues
"""

import os
import sys
from pathlib import Path

def test_local_deployment():
    """Test the deployment locally"""
    print("🧪 Testing Local Deployment...")
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Error: Run from web_dashboard directory")
        return False
    
    # Test environment variables
    print("\n1. Checking Environment Variables...")
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing: {', '.join(missing_vars)}")
        print("   Create .env file with:")
        print("   SUPABASE_URL=your_supabase_url")
        print("   SUPABASE_ANON_KEY=your_anon_key")
        return False
    else:
        print("✅ Environment variables set")
    
    # Test Supabase connection
    print("\n2. Testing Supabase Connection...")
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient()
        if client.test_connection():
            print("✅ Supabase connection successful")
        else:
            print("❌ Supabase connection failed")
            return False
    except Exception as e:
        print(f"❌ Supabase error: {e}")
        return False
    
    # Test Flask app
    print("\n3. Testing Flask Application...")
    try:
        from app import app
        print("✅ Flask app imports successfully")
        
        # Test a simple route
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Flask app responds to requests")
            else:
                print(f"❌ Flask app error: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"❌ Flask error: {e}")
        return False
    
    print("\n🎉 Local deployment test passed!")
    print("   Your app should work on Vercel if environment variables are set correctly.")
    return True

def main():
    """Main test function"""
    print("🧪 LLM Trading Bot - Deployment Test")
    print("="*40)
    
    if test_local_deployment():
        print("\n✅ All tests passed!")
        print("   If deployment is still buggy, check:")
        print("   • Vercel environment variables")
        print("   • Vercel build logs")
        print("   • Supabase database schema")
        print("   • Data migration status")
    else:
        print("\n❌ Tests failed!")
        print("   Fix the issues above before deploying.")

if __name__ == "__main__":
    main()

