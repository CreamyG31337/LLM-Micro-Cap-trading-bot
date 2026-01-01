#!/usr/bin/env python3
"""
Monitor Congress Trades Analysis Progress
==========================================

Shows real-time progress of the analysis script including:
- Trades processed recently
- Processing rate
- Estimated time remaining
- Current status
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent.parent))

from postgres_client import PostgresClient
from supabase_client import SupabaseClient

def format_time_ago(dt):
    """Format datetime as time ago"""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return str(dt)
    
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    delta = now - dt
    
    if delta.total_seconds() < 60:
        return f"{int(delta.total_seconds())}s ago"
    elif delta.total_seconds() < 3600:
        return f"{int(delta.total_seconds() / 60)}m ago"
    else:
        return f"{int(delta.total_seconds() / 3600)}h ago"

def get_recent_analyses(pg, minutes=30):
    """Get recent analysis records"""
    cutoff = datetime.now() - timedelta(minutes=minutes)
    result = pg.execute_query(
        'SELECT trade_id, conflict_score, analyzed_at, model_used '
        'FROM congress_trades_analysis '
        'WHERE analyzed_at > %s '
        'ORDER BY analyzed_at DESC',
        (cutoff,)
    )
    return result if result else []

def get_trade_details(supabase, trade_ids):
    """Get trade details from Supabase"""
    if not trade_ids:
        return {}
    
    details = {}
    batch_size = 100
    
    for i in range(0, len(trade_ids), batch_size):
        batch = trade_ids[i:i+batch_size]
        try:
            result = supabase.supabase.table('congress_trades_enriched')\
                .select('id, politician, ticker, transaction_date')\
                .in_('id', batch)\
                .execute()
            
            for trade in result.data:
                details[trade['id']] = trade
        except Exception as e:
            print(f"  [WARNING] Error fetching trade details: {e}")
    
    return details

def check_log_file():
    """Check the log file for recent activity"""
    log_path = Path(__file__).parent.parent.parent / 'congress_analysis.log'
    if not log_path.exists():
        return None, None
    
    try:
        lines = log_path.read_text(encoding='utf-8', errors='replace').split('\n')
        recent_lines = [l for l in lines[-50:] if l.strip()]
        
        # Find last "Processing batch" message
        last_batch = None
        for line in reversed(recent_lines):
            if 'Processing batch' in line:
                last_batch = line
                break
        
        # Find last "Analyzing" message
        last_analyzing = None
        for line in reversed(recent_lines):
            if 'Analyzing' in line and ' - ' in line:
                last_analyzing = line
                break
        
        return last_batch, last_analyzing
    except Exception as e:
        return None, f"Error reading log: {e}"

def main():
    print("=" * 70)
    print("CONGRESS TRADES ANALYSIS MONITOR")
    print("=" * 70)
    print()
    
    pg = PostgresClient()
    supabase = SupabaseClient()
    
    # Get recent analyses
    print("📊 Recent Activity (last 30 minutes):")
    print("-" * 70)
    
    recent = get_recent_analyses(pg, minutes=30)
    
    if not recent:
        print("  ⚠️  No analyses in the last 30 minutes")
        print("  The script may not be running or is processing very slowly")
    else:
        # Calculate processing rate
        if len(recent) > 1:
            first_time = recent[-1]['analyzed_at']
            last_time = recent[0]['analyzed_at']
            
            if isinstance(first_time, str):
                first_time = datetime.fromisoformat(first_time.replace('Z', '+00:00'))
            if isinstance(last_time, str):
                last_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
            
            time_span = (last_time - first_time).total_seconds() / 60  # minutes
            rate = len(recent) / time_span if time_span > 0 else 0
            
            print(f"  ✅ Processed: {len(recent)} trades")
            print(f"  ⏱️  Rate: {rate:.2f} trades/minute ({rate * 60:.1f} trades/hour)")
            print(f"  📅 Time span: {time_span:.1f} minutes")
        else:
            print(f"  ✅ Processed: {len(recent)} trade")
        
        # Get trade details for recent analyses
        trade_ids = [r['trade_id'] for r in recent[:20]]  # Last 20
        trade_details = get_trade_details(supabase, trade_ids)
        
        print()
        print("📋 Recent Trades Analyzed:")
        print("-" * 70)
        
        for i, analysis in enumerate(recent[:10], 1):
            trade_id = analysis['trade_id']
            trade = trade_details.get(trade_id, {})
            politician = trade.get('politician', 'Unknown')
            ticker = trade.get('ticker', 'Unknown')
            score = analysis.get('conflict_score', 'N/A')
            analyzed_at = analysis.get('analyzed_at')
            
            time_ago = format_time_ago(analyzed_at) if analyzed_at else 'Unknown'
            
            print(f"  {i:2d}. {politician[:25]:<25} - {ticker:<6} | Score: {score} | {time_ago}")
    
    # Check log file
    print()
    print("📝 Log File Status:")
    print("-" * 70)
    last_batch, last_analyzing = check_log_file()
    
    if last_batch:
        # Extract timestamp
        try:
            timestamp_str = last_batch.split(' - ')[0]
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            time_ago = format_time_ago(timestamp)
            print(f"  Last batch: {time_ago}")
            print(f"  {last_batch}")
        except:
            print(f"  {last_batch}")
    
    if last_analyzing:
        try:
            timestamp_str = last_analyzing.split(' - ')[0]
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            time_ago = format_time_ago(timestamp)
            print(f"  Currently analyzing: {time_ago}")
            # Extract politician and ticker
            if 'Analyzing' in last_analyzing and ' - ' in last_analyzing:
                parts = last_analyzing.split('Analyzing ')[1].split('...')[0]
                print(f"  {parts}")
        except:
            print(f"  {last_analyzing}")
    
    # Overall statistics
    print()
    print("📈 Overall Statistics:")
    print("-" * 70)
    
    total_result = pg.execute_query(
        'SELECT COUNT(*) as total FROM congress_trades_analysis'
    )
    total = total_result[0]['total'] if total_result else 0
    
    recent_total = pg.execute_query(
        'SELECT COUNT(*) as total FROM congress_trades_analysis WHERE analyzed_at > %s',
        (datetime.now() - timedelta(hours=24),)
    )
    last_24h = recent_total[0]['total'] if recent_total else 0
    
    print(f"  Total analyses in database: {total:,}")
    print(f"  Analyzed in last 24 hours: {last_24h:,}")
    
    # Estimate remaining (if we know target)
    if recent and len(recent) > 1:
        # Rough estimate: if we're targeting 3,262 trades and have processed some
        # This is just a rough guide
        print()
        print("💡 Note: Processing speed depends on Ollama response times")
        print("   The script will continue until all trades are processed")
    
    print()
    print("=" * 70)
    print("💡 Tip: Run this script periodically to check progress")
    print("   Or use: watch -n 30 python web_dashboard/scripts/monitor_analysis.py")
    print("=" * 70)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

