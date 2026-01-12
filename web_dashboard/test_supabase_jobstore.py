#!/usr/bin/env python3
"""
Test script to verify SQLAlchemyJobStore can connect to Supabase PostgreSQL
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding for emoji
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load environment variables
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

def test_sqlalchemy_import():
    """Test if SQLAlchemy is available"""
    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy version: {sqlalchemy.__version__}")
        return True
    except ImportError:
        print("❌ SQLAlchemy not installed")
        print("   Install with: pip install sqlalchemy")
        return False

def test_apscheduler_jobstore_import():
    """Test if SQLAlchemyJobStore is available"""
    try:
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        print("✅ SQLAlchemyJobStore import successful")
        return True
    except ImportError as e:
        print(f"❌ SQLAlchemyJobStore import failed: {e}")
        print("   Install with: pip install apscheduler[postgresql]")
        return False

def test_database_connection():
    """Test direct database connection"""
    database_url = os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        print("❌ SUPABASE_DATABASE_URL not set in environment")
        print("   Set it in .env file with format:")
        print("   SUPABASE_DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres")
        return False
    
    # Mask password in output
    safe_url = database_url.split('@')[0].split(':')[0] + ':***@' + '@'.join(database_url.split('@')[1:])
    print(f"📡 Testing connection to: {safe_url}")
    
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"   PostgreSQL version: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_jobstore_creation():
    """Test creating SQLAlchemyJobStore"""
    database_url = os.getenv("SUPABASE_DATABASE_URL")
    if not database_url:
        return False
    
    try:
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
        
        print("📦 Testing SQLAlchemyJobStore creation...")
        jobstore = SQLAlchemyJobStore(url=database_url, tablename='apscheduler_jobs')
        print("✅ SQLAlchemyJobStore created successfully")
        
        # Try to start it (this will create tables if they don't exist)
        print("📦 Testing jobstore initialization (will create tables if needed)...")
        jobstore.start(None, None)  # scheduler, alias
        
        # Check if table exists
        import sqlalchemy
        engine = sqlalchemy.create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'apscheduler_jobs'
                )
            """))
            table_exists = result.fetchone()[0]
            if table_exists:
                print("✅ Table 'apscheduler_jobs' exists")
            else:
                print("⚠️  Table 'apscheduler_jobs' not found (may be created on first use)")
        
        jobstore.shutdown()
        print("✅ SQLAlchemyJobStore shutdown successful")
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemyJobStore test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Supabase PostgreSQL connection for SQLAlchemyJobStore")
    print("=" * 60)
    print()
    
    results = []
    
    print("1. Testing SQLAlchemy import...")
    results.append(("SQLAlchemy", test_sqlalchemy_import()))
    print()
    
    print("2. Testing SQLAlchemyJobStore import...")
    results.append(("SQLAlchemyJobStore", test_apscheduler_jobstore_import()))
    print()
    
    print("3. Testing database connection...")
    results.append(("Database Connection", test_database_connection()))
    print()
    
    print("4. Testing SQLAlchemyJobStore creation...")
    results.append(("JobStore Creation", test_jobstore_creation()))
    print()
    
    print("=" * 60)
    print("Test Results Summary:")
    print("=" * 60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(result[1] for result in results)
    print()
    if all_passed:
        print("🎉 All tests passed! Supabase is ready for SQLAlchemyJobStore")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
