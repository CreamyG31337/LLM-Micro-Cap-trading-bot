#!/usr/bin/env python3
"""
Interactive Postgres Shell

Simple interactive shell for running SQL queries against the local Postgres database.
Useful for quick debugging and exploration.

Usage:
    python web_dashboard/debug/postgres_shell.py
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

try:
    from web_dashboard.postgres_client import PostgresClient
except ImportError as e:
    print(f"❌ Error importing PostgresClient: {e}")
    sys.exit(1)


class PostgresShell:
    """Interactive shell for Postgres queries"""
    
    def __init__(self):
        """Initialize the shell"""
        try:
            self.client = PostgresClient()
            print("✅ Connected to Postgres database")
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            sys.exit(1)
    
    def execute_query(self, sql: str) -> None:
        """Execute a SQL query"""
        sql = sql.strip()
        if not sql:
            return
        
        # Handle special commands
        if sql.upper().startswith('\\'):
            self.handle_special_command(sql)
            return
        
        try:
            sql_upper = sql.upper()
            if sql_upper.startswith('SELECT') or sql_upper.startswith('WITH'):
                # SELECT query
                result = self.client.execute_query(sql)
                self.print_results(result)
            else:
                # UPDATE, INSERT, DELETE, etc.
                rows_affected = self.client.execute_update(sql)
                print(f"✅ Query executed. Rows affected: {rows_affected}")
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    def print_results(self, results: List[Dict[str, Any]]) -> None:
        """Print query results in a readable format"""
        if not results:
            print("(0 rows)")
            return
        
        # Get column names
        columns = list(results[0].keys())
        
        # Calculate column widths
        col_widths = {}
        for col in columns:
            col_widths[col] = max(
                len(col),
                max(len(str(row[col])) for row in results[:100])  # Limit to first 100 rows for width calc
            )
        
        # Print header
        header = " | ".join(col.ljust(col_widths[col]) for col in columns)
        print(header)
        print("-" * len(header))
        
        # Print rows (limit to 50 for display)
        for row in results[:50]:
            values = [str(row[col])[:col_widths[col]] for col in columns]
            print(" | ".join(val.ljust(col_widths[col]) for val, col in zip(values, columns)))
        
        if len(results) > 50:
            print(f"\n... and {len(results) - 50} more row(s)")
        
        print(f"\n({len(results)} row(s))")
    
    def handle_special_command(self, cmd: str) -> None:
        """Handle special shell commands"""
        cmd = cmd.strip().upper()
        
        if cmd == '\\DT' or cmd == '\\TABLES':
            # List tables
            tables = self.client.execute_query("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            if tables:
                print("\nTables:")
                for table in tables:
                    print(f"  - {table['table_name']}")
            else:
                print("No tables found")
        
        elif cmd == '\\DU' or cmd == '\\USERS':
            # List users
            users = self.client.execute_query("""
                SELECT usename, usecreatedb, usesuper
                FROM pg_user
                ORDER BY usename
            """)
            self.print_results(users)
        
        elif cmd == '\\VERSION':
            # Show version
            version = self.client.execute_query("SELECT version()")
            if version:
                print(version[0]['version'])
        
        elif cmd == '\\DB':
            # Show current database
            db = self.client.execute_query("SELECT current_database(), current_user")
            if db:
                print(f"Database: {db[0]['current_database']}")
                print(f"User: {db[0]['current_user']}")
        
        elif cmd == '\\HELP' or cmd == '\\?':
            # Show help
            print("""
Special Commands:
  \\dt, \\tables    List all tables
  \\du, \\users     List all users
  \\version         Show Postgres version
  \\db              Show current database and user
  \\help, \\?        Show this help
  \\quit, \\exit     Exit the shell

SQL Queries:
  Enter any SQL query and press Enter to execute.
  Multi-line queries: End with semicolon (;)
            """)
        
        elif cmd in ('\\QUIT', '\\EXIT', '\\Q'):
            print("Goodbye!")
            sys.exit(0)
        
        else:
            print(f"Unknown command: {cmd}")
            print("Type \\help for available commands")
    
    def run(self) -> None:
        """Run the interactive shell"""
        print("\n" + "=" * 60)
        print("Postgres Interactive Shell")
        print("=" * 60)
        print("Type SQL queries or special commands (\\help for help)")
        print("Type \\quit to exit\n")
        
        buffer = []
        
        while True:
            try:
                # Get input
                if buffer:
                    prompt = "... "
                else:
                    prompt = "postgres> "
                
                line = input(prompt).strip()
                
                if not line:
                    continue
                
                # Add to buffer
                buffer.append(line)
                
                # Check if query is complete (ends with semicolon)
                query = " ".join(buffer)
                if query.endswith(';'):
                    # Execute query
                    self.execute_query(query.rstrip(';'))
                    buffer = []
                elif line.upper().startswith('\\'):
                    # Special command (execute immediately)
                    self.execute_query(line)
                    buffer = []
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type \\quit to exit.")
                buffer = []
            except EOFError:
                print("\nGoodbye!")
                break


def main():
    """Main entry point"""
    shell = PostgresShell()
    shell.run()


if __name__ == "__main__":
    main()

