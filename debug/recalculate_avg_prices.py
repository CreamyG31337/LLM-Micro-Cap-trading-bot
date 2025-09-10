#!/usr/bin/env python3
"""
Recalculate Average Prices from Trade Log

This script recalculates all average prices in the portfolio CSV based on the actual
trade log data. Use this when:
- You manually edit the trade log
- You suspect the portfolio CSV has stale data
- You want to verify price calculations are correct

Usage:
    python debug/recalculate_avg_prices.py
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict
import sys

def recalculate_average_prices(data_dir: str = "my trading"):
    """Recalculate average prices from trade log and update portfolio CSV"""
    
    data_path = Path(data_dir)
    trade_log_file = data_path / "llm_trade_log.csv"
    portfolio_file = data_path / "llm_portfolio_update.csv"
    
    if not trade_log_file.exists():
        print(f"❌ Trade log not found: {trade_log_file}")
        return False
    
    if not portfolio_file.exists():
        print(f"❌ Portfolio file not found: {portfolio_file}")
        return False
    
    try:
        # Read trade log
        trade_df = pd.read_csv(trade_log_file)
        print(f"📊 Loaded {len(trade_df)} trades from trade log")
        
        # Read portfolio
        portfolio_df = pd.read_csv(portfolio_file)
        print(f"📊 Loaded {len(portfolio_df)} portfolio entries")
        
        # Calculate average prices from trade log
        ticker_data = defaultdict(lambda: {'total_shares': 0, 'total_cost': 0, 'trades': []})
        
        for _, trade in trade_df.iterrows():
            ticker = trade['Ticker']
            shares = float(trade['Shares Bought'])
            price = float(trade['Buy Price'])
            cost = float(trade['Cost Basis'])
            
            ticker_data[ticker]['total_shares'] += shares
            ticker_data[ticker]['total_cost'] += cost
            ticker_data[ticker]['trades'].append({
                'shares': shares,
                'price': price,
                'cost': cost
            })
        
        print(f"\n📈 Calculated averages from trade log:")
        for ticker, data in ticker_data.items():
            if data['total_shares'] > 0:
                avg_price = data['total_cost'] / data['total_shares']
                print(f"   {ticker}: {data['total_shares']:.4f} shares, ${data['total_cost']:.2f} cost, ${avg_price:.2f} avg")
        
        # Update portfolio with recalculated averages
        updated_count = 0
        changes_made = []
        
        for idx, row in portfolio_df.iterrows():
            ticker = row['Ticker']
            
            if ticker in ticker_data and ticker_data[ticker]['total_shares'] > 0:
                old_avg_price = row['Average Price']
                new_avg_price = ticker_data[ticker]['total_cost'] / ticker_data[ticker]['total_shares']
                
                # Update the average price
                portfolio_df.at[idx, 'Average Price'] = round(new_avg_price, 2)
                
                # Recalculate cost basis to match
                shares = float(row['Shares'])
                new_cost_basis = shares * new_avg_price
                old_cost_basis = row['Cost Basis']
                portfolio_df.at[idx, 'Cost Basis'] = round(new_cost_basis, 2)
                
                # Track changes
                price_diff = abs(old_avg_price - new_avg_price)
                cost_diff = abs(old_cost_basis - new_cost_basis)
                
                if price_diff > 0.01 or cost_diff > 0.01:  # Only show if significant change
                    changes_made.append({
                        'ticker': ticker,
                        'old_price': old_avg_price,
                        'new_price': new_avg_price,
                        'old_cost': old_cost_basis,
                        'new_cost': new_cost_basis,
                        'price_diff': price_diff,
                        'cost_diff': cost_diff
                    })
                    updated_count += 1
        
        # Show detailed changes
        if changes_made:
            print(f"\n🔄 Changes made to {updated_count} entries:")
            for change in changes_made:
                print(f"   {change['ticker']}:")
                print(f"     Price: ${change['old_price']:.2f} → ${change['new_price']:.2f} (${change['price_diff']:.2f} diff)")
                print(f"     Cost:  ${change['old_cost']:.2f} → ${change['new_cost']:.2f} (${change['cost_diff']:.2f} diff)")
        else:
            print(f"\n✅ No changes needed - all prices are already accurate")
        
        # Save updated portfolio
        portfolio_df.to_csv(portfolio_file, index=False)
        
        print(f"\n✅ Portfolio updated and saved to: {portfolio_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error recalculating prices: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to recalculate average prices"""
    print("🔄 Recalculating Average Prices from Trade Log")
    print("=" * 50)
    
    # Check if data directory argument provided
    data_dir = "my trading"
    if len(sys.argv) > 1:
        data_dir = sys.argv[1]
    
    print(f"📁 Using data directory: {data_dir}")
    
    success = recalculate_average_prices(data_dir)
    
    if success:
        print("\n🎉 Average prices recalculated successfully!")
        print("   All prices are now accurate based on the trade log")
    else:
        print("\n❌ Failed to recalculate average prices")
        sys.exit(1)

if __name__ == "__main__":
    main()
