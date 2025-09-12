#!/usr/bin/env python3
"""
Demo script showing how FIFO system integrates with existing portfolio.

This demonstrates:
1. How to use FIFO system with your current data
2. Realized P&L tracking
3. Integration with existing trade log
"""

import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from data.repositories.repository_factory import RepositoryFactory
from portfolio.fifo_trade_processor import FIFOTradeProcessor


def demo_fifo_integration():
    """Demonstrate FIFO integration with existing system."""
    
    print("🔄 FIFO Integration Demo")
    print("=" * 40)
    
    # Initialize system
    settings = Settings()
    repository = RepositoryFactory.create_repository('csv', data_directory=settings.get_data_directory())
    fifo_processor = FIFOTradeProcessor(repository)
    
    print(f"📁 Data directory: {settings.get_data_directory()}")
    
    # Show current realized P&L summary
    print("\n📊 Current Realized P&L Summary")
    print("-" * 35)
    
    summary = fifo_processor.get_realized_pnl_summary()
    print(f"Total realized P&L: ${summary['total_realized_pnl']:.2f}")
    print(f"Total shares sold: {summary['total_shares_sold']}")
    print(f"Total proceeds: ${summary['total_proceeds']:.2f}")
    print(f"Average sell price: ${summary['average_sell_price']:.2f}")
    print(f"Number of sales: {summary['number_of_sales']}")
    
    # Show per-ticker breakdown
    print("\n📈 Per-Ticker Breakdown")
    print("-" * 25)
    
    # Get all unique tickers from trade log
    all_trades = repository.get_trade_history()
    tickers = list(set(trade.ticker for trade in all_trades))
    
    for ticker in sorted(tickers):
        ticker_summary = fifo_processor.get_realized_pnl_summary(ticker)
        if ticker_summary['number_of_sales'] > 0:
            print(f"{ticker}:")
            print(f"  Realized P&L: ${ticker_summary['total_realized_pnl']:.2f}")
            print(f"  Shares sold: {ticker_summary['total_shares_sold']}")
            print(f"  Avg sell price: ${ticker_summary['average_sell_price']:.2f}")
            print(f"  Sales count: {ticker_summary['number_of_sales']}")
    
    # Demonstrate how to add realized P&L to portfolio display
    print("\n💡 Integration with Portfolio Display")
    print("-" * 40)
    print("To add realized P&L to your portfolio display, you would:")
    print("1. Call fifo_processor.get_realized_pnl_summary()")
    print("2. Add a 'Realized P&L' section to the portfolio table")
    print("3. Show both unrealized (current positions) and realized (sold positions)")
    print("4. Calculate total portfolio performance including both")
    
    # Show example of how to integrate
    print("\n🔧 Example Integration Code:")
    print("-" * 30)
    print("""
# In your portfolio display code:
realized_summary = fifo_processor.get_realized_pnl_summary()
total_realized_pnl = realized_summary['total_realized_pnl']

# Add to portfolio statistics
stats_data = {
    'total_realized_pnl': total_realized_pnl,
    'total_unrealized_pnl': current_unrealized_pnl,
    'total_portfolio_pnl': total_realized_pnl + current_unrealized_pnl
}

# Display in table
print(f"Realized P&L: ${total_realized_pnl:+,.2f}")
print(f"Unrealized P&L: ${current_unrealized_pnl:+,.2f}")
print(f"Total P&L: ${total_realized_pnl + current_unrealized_pnl:+,.2f}")
""")


def demo_fifo_vs_average_cost():
    """Show the difference between FIFO and average cost methods."""
    
    print("\n⚖️ FIFO vs Average Cost Comparison")
    print("=" * 40)
    
    print("Scenario: Buy 100 shares at $100, then 100 shares at $120")
    print("Then sell 100 shares at $130")
    print()
    
    # FIFO method
    print("FIFO Method:")
    print("  - Sells oldest shares first (100 @ $100)")
    print("  - Realized P&L: (130 - 100) × 100 = $3,000")
    print("  - Remaining: 100 shares @ $120")
    print("  - Remaining cost basis: $12,000")
    print()
    
    # Average cost method
    print("Average Cost Method:")
    print("  - Average price: (100×100 + 100×120) / 200 = $110")
    print("  - Realized P&L: (130 - 110) × 100 = $2,000")
    print("  - Remaining: 100 shares @ $110")
    print("  - Remaining cost basis: $11,000")
    print()
    
    print("Key Differences:")
    print("• FIFO: Higher realized P&L, lower remaining cost basis")
    print("• Average: Lower realized P&L, higher remaining cost basis")
    print("• FIFO: Tax-advantaged (longer holding periods)")
    print("• Average: Simpler calculation")
    print("• FIFO: Industry standard for professional trading")


if __name__ == "__main__":
    demo_fifo_integration()
    demo_fifo_vs_average_cost()
    
    print("\n🎯 Next Steps:")
    print("1. Integrate FIFO processor into trading_script.py")
    print("2. Add realized P&L display to portfolio summary")
    print("3. Update trade execution to use FIFO method")
    print("4. Add lot tracking to CSV storage")
    print("5. Create realized P&L reports")
