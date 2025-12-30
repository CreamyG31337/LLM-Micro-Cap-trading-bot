#!/usr/bin/env python3
"""
Update CREATE TABLE statements in schema files to match current database structure.
This ensures LLMs looking at schema files see the complete, up-to-date table definitions.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'web_dashboard'))

try:
    from supabase_client import SupabaseClient
    from postgres_client import PostgresClient
except ImportError as e:
    print(f"❌ Error importing database clients: {e}")
    print("Make sure you're in the virtual environment and dependencies are installed")
    sys.exit(1)


def get_supabase_table_schema(table_name: str) -> List[Dict[str, any]]:
    """Get table schema from Supabase using direct Postgres connection"""
    try:
        # Try to get Supabase direct connection string
        supabase_db_url = os.getenv("SUPABASE_DB_URL")
        
        if not supabase_db_url:
            # Try to construct from SUPABASE_URL (this won't work without password)
            # For now, we'll use a workaround - query via Supabase client by selecting from the table
            # and inferring schema, or use a helper SQL function
            print(f"⚠️  SUPABASE_DB_URL not set - cannot query Supabase directly")
            print(f"   Table: {table_name} - using alternative method")
            
            # Alternative: Try to get schema by querying the table structure via Supabase client
            # This is limited but better than nothing
            try:
                client = SupabaseClient(use_service_role=True)
                # Try to get one row to see what columns exist
                result = client.supabase.table(table_name).select("*").limit(1).execute()
                if result.data:
                    # We have column names but not types - this is limited
                    print(f"   ⚠️  Can only get column names, not full schema for {table_name}")
                    return []
            except:
                pass
            
            return []
        
        # Use direct Postgres connection
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        conn = psycopg2.connect(supabase_db_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable,
            column_default,
            is_generated,
            generation_expression
        FROM information_schema.columns
        WHERE table_schema = 'public' 
          AND table_name = %s
        ORDER BY ordinal_position;
        """
        
        cursor.execute(query, (table_name,))
        result = [dict(row) for row in cursor.fetchall()]
        cursor.close()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting Supabase schema for {table_name}: {e}")
        return []


def get_postgres_table_schema(table_name: str) -> List[Dict[str, any]]:
    """Get table schema from Postgres using information_schema"""
    try:
        client = PostgresClient()
        
        query = """
        SELECT 
            column_name,
            data_type,
            character_maximum_length,
            numeric_precision,
            numeric_scale,
            is_nullable,
            column_default,
            is_generated,
            generation_expression
        FROM information_schema.columns
        WHERE table_schema = 'public' 
          AND table_name = %s
        ORDER BY ordinal_position;
        """
        
        result = client.execute_query(query, (table_name,))
        return result
        
    except Exception as e:
        print(f"❌ Error getting Postgres schema for {table_name}: {e}")
        return []


def format_column_definition(col: Dict[str, any]) -> str:
    """Format a column definition from information_schema data"""
    name = col['column_name']
    data_type = col['data_type']
    
    # Handle data types with length/precision
    if data_type in ['character varying', 'varchar']:
        max_len = col.get('character_maximum_length')
        if max_len:
            data_type = f"VARCHAR({max_len})"
        else:
            data_type = "VARCHAR"
    elif data_type == 'character':
        max_len = col.get('character_maximum_length')
        if max_len:
            data_type = f"CHAR({max_len})"
        else:
            data_type = "CHAR"
    elif data_type in ['numeric', 'decimal']:
        precision = col.get('numeric_precision')
        scale = col.get('numeric_scale')
        if precision and scale is not None:
            data_type = f"DECIMAL({precision}, {scale})"
        elif precision:
            data_type = f"DECIMAL({precision})"
        else:
            data_type = "DECIMAL"
    elif data_type == 'timestamp with time zone':
        data_type = "TIMESTAMP WITH TIME ZONE"
    elif data_type == 'timestamp without time zone':
        data_type = "TIMESTAMP"
    elif data_type == 'double precision':
        data_type = "DOUBLE PRECISION"
    elif data_type == 'uuid':
        data_type = "UUID"
    elif data_type == 'text':
        data_type = "TEXT"
    elif data_type == 'boolean':
        data_type = "BOOLEAN"
    elif data_type == 'integer':
        data_type = "INTEGER"
    elif data_type == 'bigint':
        data_type = "BIGINT"
    elif data_type == 'smallint':
        data_type = "SMALLINT"
    elif data_type == 'real':
        data_type = "REAL"
    elif data_type.startswith('vector'):
        data_type = col['data_type'].upper()  # Keep as-is for vector types
    else:
        data_type = data_type.upper()
    
    # Build column definition
    parts = [f"    {name} {data_type}"]
    
    # Handle NOT NULL
    if col.get('is_nullable') == 'NO':
        parts.append("NOT NULL")
    
    # Handle DEFAULT
    default = col.get('column_default')
    if default:
        # Clean up default value
        default = default.strip()
        # Remove ::type casts for readability
        default = re.sub(r'::\w+(\[\])?', '', default)
        # Handle function calls
        if default.startswith("'") and default.endswith("'"):
            # String literal
            parts.append(f"DEFAULT {default}")
        elif default.upper() in ['NOW()', 'CURRENT_TIMESTAMP', 'CURRENT_DATE']:
            parts.append(f"DEFAULT {default}")
        elif default.startswith('uuid_generate_v4()'):
            parts.append("DEFAULT uuid_generate_v4()")
        elif default.startswith('gen_random_uuid()'):
            parts.append("DEFAULT gen_random_uuid()")
        elif default.isdigit() or (default.startswith('-') and default[1:].isdigit()):
            parts.append(f"DEFAULT {default}")
        elif default.startswith("'") or default.upper() == 'TRUE' or default.upper() == 'FALSE':
            parts.append(f"DEFAULT {default}")
        else:
            parts.append(f"DEFAULT {default}")
    
    # Handle GENERATED columns
    if col.get('is_generated') == 'ALWAYS':
        gen_expr = col.get('generation_expression')
        if gen_expr:
            # Clean up generation expression
            gen_expr = gen_expr.strip()
            parts.append(f"GENERATED ALWAYS AS ({gen_expr}) STORED")
    
    return " ".join(parts)


