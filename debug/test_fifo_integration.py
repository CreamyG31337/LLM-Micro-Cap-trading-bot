#!/usr/bin/env python3
"""
Test FIFO integration with trading script.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from config.settings import Settings
from data.repositories.repository_factory import RepositoryFactory
from portfolio.fifo_trade_processor import FIFOTradeProcessor

def test_fifo_integration():
    """Test FIFO integration."""
    print('🧪 Testing FIFO Integration')
    print('=' * 30)

    # Initialize system
    settings = Settings()
    repository = RepositoryFactory.create_repository('csv', data_directory=settings.get_data_directory())
    fifo_processor = FIFOTradeProcessor(repository)

    print('✅ FIFO processor initialized successfully')

    # Test realized P&L summary
    summary = fifo_processor.get_realized_pnl_summary()
    print(f'📊 Current realized P&L: ${summary["total_realized_pnl"]}')
    print(f'📈 Total sales: {summary["number_of_sales"]}')

    print('✅ FIFO integration test passed!')

if __name__ == "__main__":
    test_fifo_integration()
