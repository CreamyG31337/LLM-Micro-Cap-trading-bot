#!/usr/bin/env python3
"""
Test the portfolio grouping fix to ensure all positions for the day are shown.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from data.repositories.repository_factory import RepositoryFactory

def test_portfolio_fix():
    """Test that the portfolio fix shows all positions for the day."""
    
    print("🔧 Testing Portfolio Grouping Fix")
    print("=" * 40)
    
    # Initialize system
    settings = Settings()
    repository = RepositoryFactory.create_repository('csv', data_directory=settings.get_data_directory())
    
    print(f"📁 Data directory: {settings.get_data_directory()}")
    
    # Get latest portfolio snapshot
    snapshot = repository.get_latest_portfolio_snapshot()
    
    if snapshot:
        print(f"📅 Latest snapshot timestamp: {snapshot.timestamp}")
        print(f"📊 Number of positions: {len(snapshot.positions)}")
        print("\n🏢 Positions in latest snapshot:")
        print("-" * 50)
        
        for i, position in enumerate(snapshot.positions, 1):
            print(f"{i:2d}. {position.ticker:<8} - {position.shares} shares @ ${position.avg_price}")
        
        # Check if HLIT.TO is included
        hlit_positions = [p for p in snapshot.positions if p.ticker == 'HLIT.TO']
        if hlit_positions:
            print(f"\n✅ HLIT.TO found in portfolio: {hlit_positions[0].shares} shares")
        else:
            print("\n❌ HLIT.TO NOT found in portfolio")
            
    else:
        print("❌ No portfolio snapshot found")

if __name__ == "__main__":
    test_portfolio_fix()
