"""Test and debug update_portfolio_prices job until it works perfectly."""
import sys
from pathlib import Path
from datetime import datetime, timedelta, date
import time

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from web_dashboard.supabase_client import SupabaseClient
from web_dashboard.scheduler.jobs_portfolio import update_portfolio_prices_job, backfill_portfolio_prices_range
from utils.market_holidays import MarketHolidays
import pandas as pd

def wipe_portfolio_data(fund_name: str, start_date: date, end_date: date) -> int:
    """Delete portfolio_positions data for a date range (DO NOT touch trade_log)."""
    client = SupabaseClient(use_service_role=True)
    
    print(f"\n[WIPE] Wiping portfolio_positions data for {fund_name} from {start_date} to {end_date}...")
    
    deleted_count = 0
    start_of_range = datetime.combine(start_date, datetime.min.time()).isoformat()
    end_of_range = datetime.combine(end_date, datetime.max.time()).isoformat()
    
    # Paginated delete (Supabase limit is 1000 rows per request)
    while True:
        # Get batch of IDs to delete
        result = client.supabase.table("portfolio_positions")\
            .select("id")\
            .eq("fund", fund_name)\
            .gte("date", start_of_range)\
            .lte("date", end_of_range)\
            .limit(1000)\
            .execute()
        
        if not result.data:
            break
        
        ids_to_delete = [row['id'] for row in result.data]
        
        # Delete this batch
        delete_result = client.supabase.table("portfolio_positions")\
            .delete()\
            .in_("id", ids_to_delete)\
            .execute()
        
        batch_deleted = len(delete_result.data) if delete_result.data else len(ids_to_delete)
        deleted_count += batch_deleted
        print(f"   Deleted {batch_deleted} positions (total: {deleted_count})")
        
        if len(result.data) < 1000:
            break
    
    print(f"[OK] Deleted {deleted_count} total positions")
    return deleted_count

def check_data_exists(fund_name: str, start_date: date, end_date: date) -> dict:
    """Check what dates have data."""
    client = SupabaseClient(use_service_role=True)
    market_holidays = MarketHolidays()
    
    # Get all dates with data
    all_rows = []
    batch_size = 1000
    offset = 0
    
    start_of_range = datetime.combine(start_date, datetime.min.time()).isoformat()
    end_of_range = datetime.combine(end_date, datetime.max.time()).isoformat()
    
    while True:
        result = client.supabase.table("portfolio_positions")\
            .select("date")\
            .eq("fund", fund_name)\
            .gte("date", start_of_range)\
            .lte("date", end_of_range)\
            .order("date")\
            .range(offset, offset + batch_size - 1)\
            .execute()
        
        if not result.data:
            break
        
        all_rows.extend(result.data)
        if len(result.data) < batch_size:
            break
        offset += batch_size
    
    if not all_rows:
        return {
            'dates_with_data': [],
            'total_positions': 0,
            'missing_trading_days': []
        }
    
    df = pd.DataFrame(all_rows)
    df['date'] = pd.to_datetime(df['date']).dt.date
    dates_with_data = sorted(set(df['date'].tolist()))
    
    # Find missing trading days
    missing_days = []
    if dates_with_data:
        current = start_date
        while current <= end_date:
            if market_holidays.is_trading_day(current, market="any"):
                if current not in dates_with_data:
                    missing_days.append(current)
            current += timedelta(days=1)
    
    return {
        'dates_with_data': dates_with_data,
        'total_positions': len(all_rows),
        'missing_trading_days': missing_days
    }

def check_job_executions() -> list:
    """Check recent job executions."""
    client = SupabaseClient(use_service_role=True)
    
    result = client.supabase.table("job_executions")\
        .select("target_date, status, completed_at, duration_ms, error_message, funds_processed")\
        .eq("job_name", "update_portfolio_prices")\
        .order("completed_at", desc=True)\
        .limit(5)\
        .execute()
    
    return result.data if result.data else []

