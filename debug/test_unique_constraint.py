#!/usr/bin/env python3
"""
Test the unique constraint on portfolio_positions to ensure it prevents duplicates
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

from supabase_client import SupabaseClient
from datetime import datetime, timezone
import uuid

def test_unique_constraint():
    """Test that the unique constraint prevents duplicates"""
    client = SupabaseClient(use_service_role=True)
    fund_name = 'Project Chimera'
    
    print("="*80)
    print("TESTING UNIQUE CONSTRAINT ON PORTFOLIO_POSITIONS")
    print("="*80)
    
    # Test 1: Check that date_only column exists and is populated
    print("\n[TEST 1] Checking date_only column exists and is populated...")
    result = client.supabase.table('portfolio_positions')\
        .select('id, date, date_only, fund, ticker')\
        .eq('fund', fund_name)\
        .limit(10)\
        .execute()
    
    if result.data:
        print(f"  Found {len(result.data)} sample records:")
        all_have_date_only = True
        for record in result.data[:5]:
            has_date_only = record.get('date_only') is not None
            if not has_date_only:
                all_have_date_only = False
            print(f"    ID: {record['id'][:8]}... | Date: {record['date']} | Date Only: {record.get('date_only', 'NULL')}")
        
        if all_have_date_only:
            print("  [PASS] All records have date_only populated")
        else:
            print("  [FAIL] Some records are missing date_only - trigger may not be working")
    else:
        print("  [SKIP] No records found to test")
    
    # Test 2: Try to insert a duplicate (should fail or be prevented)
    print("\n[TEST 2] Testing duplicate prevention...")
    
    # Get an existing position to duplicate
    existing = client.supabase.table('portfolio_positions')\
        .select('fund, ticker, date, date_only')\
        .eq('fund', fund_name)\
        .limit(1)\
        .execute()
    
    if not existing.data:
        print("  [SKIP] No existing positions to test duplicate prevention")
        return
    
    test_record = existing.data[0]
    test_fund = test_record['fund']
    test_ticker = test_record['ticker']
    test_date = test_record['date']
    test_date_only = test_record.get('date_only')
    
    print(f"  Using existing position: {test_fund} | {test_ticker} | {test_date_only}")
    
    # Try to insert a duplicate with same (fund, ticker, date_only)
    # This should fail due to unique constraint
    test_duplicate = {
        'id': str(uuid.uuid4()),
        'fund': test_fund,
        'ticker': test_ticker,
        'shares': 100.0,
        'price': 10.0,
        'cost_basis': 1000.0,
        'pnl': 0.0,
        'currency': 'USD',
        'date': test_date,  # Same date (will result in same date_only)
    }
    
    try:
        result = client.supabase.table('portfolio_positions')\
            .insert(test_duplicate)\
            .execute()
        
        print("  [FAIL] Duplicate was inserted! Unique constraint is not working")
        print(f"  Inserted record ID: {result.data[0]['id'] if result.data else 'unknown'}")
        
        # Clean up the duplicate we just created
        if result.data:
            client.supabase.table('portfolio_positions')\
                .delete()\
                .eq('id', result.data[0]['id'])\
                .execute()
            print("  Cleaned up test duplicate")
        
    except Exception as e:
        error_msg = str(e)
        if 'duplicate' in error_msg.lower() or 'unique' in error_msg.lower() or 'violates' in error_msg.lower():
            print("  [PASS] Duplicate insertion was prevented by unique constraint")
            print(f"  Error (expected): {error_msg[:100]}...")
        else:
            print(f"  [UNKNOWN] Got unexpected error: {error_msg[:100]}...")
    
    # Test 3: Test that upsert works correctly (should update existing, not create duplicate)
    print("\n[TEST 3] Testing upsert behavior with unique constraint...")
    
    # Get an existing position to upsert
    existing_for_upsert = client.supabase.table('portfolio_positions')\
        .select('*')\
        .eq('fund', fund_name)\
        .limit(1)\
        .execute()
    
    if not existing_for_upsert.data:
        print("  [SKIP] No existing positions to test upsert")
        return
    
    original = existing_for_upsert.data[0]
    original_id = original['id']
    original_shares = float(original['shares'])
    
    # Create upsert data with same (fund, ticker, date_only) but different shares
    # Need to include date_only for PostgREST upsert to work with the unique constraint
    from datetime import datetime as dt
    date_obj = dt.fromisoformat(original['date'].replace('Z', '+00:00'))
    date_only_str = date_obj.date().isoformat()
    
    upsert_data = {
        'fund': original['fund'],
        'ticker': original['ticker'],
        'shares': original_shares + 1.0,  # Different value
        'price': float(original['price']),
        'cost_basis': float(original['cost_basis']),
        'pnl': float(original.get('pnl', 0)),
        'currency': original.get('currency', 'USD'),
        'date': original['date'],  # Same date
        'date_only': date_only_str,  # Include date_only for on_conflict to work
    }
    
    try:
        # Upsert should update the existing record, not create a duplicate
        # PostgREST needs column names in the exact order of the constraint: (fund, ticker, date_only)
        result = client.supabase.table('portfolio_positions')\
            .upsert(
                upsert_data,
                on_conflict="fund,ticker,date_only"
            )\
            .execute()
        
        if result.data:
            updated_record = result.data[0]
            updated_id = updated_record['id']
            updated_shares = float(updated_record['shares'])
            
            if updated_id == original_id:
                print(f"  [PASS] Upsert updated existing record (ID: {updated_id[:8]}...)")
                print(f"  Shares changed from {original_shares} to {updated_shares}")
            else:
                print(f"  [WARNING] Upsert created new record instead of updating")
                print(f"  Original ID: {original_id[:8]}... | New ID: {updated_id[:8]}...")
            
            # Restore original shares
            client.supabase.table('portfolio_positions')\
                .update({'shares': original_shares})\
                .eq('id', original_id)\
                .execute()
            print("  Restored original shares value")
        
    except Exception as e:
        print(f"  [FAIL] Upsert failed: {e}")
    
    # Test 4: Verify unique index exists
    print("\n[TEST 4] Verifying unique index exists...")
    # We can't directly query indexes via Supabase client, but we can infer it exists
    # if the constraint is working (which we tested above)
    print("  [INFO] Unique index verification requires direct database access")
    print("  Run: SELECT indexname FROM pg_indexes WHERE tablename = 'portfolio_positions' AND indexname = 'idx_portfolio_positions_unique';")
    
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)
    print("\nSummary:")
    print("  - If all tests passed, the unique constraint is working correctly")
    print("  - The constraint prevents duplicates at the database level")
    print("  - Upsert operations will update existing records instead of creating duplicates")

if __name__ == "__main__":
    test_unique_constraint()