def find_create_table_statements(content: str) -> List[Tuple[int, int, str, str]]:
    """Find all CREATE TABLE statements in content
    Returns list of (start_line, end_line, table_name, full_statement)
    """
    statements = []
    lines = content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        # Look for CREATE TABLE
        match = re.match(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_]+)', line, re.IGNORECASE)
        if match:
            table_name = match.group(1)
            start_line = i
            
            # Find the end of the CREATE TABLE statement (closing parenthesis)
            paren_count = 0
            end_line = i
            in_string = False
            string_char = None
            
            for j in range(i, len(lines)):
                line_text = lines[j]
                for char in line_text:
                    if char in ("'", '"') and (j == i or lines[j-1][-1] != '\\'):
                        if not in_string:
                            in_string = True
                            string_char = char
                        elif char == string_char:
                            in_string = False
                            string_char = None
                    
                    if not in_string:
                        if char == '(':
                            paren_count += 1
                        elif char == ')':
                            paren_count -= 1
                            if paren_count == 0:
                                end_line = j
                                break
                
                if paren_count == 0:
                    break
            
            # Extract the full statement
            full_statement = '\n'.join(lines[start_line:end_line+1])
            statements.append((start_line, end_line, table_name, full_statement))
            i = end_line + 1
        else:
            i += 1
    
    return statements


def generate_create_table_statement(table_name: str, columns: List[Dict[str, any]], 
                                    constraints: Optional[List[str]] = None) -> str:
    """Generate a CREATE TABLE statement from column definitions"""
    lines = [f"CREATE TABLE {table_name} ("]
    
    # Add columns
    col_defs = []
    for col in columns:
        col_def = format_column_definition(col)
        col_defs.append(col_def)
    
    # Join columns with commas
    for i, col_def in enumerate(col_defs):
        if i < len(col_defs) - 1:
            lines.append(col_def + ",")
        else:
            lines.append(col_def)
    
    # Add constraints if any
    if constraints:
        for constraint in constraints:
            lines.append(f",    {constraint}")
    
    lines.append(");")
    
    return '\n'.join(lines)


