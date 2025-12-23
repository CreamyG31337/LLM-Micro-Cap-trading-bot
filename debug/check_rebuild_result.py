import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.supabase_client import SupabaseClient

client = SupabaseClient()

# Check portfolio positions
positions = client.supabase.table('portfolio_positions') \
    .select('count', count='exact') \
    .eq('fund', 'Project Chimera') \
    .execute()

print(f"Portfolio positions for Project Chimera: {positions.count}")

# Check trades
trades = client.supabase.table('trade_log') \
    .select('count', count='exact') \
    .eq('fund', 'Project Chimera') \
    .execute()

print(f"Trades for Project Chimera: {trades.count}")

if positions.count == 0 and trades.count > 0:
    print("\n❌ PROBLEM: Trades exist but no positions were created by rebuild!")
    print("The rebuild script likely failed. Check the admin logs.")
elif positions.count > 0:
    print(f"\n✅ Rebuild succeeded - {positions.count} positions created")
