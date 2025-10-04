#!/usr/bin/env python3
"""
Check what data is actually in Supabase
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from data.repositories.repository_factory import RepositoryFactory

def check_supabase_data():
    # Load environment variables
    load_dotenv(Path('web_dashboard') / '.env')

    # Create repository
    repository = RepositoryFactory.create_repository(
        'supabase',
        url=os.getenv('SUPABASE_URL'),
        key=os.getenv('SUPABASE_ANON_KEY'),
        fund='Project Chimera'
    )

    # Get a sample of data
    snapshots = repository.get_portfolio_data()
    if snapshots:
        print(f'Found {len(snapshots)} snapshots')
        latest = snapshots[-1]
        print(f'Latest snapshot: {latest.timestamp}')
        if latest.positions:
            pos = latest.positions[0]
            print(f'Sample position: {pos.ticker}')
            print(f'  Shares: {pos.shares}')
            print(f'  Avg Price: {pos.avg_price}')
            print(f'  Current Price: {getattr(pos, "current_price", "NOT SET")}')
            print(f'  Cost Basis: {pos.cost_basis}')
            print(f'  PnL: {getattr(pos, "pnl", "NOT SET")}')
            
            # Check if current_price equals avg_price (which would cause 0% performance)
            current_price = getattr(pos, "current_price", None)
            if current_price and current_price == pos.avg_price:
                print("  ⚠️  Current price equals average price - this causes 0% performance!")
            elif not current_price:
                print("  ⚠️  No current price set - using average price as fallback")
    else:
        print("No snapshots found")

if __name__ == "__main__":
    check_supabase_data()
