#!/usr/bin/env python3
"""
Debug Portfolio Summary - Figure out P&L calculation issues
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def debug_portfolio_summary():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    try:
        from data.repositories.repository_factory import RepositoryFactory

        # Load environment variables
        load_dotenv(project_root / 'web_dashboard' / '.env')

        # Create repository for Project Chimera
        repository = RepositoryFactory.create_repository(
            'supabase',
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_ANON_KEY'),
            fund='Project Chimera'
        )

        # Get current positions
        positions = repository.get_current_positions()

        print('=== DEBUG Portfolio Summary ===')
        print(f'Total positions retrieved: {len(positions)}')
        print()

        if positions:
            print('=== Examining first few positions ===')
            for i, pos in enumerate(positions[:3]):
                print(f'\nPosition {i+1}:')
                print(f'  Ticker: {pos.get("ticker")}')
                print(f'  Raw total_pnl: {repr(pos.get("total_pnl"))} (type: {type(pos.get("total_pnl"))})')
                print(f'  Raw total_market_value: {repr(pos.get("total_market_value"))} (type: {type(pos.get("total_market_value"))})')
                print(f'  Raw total_cost_basis: {repr(pos.get("total_cost_basis"))} (type: {type(pos.get("total_cost_basis"))})')
                
                # Try converting to float
                try:
                    pnl_float = float(pos.get('total_pnl', 0))
                    market_value_float = float(pos.get('total_market_value', 0))
                    cost_basis_float = float(pos.get('total_cost_basis', 0))
                    
                    print(f'  Converted total_pnl: ${pnl_float:.2f}')
                    print(f'  Converted total_market_value: ${market_value_float:.2f}')
                    print(f'  Converted total_cost_basis: ${cost_basis_float:.2f}')
                except Exception as e:
                    print(f'  ERROR converting to float: {e}')

            print('\n=== Calculating totals ===')
            
            # Debug the original calculation method
            total_pnl_original = sum(float(pos.get('total_pnl', 0)) for pos in positions)
            total_market_value_original = sum(float(pos.get('total_market_value', 0)) for pos in positions)
            total_cost_basis_original = sum(float(pos.get('total_cost_basis', 0)) for pos in positions)
            
            print(f'Original method:')
            print(f'  Total P&L: ${total_pnl_original:.2f}')
            print(f'  Total Market Value: ${total_market_value_original:.2f}')
            print(f'  Total Cost Basis: ${total_cost_basis_original:.2f}')
            
            # Alternative calculation method
            total_pnl_alt = 0
            total_market_value_alt = 0
            total_cost_basis_alt = 0
            
            for pos in positions:
                pnl = pos.get('total_pnl', 0)
                market_val = pos.get('total_market_value', 0)
                cost_basis = pos.get('total_cost_basis', 0)
                
                if pnl is not None:
                    total_pnl_alt += float(pnl)
                if market_val is not None:
                    total_market_value_alt += float(market_val)
                if cost_basis is not None:
                    total_cost_basis_alt += float(cost_basis)
            
            print(f'\nAlternative method:')
            print(f'  Total P&L: ${total_pnl_alt:.2f}')
            print(f'  Total Market Value: ${total_market_value_alt:.2f}')
            print(f'  Total Cost Basis: ${total_cost_basis_alt:.2f}')
            
            if total_cost_basis_alt > 0:
                pnl_pct = (total_pnl_alt / total_cost_basis_alt * 100)
                print(f'  P&L Percentage: {pnl_pct:.2f}%')

            print('\n=== Individual Position Details ===')
            for pos in positions:
                ticker = pos.get('ticker', 'Unknown')
                pnl = float(pos.get('total_pnl', 0))
                cost_basis = float(pos.get('total_cost_basis', 0))
                market_value = float(pos.get('total_market_value', 0))
                
                pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0
                print(f'  {ticker}: P&L=${pnl:.2f} ({pnl_pct:.2f}%), Market=${market_value:.2f}, Cost=${cost_basis:.2f}')

        else:
            print('No positions found!')

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_portfolio_summary()