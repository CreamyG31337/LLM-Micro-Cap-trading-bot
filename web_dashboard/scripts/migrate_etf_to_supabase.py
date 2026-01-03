#!/usr/bin/env python3
"""
Migrate ETF Holdings Data from PostgreSQL to Supabase
======================================================
Schema already applied manually - this script just migrates the data.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from postgres_client import PostgresClient
from supabase_client import SupabaseClient

def migrate_data():
    """Export from PostgreSQL and import to Supabase"""
    print("=" * 60)
    print("ETF Holdings Data Migration")
    print("=" * 60)
    
    pg = PostgresClient()
    supabase = SupabaseClient(use_service_role=True)  # Use service role for writes
    
    # Get all holdings from PostgreSQL
    print("\n1. Fetching data from PostgreSQL...")
    query = "SELECT * FROM etf_holdings_log ORDER BY date DESC, etf_ticker, holding_ticker"
    
    try:
        holdings = pg.execute_query(query)
        print(f"✅ Fetched {len(holdings)} holdings records")
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return False
    
    if not holdings:
        print("⚠️  No data to migrate")
        return True
    
    # Batch insert to Supabase
    print(f"\n2. Importing {len(holdings)} records to Supabase...")
    batch_size = 500  # Smaller batches for Supabase
    total_inserted = 0
    
    for i in range(0, len(holdings), batch_size):
        batch = holdings[i:i + batch_size]
        
        try:
            # Convert to list of dicts for Supabase
            records = []
            for row in batch:
                record = {
                    'date': str(row['date']),
                    'etf_ticker': row['etf_ticker'],
                    'holding_ticker': row['holding_ticker'],
                    'holding_name': row['holding_name'],
                }
                
                # Add optional numeric fields only if not None
                if row.get('shares_held') is not None:
                    record['shares_held'] = float(row['shares_held'])
                if row.get('weight_percent') is not None:
                    record['weight_percent'] = float(row['weight_percent'])
                if row.get('market_value') is not None:
                    record['market_value'] = float(row['market_value'])
                    
                records.append(record)
            
            # Use upsert to handle any duplicates
            supabase.supabase.table('etf_holdings_log').upsert(records).execute()
            total_inserted += len(batch)
            print(f"  ✓ Batch {i//batch_size + 1}/{(len(holdings)-1)//batch_size + 1}: {total_inserted}/{len(holdings)} records")
            
        except Exception as e:
            print(f"❌ Error inserting batch {i//batch_size + 1}: {e}")
            print(f"   First record in failed batch: {records[0] if records else 'N/A'}")
            return False
    
    print(f"\n✅ Successfully migrated {total_inserted} records!")
    return True

def verify_migration():
    """Verify data was migrated correctly"""
    print("\n" + "=" * 60)
    print("Verification")
    print("=" * 60)
    
    pg = PostgresClient()
    supabase = SupabaseClient(use_service_role=True)
    
    try:
        # Count records
        pg_count = pg.execute_query("SELECT COUNT(*) as count FROM etf_holdings_log")[0]['count']
        supabase_result = supabase.supabase.table('etf_holdings_log').select('*', count='exact').limit(1).execute()
        supabase_count = supabase_result.count
        
        print(f"\nPostgreSQL: {pg_count} records")
        print(f"Supabase:   {supabase_count} records")
        
        if pg_count == supabase_count:
            print("✅ Record counts match!")
        else:
            print(f"⚠️  Record count mismatch: {supabase_count - pg_count} difference")
            
        # Check distinct ETFs
        pg_etfs = pg.execute_query("SELECT DISTINCT etf_ticker FROM etf_holdings_log ORDER BY etf_ticker")
        supabase_etfs_result = supabase.supabase.table('etf_holdings_log').select('etf_ticker').execute()
        supabase_etf_list = sorted(list(set(row['etf_ticker'] for row in supabase_etfs_result.data)))
        
        pg_etf_list = [row['etf_ticker'] for row in pg_etfs]
        
        print(f"\nETFs in PostgreSQL: {', '.join(pg_etf_list)}")
        print(f"ETFs in Supabase:   {', '.join(supabase_etf_list)}")
        
        if pg_etf_list == supabase_etf_list:
            print("✅ ETF lists match!")
        else:
            print("⚠️  ETF lists differ")
            
        return True
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🚀 ETF Holdings Data Migration: PostgreSQL → Supabase\n")
    
    if not migrate_data():
        print("\n❌ Migration failed")
        sys.exit(1)
    
    if not verify_migration():
        print("\n❌ Verification failed")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
