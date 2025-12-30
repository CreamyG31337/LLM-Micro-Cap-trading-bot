
import sys
from pathlib import Path
from statistics import mean, median

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from postgres_client import PostgresClient

def analyze_stats():
    print("Connecting to Postgres...")
    client = PostgresClient()
    
    print("Fetching session stats...")
    sessions = client.execute_query("""
        SELECT 
            id, 
            politician_name, 
            trade_count, 
            start_date, 
            end_date, 
            (end_date - start_date) as duration_days
        FROM congress_trade_sessions
        ORDER BY trade_count DESC
    """)
    
    if not sessions:
        print("No sessions found.")
        return

    trade_counts = [s['trade_count'] for s in sessions]
    durations = [s['duration_days'] for s in sessions]
    
    print(f"\nTotal Sessions: {len(sessions)}")
    print(f"Total Trades Covered: {sum(trade_counts)}")
    
    print(f"\nTrades per Session:")
    print(f"  Average: {mean(trade_counts):.2f}")
    print(f"  Median:  {median(trade_counts):.2f}")
    print(f"  Max:     {max(trade_counts)}")
    print(f"  Min:     {min(trade_counts)}")
    
    print(f"\nSession Duration (Days):")
    print(f"  Average: {mean(durations):.2f}")
    print(f"  Median:  {median(durations):.2f}")
    print(f"  Max:     {max(durations)}")
    
    print("\nTop 5 Largest Sessions (by trade count):")
    for s in sessions[:5]:
        print(f"  - {s['politician_name']}: {s['trade_count']} trades over {s['duration_days']} days ({s['start_date']} to {s['end_date']})")

    # Check for single-trade sessions
    single_trade = len([c for c in trade_counts if c == 1])
    print(f"\nSingle-trade sessions: {single_trade} ({single_trade/len(sessions)*100:.1f}%)")

if __name__ == "__main__":
    analyze_stats()
