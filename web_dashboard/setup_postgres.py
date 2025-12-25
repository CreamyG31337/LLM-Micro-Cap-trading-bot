#!/usr/bin/env python3
"""
Set up local Postgres database with research articles schema.

This script creates the necessary tables in your local Postgres Docker container
for storing research articles scraped from websites.
"""

import os
import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from web_dashboard.postgres_client import PostgresClient
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install psycopg2-binary python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv("web_dashboard/.env")


def setup_postgres():
    """Set up the local Postgres database with research articles schema."""
    print("🚀 Setting up Local Postgres Database")
    print("=" * 50)
    
    # Configure logging to see detailed error messages
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s: %(message)s'
    )
    
    # Check for RESEARCH_DATABASE_URL
    database_url = os.getenv("RESEARCH_DATABASE_URL")
    if not database_url:
        print("❌ RESEARCH_DATABASE_URL must be set in environment")
        print("   Add to web_dashboard/.env:")
        print("   RESEARCH_DATABASE_URL=postgresql://postgres@localhost:5432/trading_db")
        print("   (Password may not be required for localhost connections)")
        return False
    
    print(f"📋 Using RESEARCH_DATABASE_URL: {database_url.split('@')[0]}@***")  # Mask password
    
    # Initialize Postgres client
    try:
        print("\n🔍 Initializing Postgres client...")
        client = PostgresClient()
        print("✅ Postgres client initialized")
    except Exception as e:
        print(f"\n❌ Failed to initialize Postgres client: {e}")
        print("\n💡 Troubleshooting:")
        print("   1. Make sure your Postgres container is running")
        print("   2. Check that RESEARCH_DATABASE_URL is correct in .env")
        print("   3. Verify the database 'trading_db' exists")
        print("   4. Check port 5432 is accessible")
        print("   5. For localhost, password may not be required (trust authentication)")
        print("   6. Check logs above for detailed error messages")
        return False
    
    # Test connection
    print("\n🔍 Testing database connection...")
    if not client.test_connection():
        print("❌ Connection test failed")
        print("   Check the logs above for detailed error information")
        return False
    
    # Check for pgvector extension
    print("\n🔍 Checking for pgvector extension...")
    try:
        result = client.execute_query("SELECT * FROM pg_extension WHERE extname = 'vector'")
        if result:
            print("✅ pgvector extension is installed")
        else:
            print("⚠️  pgvector extension not found")
            print("   Run this SQL command in your database:")
            print("   CREATE EXTENSION IF NOT EXISTS vector;")
            response = input("\n   Continue anyway? (y/n): ")
            if response.lower() != 'y':
                return False
    except Exception as e:
        print(f"⚠️  Could not check for pgvector extension: {e}")
        print("   Make sure pgvector is installed before using vector search")
    
    # Read and execute schema file
    schema_file = Path("web_dashboard/schema/10_research_articles.sql")
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
    
    print(f"\n📄 Executing: {schema_file.name}")
    try:
        with open(schema_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Split SQL by semicolons (handling comments and multi-line statements)
        # Simple approach: execute the entire file
        with client.get_connection() as conn:
            cursor = conn.cursor()
            # Execute the SQL file
            cursor.execute(sql_content)
            conn.commit()
            print(f"✅ Successfully executed {schema_file.name}")
            
    except Exception as e:
        print(f"❌ Error executing {schema_file.name}: {e}")
        print("\n💡 Common issues:")
        print("   - Table might already exist (this is OK)")
        print("   - pgvector extension not installed")
        print("   - Insufficient permissions")
        return False
    
    # Verify table exists
    print("\n🔍 Verifying table creation...")
    try:
        result = client.execute_query(
            "SELECT COUNT(*) as count FROM information_schema.tables WHERE table_name = 'research_articles'"
        )
        if result and result[0]['count'] > 0:
            print("✅ research_articles table exists")
        else:
            print("❌ research_articles table not found")
            return False
    except Exception as e:
        print(f"❌ Error verifying table: {e}")
        return False
    
    # Check indexes
    print("\n🔍 Verifying indexes...")
    try:
        result = client.execute_query(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'research_articles'"
        )
        indexes = [row['indexname'] for row in result]
        print(f"✅ Found {len(indexes)} indexes: {', '.join(indexes)}")
    except Exception as e:
        print(f"⚠️  Could not verify indexes: {e}")
    
    print("\n✅ Postgres database setup complete!")
    print("\n📋 Next steps:")
    print("  1. Test the connection: python -c 'from web_dashboard.postgres_client import PostgresClient; PostgresClient().test_connection()'")
    print("  2. Start using ResearchRepository in your scraping code")
    print("  3. Set up password authentication if not already done")
    
    return True


if __name__ == "__main__":
    success = setup_postgres()
    if not success:
        sys.exit(1)