def get_table_constraints(table_name: str, database: str = 'postgres') -> List[str]:
    """Get table constraints (PRIMARY KEY, UNIQUE, FOREIGN KEY, etc.)"""
    constraints = []
    
    try:
        if database == 'postgres':
            client = PostgresClient()
            
            # Get primary key
            pk_query = """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass
              AND i.indisprimary;
            """
            pk_result = client.execute_query(pk_query, (table_name,))
            if pk_result:
                pk_cols = [row['attname'] for row in pk_result]
                if len(pk_cols) == 1:
                    constraints.append(f"PRIMARY KEY ({pk_cols[0]})")
                else:
                    constraints.append(f"PRIMARY KEY ({', '.join(pk_cols)})")
            
            # Get unique constraints
            unique_query = """
            SELECT
                conname as constraint_name,
                array_agg(a.attname ORDER BY array_position(con.conkey, a.attnum)) as columns
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
            JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = ANY(con.conkey)
            WHERE nsp.nspname = 'public'
              AND rel.relname = %s
              AND con.contype = 'u'
            GROUP BY conname;
            """
            unique_result = client.execute_query(unique_query, (table_name,))
            for row in unique_result:
                cols = row['columns']
                if len(cols) == 1:
                    constraints.append(f"UNIQUE ({cols[0]})")
                else:
                    constraints.append(f"UNIQUE ({', '.join(cols)})")
            
            # Get foreign keys
            fk_query = """
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
              AND tc.table_name = %s;
            """
            fk_result = client.execute_query(fk_query, (table_name,))
            for row in fk_result:
                constraints.append(
                    f"FOREIGN KEY ({row['column_name']}) "
                    f"REFERENCES {row['foreign_table_name']}({row['foreign_column_name']})"
                )
        
    except Exception as e:
        print(f"⚠️  Error getting constraints for {table_name}: {e}")
    
    return constraints


def update_schema_file(file_path: Path, table_mapping: Dict[str, str]) -> bool:
    """Update CREATE TABLE statements in a schema file
    
    Args:
        file_path: Path to schema file
        table_mapping: Dict mapping table_name -> database ('supabase' or 'postgres')
    
    Returns:
        True if file was updated, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        statements = find_create_table_statements(content)
        
        if not statements:
            print(f"  ℹ️  No CREATE TABLE statements found in {file_path.name}")
            return False
        
        updated = False
        for start_line, end_line, table_name, old_statement in statements:
            print(f"  📋 Found table: {table_name}")
            
            # Determine which database to query
            database = table_mapping.get(table_name, 'supabase')  # Default to Supabase
            
            # Get current schema
            if database == 'postgres':
                columns = get_postgres_table_schema(table_name)
            else:
                columns = get_supabase_table_schema(table_name)
            
            if not columns:
                print(f"    ⚠️  Could not get schema for {table_name}, skipping")
                continue
            
            # Get constraints
            constraints = get_table_constraints(table_name, database)
            
            # Generate new CREATE TABLE statement
            new_statement = generate_create_table_statement(table_name, columns, constraints)
            
            # Replace in content
            lines = content.split('\n')
            new_lines = lines[:start_line] + new_statement.split('\n') + lines[end_line+1:]
            content = '\n'.join(new_lines)
            updated = True
            print(f"    ✅ Updated {table_name}")
        
        if updated and content != original_content:
            # Backup original file
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Write updated content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"  ✅ Updated {file_path.name} (backup saved to {backup_path.name})")
            return True
        else:
            print(f"  ℹ️  No changes needed for {file_path.name}")
            return False
            
    except Exception as e:
        print(f"  ❌ Error updating {file_path.name}: {e}")
        return False


def main():
    """Main function to update all schema files"""
    schema_dir = Path(__file__).parent
    
    print("🔍 Scanning schema files for CREATE TABLE statements...")
    
    # Find all SQL schema files
    schema_files = sorted(schema_dir.glob("*.sql"))
    schema_files = [f for f in schema_files if f.name != "README.md"]
    
    # Also check supabase subdirectory
    supabase_dir = schema_dir / "supabase"
    if supabase_dir.exists():
        schema_files.extend(supabase_dir.glob("*.sql"))
    
    print(f"📁 Found {len(schema_files)} schema files")
    
    # Map tables to databases
    # Tables in Supabase
    supabase_tables = {
        'portfolio_positions', 'trade_log', 'cash_balances', 'performance_metrics',
        'user_funds', 'user_profiles', 'fund_thesis', 'fund_thesis_pillars',
        'fund_contributions', 'exchange_rates', 'user_preferences', 'rss_feeds',
        'job_executions', 'social_metrics', 'social_posts', 'sentiment_sessions',
        'congress_trades', 'congress_trades_staging', 'congress_trade_sessions',
        'committees', 'watchlist'
    }
    
    # Tables in Postgres
    postgres_tables = {
        'research_articles', 'congress_trades_analysis', 'social_sentiment_analysis',
        'extracted_tickers', 'post_summaries'
    }
    
    table_mapping = {}
    for table in supabase_tables:
        table_mapping[table] = 'supabase'
    for table in postgres_tables:
        table_mapping[table] = 'postgres'
    
    # Process each schema file
    updated_count = 0
    for schema_file in schema_files:
        print(f"\n📄 Processing {schema_file.name}...")
        if update_schema_file(schema_file, table_mapping):
            updated_count += 1
    
    print(f"\n✅ Done! Updated {updated_count} schema files")
    print("💾 Backup files (.bak) were created for safety")


if __name__ == "__main__":
    main()

