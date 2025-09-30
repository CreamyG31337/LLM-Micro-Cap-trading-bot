#!/usr/bin/env python3
"""
Deployment Diagnostic Script
Run this to identify deployment issues
"""

import os
import sys
import requests
from pathlib import Path
import json
from datetime import datetime

def check_environment_variables():
    """Check if required environment variables are set"""
    print("🔍 Checking Environment Variables...")
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'FLASK_SECRET_KEY', 'JWT_SECRET']
    missing_vars = []
    
    for var in required_vars:
        if os.getenv(var):
            print(f"  ✅ {var}: Set")
        else:
            print(f"  ❌ {var}: Missing")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("   Set these in Vercel dashboard → Settings → Environment Variables")
        return False
    else:
        print("  ✅ All environment variables set")
        return True

def check_supabase_connection():
    """Test Supabase database connection"""
    print("\n🔍 Testing Supabase Connection...")
    
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient()
        
        if client.test_connection():
            print("  ✅ Supabase connection successful")
            return True
        else:
            print("  ❌ Supabase connection failed")
            return False
    except Exception as e:
        print(f"  ❌ Supabase connection error: {e}")
        return False

def check_database_schema():
    """Check if database schema is properly set up"""
    print("\n🔍 Checking Database Schema...")
    
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient()
        
        # Check if key tables exist
        tables_to_check = [
            'portfolio_positions',
            'trade_log', 
            'cash_balances',
            'user_profiles',
            'user_funds'
        ]
        
        missing_tables = []
        for table in tables_to_check:
            try:
                result = client.supabase.table(table).select("*").limit(1).execute()
                print(f"  ✅ Table '{table}': Exists")
            except Exception as e:
                print(f"  ❌ Table '{table}': Missing or error - {e}")
                missing_tables.append(table)
        
        if missing_tables:
            print(f"\n⚠️  Missing tables: {', '.join(missing_tables)}")
            print("   Run schema/00_complete_setup.sql in Supabase SQL Editor")
            return False
        else:
            print("  ✅ All required tables exist")
            return True
            
    except Exception as e:
        print(f"  ❌ Schema check error: {e}")
        return False

def check_data_migration():
    """Check if data has been migrated to database"""
    print("\n🔍 Checking Data Migration...")
    
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient()
        
        # Check portfolio positions
        positions_result = client.supabase.table("portfolio_positions").select("id").limit(1).execute()
        positions_count = len(positions_result.data) if positions_result.data else 0
        
        # Check trade log
        trades_result = client.supabase.table("trade_log").select("id").limit(1).execute()
        trades_count = len(trades_result.data) if trades_result.data else 0
        
        # Check cash balances
        cash_result = client.supabase.table("cash_balances").select("id").limit(1).execute()
        cash_count = len(cash_result.data) if cash_result.data else 0
        
        print(f"  📊 Portfolio positions: {positions_count} records")
        print(f"  📊 Trade log entries: {trades_count} records")
        print(f"  📊 Cash balances: {cash_count} records")
        
        if positions_count == 0 and trades_count == 0:
            print("  ⚠️  No data found in database")
            print("   Run: python migrate.py")
            return False
        else:
            print("  ✅ Data migration appears successful")
            return True
            
    except Exception as e:
        print(f"  ❌ Data migration check error: {e}")
        return False

def check_flask_app():
    """Test if Flask app can start"""
    print("\n🔍 Testing Flask Application...")
    
    try:
        # Test imports
        from app import app
        print("  ✅ Flask app imports successfully")
        
        # Test app configuration
        if app.secret_key:
            print("  ✅ Flask secret key set")
        else:
            print("  ❌ Flask secret key not set")
            return False
            
        print("  ✅ Flask app configuration looks good")
        return True
        
    except Exception as e:
        print(f"  ❌ Flask app error: {e}")
        return False

def check_vercel_deployment():
    """Check Vercel deployment status (if URL provided)"""
    print("\n🔍 Checking Vercel Deployment...")
    
    # This would need the actual deployment URL
    print("  ℹ️  To check Vercel deployment:")
    print("     1. Go to Vercel dashboard")
    print("     2. Check deployment status")
    print("     3. Review build logs")
    print("     4. Check function logs")
    
    return True

def generate_report():
    """Generate a diagnostic report"""
    print("\n" + "="*60)
    print("📋 DEPLOYMENT DIAGNOSTIC REPORT")
    print("="*60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all checks
    env_ok = check_environment_variables()
    supabase_ok = check_supabase_connection()
    schema_ok = check_database_schema()
    data_ok = check_data_migration()
    flask_ok = check_flask_app()
    vercel_ok = check_vercel_deployment()
    
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    
    checks = [
        ("Environment Variables", env_ok),
        ("Supabase Connection", supabase_ok),
        ("Database Schema", schema_ok),
        ("Data Migration", data_ok),
        ("Flask Application", flask_ok),
        ("Vercel Deployment", vercel_ok)
    ]
    
    passed = sum(1 for _, status in checks if status)
    total = len(checks)
    
    for name, status in checks:
        status_icon = "✅" if status else "❌"
        print(f"  {status_icon} {name}")
    
    print(f"\nOverall Status: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 All checks passed! Deployment should be working.")
    else:
        print("⚠️  Some issues found. See details above for fixes.")
        
        print("\n🔧 QUICK FIXES:")
        if not env_ok:
            print("  • Set environment variables in Vercel dashboard")
        if not supabase_ok:
            print("  • Check Supabase URL and API key")
        if not schema_ok:
            print("  • Run schema/00_complete_setup.sql in Supabase")
        if not data_ok:
            print("  • Run: python migrate.py")
        if not flask_ok:
            print("  • Check Flask configuration and dependencies")

def main():
    """Main diagnostic function"""
    print("🔍 LLM Micro-Cap Trading Bot - Deployment Diagnostics")
    print("="*60)
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Error: Run this script from the web_dashboard directory")
        print("   cd web_dashboard")
        print("   python debug_deployment.py")
        sys.exit(1)
    
    generate_report()

if __name__ == "__main__":
    main()