def main():
    fund_name = "Project Chimera"
    start_date = date(2025, 12, 17)
    end_date = date.today()
    
    print(f"\n{'='*80}")
    print(f"TESTING update_portfolio_prices JOB - {fund_name}")
    print(f"Date range: {start_date} to {end_date}")
    print(f"{'='*80}\n")
    
    iteration = 1
    max_iterations = 5  # Reduced since it's working
    
    while iteration <= max_iterations:
        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}/{max_iterations}")
        print(f"{'='*80}\n")
        
        # Step 1: Wipe data
        print("STEP 1: Wiping existing data...")
        deleted = wipe_portfolio_data(fund_name, start_date, end_date)
        print(f"   Deleted {deleted} positions\n")
        
        # Step 2: Check initial state
        print("STEP 2: Checking initial state (should be empty)...")
        initial_state = check_data_exists(fund_name, start_date, end_date)
        print(f"   Dates with data: {len(initial_state['dates_with_data'])}")
        print(f"   Total positions: {initial_state['total_positions']}")
        if initial_state['dates_with_data']:
            print(f"   [WARNING] Data still exists after wipe!")
            print(f"   Dates: {initial_state['dates_with_data'][:5]}...")
        
        # Step 3: Run the update job (should auto-detect and backfill missing dates)
        print(f"\nSTEP 3: Running update_portfolio_prices_job (should auto-backfill missing dates)...")
        start_time = time.time()
        try:
            # Run for today - it should detect missing dates and backfill automatically
            update_portfolio_prices_job(target_date=None)
            duration = time.time() - start_time
            print(f"   [OK] Job completed in {duration:.2f}s")
        except Exception as e:
            duration = time.time() - start_time
            print(f"   [FAIL] Job failed after {duration:.2f}s: {e}")
            import traceback
            traceback.print_exc()
        
        # Step 4: Check job executions
        print(f"\nSTEP 4: Checking job_executions...")
        executions = check_job_executions()
        if executions:
            latest = executions[0]
            print(f"   Latest execution:")
            print(f"      Target date: {latest.get('target_date')}")
            print(f"      Status: {latest.get('status')}")
            print(f"      Duration: {latest.get('duration_ms', 0)}ms")
            print(f"      Funds processed: {latest.get('funds_processed', [])}")
            if latest.get('error_message'):
                print(f"      Error: {latest.get('error_message')}")
        else:
            print(f"   [WARNING] No job executions found!")
        
        # Step 5: Check data after job
        print(f"\nSTEP 5: Checking data after job run...")
        time.sleep(2)  # Give database a moment to update
        final_state = check_data_exists(fund_name, start_date, end_date)
        print(f"   Dates with data: {len(final_state['dates_with_data'])}")
        print(f"   Total positions: {final_state['total_positions']}")
        
        if final_state['dates_with_data']:
            print(f"   First date: {final_state['dates_with_data'][0]}")
            print(f"   Last date: {final_state['dates_with_data'][-1]}")
        
        if final_state['missing_trading_days']:
            print(f"   [WARNING] Missing {len(final_state['missing_trading_days'])} trading days:")
            for missing_day in final_state['missing_trading_days'][:10]:
                print(f"      - {missing_day}")
            if len(final_state['missing_trading_days']) > 10:
                print(f"      ... and {len(final_state['missing_trading_days']) - 10} more")
        else:
            print(f"   [OK] All trading days have data!")
        
        # Step 6: Evaluate
        print(f"\nSTEP 6: Evaluation...")
        if final_state['missing_trading_days']:
            print(f"   [FAIL] FAILED: Missing {len(final_state['missing_trading_days'])} trading days")
            print(f"   Will retry in next iteration...\n")
            iteration += 1
            time.sleep(5)  # Brief pause before next iteration
        else:
            print(f"   [OK] SUCCESS: All trading days have data!")
            print(f"   Total positions created: {final_state['total_positions']}")
            print(f"   Date range covered: {final_state['dates_with_data'][0]} to {final_state['dates_with_data'][-1]}")
            print(f"\n{'='*80}")
            print(f"JOB IS WORKING CORRECTLY!")
            print(f"{'='*80}\n")
            break
    
    if iteration > max_iterations:
        print(f"\n{'='*80}")
        print(f"MAX ITERATIONS REACHED - JOB STILL NOT WORKING")
        print(f"{'='*80}\n")

if __name__ == "__main__":
    main()

