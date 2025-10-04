#!/usr/bin/env python3
"""
Debug Trading Script Data - Check exactly what data the trading script gets
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def debug_trading_script_data():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    try:
        from data.repositories.repository_factory import RepositoryFactory

        # Load environment variables
        load_dotenv(project_root / 'web_dashboard' / '.env')

        # Create repository for Project Chimera using Supabase
        repository = RepositoryFactory.create_repository(
            'supabase',
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY'),
            fund='Project Chimera'
        )

        print('=== DEBUGGING TRADING SCRIPT DATA FLOW ===')
        print(f'Repository type: {type(repository).__name__}')
        print(f'Fund: {repository.fund}')
        print()

        # 1. Check current_positions view (what our debug script uses)
        print('=== 1. CURRENT_POSITIONS VIEW DATA ===')
        current_positions = repository.get_current_positions()
        print(f'Records from current_positions view: {len(current_positions)}')
        
        if current_positions:
            first_pos = current_positions[0]
            print(f'Sample current_positions record:')
            for key, value in first_pos.items():
                print(f'  {key}: {value}')
            print()

        # 2. Check latest portfolio snapshot (what trading script might use)
        print('=== 2. LATEST PORTFOLIO SNAPSHOT DATA ===')
        snapshot = repository.get_latest_portfolio_snapshot()
        if snapshot:
            print(f'Snapshot timestamp: {snapshot.timestamp}')
            print(f'Positions in snapshot: {len(snapshot.positions)}')
            print(f'Total value: {snapshot.total_value}')
            
            if snapshot.positions:
                first_snapshot_pos = snapshot.positions[0]
                print(f'Sample snapshot position:')
                print(f'  ticker: {first_snapshot_pos.ticker}')
                print(f'  shares: {first_snapshot_pos.shares}')
                print(f'  avg_price: {first_snapshot_pos.avg_price}')
                print(f'  current_price: {first_snapshot_pos.current_price}')
                print(f'  cost_basis: {first_snapshot_pos.cost_basis}')
                print(f'  market_value: {first_snapshot_pos.market_value}')
                print(f'  unrealized_pnl: {first_snapshot_pos.unrealized_pnl}')
        else:
            print('No portfolio snapshots found!')
        print()

        # 3. Check portfolio positions table directly
        print('=== 3. RAW PORTFOLIO_POSITIONS TABLE ===')
        try:
            # Get raw data from portfolio_positions table
            result = repository.supabase.table("portfolio_positions").select("*").eq("fund", "Project Chimera").order("date", desc=True).limit(5).execute()
            print(f'Raw portfolio_positions records: {len(result.data)}')
            
            if result.data:
                raw_pos = result.data[0]
                print(f'Sample raw portfolio_positions record:')
                for key, value in raw_pos.items():
                    print(f'  {key}: {value}')
        except Exception as e:
            print(f'Error accessing raw table: {e}')
        print()

        # 4. Test what the trading script's portfolio manager gets
        print('=== 4. TESTING PORTFOLIO MANAGER DATA ===')
        try:
            from portfolio.portfolio_manager import PortfolioManager
            
            pm = PortfolioManager(repository)
            portfolio_data = pm.load_portfolio()
            
            print(f'Portfolio manager loaded {len(portfolio_data)} snapshots')
            if portfolio_data:
                latest = portfolio_data[-1]
                print(f'Latest snapshot: {latest.timestamp}')
                print(f'Positions: {len(latest.positions)}')
                
                if latest.positions:
                    pos = latest.positions[0]
                    print(f'Sample position from portfolio manager:')
                    print(f'  ticker: {pos.ticker}')
                    print(f'  current_price: {pos.current_price}')
                    print(f'  avg_price: {pos.avg_price}')
                    print(f'  unrealized_pnl: {pos.unrealized_pnl}')
                    print(f'  market_value: {pos.market_value}')
        except Exception as e:
            print(f'Error testing portfolio manager: {e}')
        print()

        # 5. Calculate totals both ways
        print('=== 5. COMPARING CALCULATION METHODS ===')
        
        # Method 1: Using current_positions view
        if current_positions:
            total_pnl_view = sum(float(pos.get('total_pnl', 0)) for pos in current_positions)
            total_value_view = sum(float(pos.get('total_market_value', 0)) for pos in current_positions)
            total_cost_view = sum(float(pos.get('total_cost_basis', 0)) for pos in current_positions)
            
            print(f'current_positions view totals:')
            print(f'  Total P&L: ${total_pnl_view:.2f}')
            print(f'  Total Value: ${total_value_view:.2f}')
            print(f'  Total Cost: ${total_cost_view:.2f}')
        
        # Method 2: Using latest snapshot
        if snapshot and snapshot.positions:
            total_pnl_snapshot = sum(float(pos.unrealized_pnl or 0) for pos in snapshot.positions)
            total_value_snapshot = sum(float(pos.market_value or 0) for pos in snapshot.positions) 
            total_cost_snapshot = sum(float(pos.cost_basis or 0) for pos in snapshot.positions)
            
            print(f'snapshot positions totals:')
            print(f'  Total P&L: ${total_pnl_snapshot:.2f}')
            print(f'  Total Value: ${total_value_snapshot:.2f}')
            print(f'  Total Cost: ${total_cost_snapshot:.2f}')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_trading_script_data()