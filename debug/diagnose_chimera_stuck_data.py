"""Diagnostic script to check why Project Chimera fund is stuck with old data."""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, date

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from web_dashboard.supabase_client import SupabaseClient

def main():
    fund_name = "Project Chimera"
    print(f"\n{'='*60}")
    print(f"DIAGNOSING: {fund_name} - Stuck with Old Data")
    print(f"{'='*60}\n")
    
    client = SupabaseClient(use_service_role=True)
    
    # 1. Check if fund is marked as production
    print("1. Checking fund production status...")
    try:
        fund_result = client.supabase.table("funds")\
            .select("name, is_production, base_currency")\
            .eq("name", fund_name)\
            .execute()
        
        if not fund_result.data:
            print(f"   [FAIL] Fund '{fund_name}' NOT FOUND in database!")
            return
        else:
            fund = fund_result.data[0]
            is_prod = fund.get('is_production', False)
            base_currency = fund.get('base_currency', 'CAD')
            print(f"   [OK] Fund found: {fund_name}")
            print(f"   Production flag: {is_prod}")
            print(f"   Base currency: {base_currency}")
            if not is_prod:
                print(f"   [WARNING] Fund is NOT marked as production!")
                print(f"      The update job only processes production funds.")
    except Exception as e:
        print(f"   [FAIL] Error checking fund: {e}")
        return
    
    # 2. Check recent job executions
    print(f"\n2. Checking recent job executions for 'update_portfolio_prices'...")
    try:
        job_result = client.supabase.table("job_executions")\
            .select("*")\
            .eq("job_name", "update_portfolio_prices")\
            .order("completed_at", desc=True)\
            .limit(10)\
            .execute()
        
        if job_result.data:
            print(f"   [OK] Found {len(job_result.data)} recent executions:")
            for i, exec in enumerate(job_result.data[:5], 1):
                status = exec.get('status', 'unknown')
                completed_at = exec.get('completed_at', 'N/A')
                error_msg = exec.get('error_message', '')
                funds_processed = exec.get('funds_processed', [])
                duration_ms = exec.get('duration_ms', 0)
                
                status_icon = "[OK]" if status == "success" else "[FAIL]" if status == "failed" else "[RUN]"
                print(f"   {i}. {status_icon} {status.upper()} - {completed_at}")
                print(f"      Duration: {duration_ms}ms")
                if funds_processed:
                    print(f"      Funds processed: {funds_processed}")
                    if fund_name in funds_processed:
                        print(f"      [OK] {fund_name} was processed")
                    else:
                        print(f"      [WARNING] {fund_name} was NOT in the processed list!")
                if error_msg:
                    print(f"      Error: {error_msg[:100]}")
        else:
            print(f"   [WARNING] No recent job executions found!")
    except Exception as e:
        print(f"   [FAIL] Error checking job executions: {e}")
    
    # 3. Check trade log data
    print(f"\n3. Checking trade log data...")
    try:
        trades_result = client.supabase.table("trade_log")\
            .select("date, ticker, shares, price", count='exact')\
            .eq("fund", fund_name)\
            .order("date", desc=True)\
            .limit(5)\
            .execute()
        
        print(f"   Total trades: {trades_result.count if hasattr(trades_result, 'count') else 'unknown'}")
        if trades_result.data:
            print(f"   [OK] Found trades - showing 5 most recent:")
            for trade in trades_result.data:
                print(f"      {trade.get('date')}: {trade.get('ticker')} - {trade.get('shares')} shares @ ${trade.get('price')}")
        else:
            print(f"   [WARNING] No trades found for {fund_name}!")
    except Exception as e:
        print(f"   [FAIL] Error checking trades: {e}")
    
    # 4. Check latest positions in portfolio_positions
    print(f"\n4. Checking latest positions in portfolio_positions...")
    try:
        # Get most recent date
        latest_date_result = client.supabase.table("portfolio_positions")\
            .select("date")\
            .eq("fund", fund_name)\
            .order("date", desc=True)\
            .limit(1)\
            .execute()
        
        if latest_date_result.data:
            latest_date = latest_date_result.data[0]['date']
            print(f"   [OK] Most recent position date: {latest_date}")
            
            # Check how old this is
            if isinstance(latest_date, str):
                latest_date_obj = datetime.fromisoformat(latest_date.replace('Z', '+00:00')).date()
            else:
                latest_date_obj = latest_date if isinstance(latest_date, date) else latest_date.date()
            
            today = date.today()
            days_old = (today - latest_date_obj).days
            print(f"   Days since last update: {days_old}")
            
            if days_old > 1:
                print(f"   [WARNING] Data is {days_old} days old!")
            
            # Get positions for that date
            positions_result = client.supabase.table("portfolio_positions")\
                .select("ticker, shares, price, date")\
                .eq("fund", fund_name)\
                .eq("date", latest_date)\
                .limit(10)\
                .execute()
            
            if positions_result.data:
                print(f"   Found {len(positions_result.data)} positions (showing first 10):")
                for pos in positions_result.data[:10]:
                    print(f"      {pos.get('ticker')}: {pos.get('shares')} shares @ ${pos.get('price')}")
        else:
            print(f"   [FAIL] No positions found in portfolio_positions for {fund_name}!")
    except Exception as e:
        print(f"   [FAIL] Error checking positions: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Check for recent dates (last 7 days)
    print(f"\n5. Checking positions for last 7 days...")
    try:
        seven_days_ago = (date.today() - timedelta(days=7)).isoformat()
        recent_positions = client.supabase.table("portfolio_positions")\
            .select("date", count='exact')\
            .eq("fund", fund_name)\
            .gte("date", seven_days_ago)\
            .order("date", desc=True)\
            .execute()
        
        if recent_positions.data:
            dates = sorted(set([p['date'] for p in recent_positions.data]), reverse=True)
            print(f"   [OK] Found positions for {len(dates)} unique dates in last 7 days:")
            for d in dates[:5]:
                count = sum(1 for p in recent_positions.data if p['date'] == d)
                print(f"      {d}: {count} positions")
        else:
            print(f"   [WARNING] No positions found in the last 7 days!")
    except Exception as e:
        print(f"   [FAIL] Error checking recent dates: {e}")
    
    # 6. Check latest_positions view
    print(f"\n6. Checking latest_positions view...")
    try:
        latest_view = client.supabase.table("latest_positions")\
            .select("ticker, date, current_price, shares")\
            .eq("fund", fund_name)\
            .limit(5)\
            .execute()
        
        if latest_view.data:
            print(f"   [OK] Found {len(latest_view.data)} positions in latest_positions view:")
            for pos in latest_view.data:
                pos_date = pos.get('date', 'N/A')
                print(f"      {pos.get('ticker')}: {pos.get('shares')} shares @ ${pos.get('current_price')} (date: {pos_date})")
        else:
            print(f"   [WARNING] No positions in latest_positions view!")
    except Exception as e:
        print(f"   [FAIL] Error checking latest_positions view: {e}")
    
    # 7. Summary and recommendations
    print(f"\n{'='*60}")
    print(f"SUMMARY & RECOMMENDATIONS")
    print(f"{'='*60}\n")
    
    # Re-check key findings
    fund_is_prod = fund.get('is_production', False) if 'fund' in locals() else False
    has_recent_jobs = len(job_result.data) > 0 if 'job_result' in locals() and job_result.data else False
    fund_was_processed = False
    if 'job_result' in locals() and job_result.data:
        for exec in job_result.data:
            funds_processed = exec.get('funds_processed', [])
            if fund_name in funds_processed:
                fund_was_processed = True
                break
    
    if not fund_is_prod:
        print("[FAIL] ISSUE FOUND: Fund is not marked as production!")
        print("   -> Fix: Run SQL: UPDATE funds SET is_production = true WHERE name = 'Project Chimera';")
    elif not has_recent_jobs:
        print("[FAIL] ISSUE FOUND: No recent job executions found!")
        print("   -> Check: Is the scheduler running? Check admin logs.")
    elif not fund_was_processed:
        print("[FAIL] ISSUE FOUND: Fund was not in the processed funds list!")
        print("   -> Possible causes:")
        print("     - Error during processing (check logs)")
        print("     - No trades found")
        print("     - No active positions")
        print("     - All price fetches failed")
    else:
        print("[OK] Fund appears to be configured correctly.")
        print("   -> Check: Recent positions may be old due to:")
        print("     - Job running but failing silently")
        print("     - Price fetch failures")
        print("     - Database upsert errors")
    
    print(f"\n{'='*60}\n")

if __name__ == "__main__":
    main()

