#!/usr/bin/env python3
"""
Postgres Database Utilities for Debugging

Helper utilities for connecting to and debugging the local Postgres database.
These utilities use the RESEARCH_DATABASE_URL from environment (with password support).

SECURITY NOTE: This script should ONLY be run from the server/command line.
It is NOT accessible via web interface and should never be exposed as a web endpoint.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from web_dashboard.postgres_client import PostgresClient
except ImportError as e:
    print(f"❌ Error importing PostgresClient: {e}")
    print("Make sure you're in the project root and dependencies are installed")
    sys.exit(1)


class PostgresUtils:
    """Utility class for Postgres database operations"""
    
    def __init__(self):
        """Initialize Postgres utilities"""
        try:
            self.client = PostgresClient()
            logger.info("Postgres client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Postgres client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test database connection"""
        print("=" * 60)
        print("Testing Postgres Connection")
        print("=" * 60)
        
        try:
            if self.client.test_connection():
                print("✅ Connection successful!")
                return True
            else:
                print("❌ Connection failed")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        print("\n" + "=" * 60)
        print("Database Information")
        print("=" * 60)
        
        try:
            info = {}
            
            # Get Postgres version
            version_result = self.client.execute_query("SELECT version()")
            if version_result:
                info['version'] = version_result[0]['version']
                print(f"Postgres Version: {version_result[0]['version'].split(',')[0]}")
            
            # Get current database
            db_result = self.client.execute_query("SELECT current_database(), current_user")
            if db_result:
                info['database'] = db_result[0]['current_database']
                info['user'] = db_result[0]['current_user']
                print(f"Database: {info['database']}")
                print(f"User: {info['user']}")
            
            # Get pgvector extension status
            vector_result = self.client.execute_query(
                "SELECT * FROM pg_extension WHERE extname = 'vector'"
            )
            if vector_result:
                info['pgvector'] = True
                print("✅ pgvector extension is installed")
            else:
                info['pgvector'] = False
                print("⚠️  pgvector extension not found")
            
            return info
            
        except Exception as e:
            print(f"❌ Error getting database info: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def list_tables(self) -> List[str]:
        """List all tables in the database"""
        print("\n" + "=" * 60)
        print("Database Tables")
        print("=" * 60)
        
        try:
            result = self.client.execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            
            tables = [row['table_name'] for row in result]
            
            if tables:
                print(f"Found {len(tables)} table(s):")
                for table in tables:
                    print(f"  - {table}")
            else:
                print("No tables found")
            
            return tables
            
        except Exception as e:
            print(f"❌ Error listing tables: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def describe_table(self, table_name: str) -> Dict[str, Any]:
        """Get table structure and information"""
        print("\n" + "=" * 60)
        print(f"Table Structure: {table_name}")
        print("=" * 60)
        
        try:
            # Get columns
            columns_result = self.client.execute_query("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            
            if not columns_result:
                print(f"❌ Table '{table_name}' not found")
                return {}
            
            print("\nColumns:")
            print("-" * 60)
            for col in columns_result:
                col_type = col['data_type']
                if col['character_maximum_length']:
                    col_type += f"({col['character_maximum_length']})"
                nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
                default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
                print(f"  {col['column_name']:<30} {col_type:<20} {nullable}{default}")
            
            # Get indexes
            indexes_result = self.client.execute_query("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s
            """, (table_name,))
            
            if indexes_result:
                print("\nIndexes:")
                print("-" * 60)
                for idx in indexes_result:
                    print(f"  {idx['indexname']}")
                    print(f"    {idx['indexdef']}")
            
            # Get row count
            count_result = self.client.execute_query(f"SELECT COUNT(*) as count FROM {table_name}")
            if count_result:
                print(f"\nRow Count: {count_result[0]['count']}")
            
            return {
                'columns': columns_result,
                'indexes': indexes_result,
                'row_count': count_result[0]['count'] if count_result else 0
            }
            
        except Exception as e:
            print(f"❌ Error describing table: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results"""
        print("\n" + "=" * 60)
        print("Executing SQL Query")
        print("=" * 60)
        print(f"Query: {sql[:100]}{'...' if len(sql) > 100 else ''}")
        if params:
            print(f"Params: {params}")
        
        try:
            # Check if it's a SELECT query
            sql_upper = sql.strip().upper()
            if sql_upper.startswith('SELECT'):
                result = self.client.execute_query(sql, params)
                print(f"\n✅ Query executed successfully")
                print(f"Results: {len(result)} row(s)")
                
                if result:
                    # Print column headers
                    columns = list(result[0].keys())
                    print("\n" + " | ".join(columns))
                    print("-" * 60)
                    
                    # Print rows (limit to 20 for display)
                    for i, row in enumerate(result[:20]):
                        values = [str(row[col])[:30] for col in columns]
                        print(" | ".join(values))
                    
                    if len(result) > 20:
                        print(f"\n... and {len(result) - 20} more row(s)")
                
                return result
            else:
                # UPDATE, INSERT, DELETE, etc.
                rows_affected = self.client.execute_update(sql, params)
                print(f"\n✅ Query executed successfully")
                print(f"Rows affected: {rows_affected}")
                return []
                
        except Exception as e:
            print(f"❌ Error executing query: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_research_articles_stats(self) -> Dict[str, Any]:
        """Get statistics about research_articles table"""
        print("\n" + "=" * 60)
        print("Research Articles Statistics")
        print("=" * 60)
        
        try:
            stats = {}
            
            # Total count
            total_result = self.client.execute_query("SELECT COUNT(*) as count FROM research_articles")
            stats['total'] = total_result[0]['count'] if total_result else 0
            print(f"Total Articles: {stats['total']}")
            
            # By ticker
            ticker_result = self.client.execute_query("""
                SELECT ticker, COUNT(*) as count
                FROM research_articles
                WHERE ticker IS NOT NULL
                GROUP BY ticker
                ORDER BY count DESC
                LIMIT 10
            """)
            if ticker_result:
                print("\nTop Tickers:")
                for row in ticker_result:
                    print(f"  {row['ticker']}: {row['count']} articles")
                stats['by_ticker'] = ticker_result
            
            # By article type
            type_result = self.client.execute_query("""
                SELECT article_type, COUNT(*) as count
                FROM research_articles
                GROUP BY article_type
                ORDER BY count DESC
            """)
            if type_result:
                print("\nBy Article Type:")
                for row in type_result:
                    print(f"  {row['article_type']}: {row['count']} articles")
                stats['by_type'] = type_result
            
            # Recent articles
            recent_result = self.client.execute_query("""
                SELECT COUNT(*) as count
                FROM research_articles
                WHERE fetched_at >= NOW() - INTERVAL '7 days'
            """)
            stats['recent_7_days'] = recent_result[0]['count'] if recent_result else 0
            print(f"\nArticles (last 7 days): {stats['recent_7_days']}")
            
            # Oldest and newest
            date_result = self.client.execute_query("""
                SELECT 
                    MIN(fetched_at) as oldest,
                    MAX(fetched_at) as newest
                FROM research_articles
            """)
            if date_result and date_result[0]['oldest']:
                print(f"\nDate Range:")
                print(f"  Oldest: {date_result[0]['oldest']}")
                print(f"  Newest: {date_result[0]['newest']}")
                stats['date_range'] = date_result[0]
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting statistics: {e}")
            import traceback
            traceback.print_exc()
            return {}


def main():
    """Command-line interface for Postgres utilities"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Postgres database utilities for debugging",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connection
  python web_dashboard/debug/postgres_utils.py --test
  
  # Get database info
  python web_dashboard/debug/postgres_utils.py --info
  
  # List all tables
  python web_dashboard/debug/postgres_utils.py --list-tables
  
  # Describe a table
  python web_dashboard/debug/postgres_utils.py --describe research_articles
  
  # Execute SQL query
  python web_dashboard/debug/postgres_utils.py --sql "SELECT COUNT(*) FROM research_articles"
  
  # Get research articles statistics
  python web_dashboard/debug/postgres_utils.py --stats
        """
    )
    
    parser.add_argument('--test', action='store_true', help='Test database connection')
    parser.add_argument('--info', action='store_true', help='Get database information')
    parser.add_argument('--list-tables', action='store_true', help='List all tables')
    parser.add_argument('--describe', metavar='TABLE', help='Describe a table structure')
    parser.add_argument('--sql', metavar='QUERY', help='Execute a SQL query')
    parser.add_argument('--stats', action='store_true', help='Get research articles statistics')
    parser.add_argument('--verify', action='store_true', help='Verify production connection (quick check)')
    
    args = parser.parse_args()
    
    # If no arguments, show help
    if not any(vars(args).values()):
        parser.print_help()
        return 0
    
    try:
        utils = PostgresUtils()
        
        if args.test:
            success = utils.test_connection()
            return 0 if success else 1
        
        if args.info:
            utils.get_database_info()
            return 0
        
        if args.list_tables:
            utils.list_tables()
            return 0
        
        if args.describe:
            utils.describe_table(args.describe)
            return 0
        
        if args.sql:
            utils.execute_sql(args.sql)
            return 0
        
        if args.stats:
            utils.get_research_articles_stats()
            return 0
        
        if args.verify:
            # Quick verification
            print("Verifying Postgres connection...")
            if utils.test_connection():
                info = utils.get_database_info()
                tables = utils.list_tables()
                if 'research_articles' in tables:
                    stats = utils.get_research_articles_stats()
                    print("\nProduction Status: OK")
                    print(f"  - Connected to: {info.get('database', 'unknown')}")
                    print(f"  - pgvector: {'installed' if info.get('pgvector') else 'not found'}")
                    print(f"  - Total articles: {stats.get('total', 0)}")
                    return 0
                else:
                    print("\nWARNING: research_articles table not found")
                    return 1
            else:
                print("\nERROR: Connection failed")
                return 1
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

