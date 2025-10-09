"""
Debug script to investigate FIFO P&L calculation differences between CSV and Supabase.
"""

import os
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
import sys
sys.path.append('.')

from data.repositories.csv_repository import CSVRepository
from data.repositories.supabase_repository import SupabaseRepository
from portfolio.fifo_trade_processor import FIFOTradeProcessor

# Load Supabase credentials
load_dotenv("web_dashboard/.env")

def investigate_fifo_bug():
    """Investigate the FIFO P&L calculation bug."""
    print("=== FIFO BUG INVESTIGATION ===")
    
    # Create temporary directory for CSV tests
    test_data_dir = Path(tempfile.mkdtemp(prefix="debug_fifo_"))
    test_fund = "TEST"
    
    try:
        # Create repositories
        csv_repo = CSVRepository(str(test_data_dir))
        supabase_repo = SupabaseRepository(fund=test_fund)
        
        print(f"CSV Repository: {csv_repo}")
        print(f"Supabase Repository: {supabase_repo}")
        
        # Check existing trades in both repositories
        print("\n=== EXISTING TRADES ===")
        csv_trades = csv_repo.get_trade_history()
        supabase_trades = supabase_repo.get_trade_history()
        
        print(f"CSV existing trades: {len(csv_trades)}")
        for trade in csv_trades:
            print(f"  CSV Trade: {trade.ticker} {trade.action} {trade.shares} @ {trade.price} on {trade.timestamp}")
        
        print(f"Supabase existing trades: {len(supabase_trades)}")
        for trade in supabase_trades:
            print(f"  Supabase Trade: {trade.ticker} {trade.action} {trade.shares} @ {trade.price} on {trade.timestamp}")
        
        # Create FIFO processors
        print("\n=== CREATING FIFO PROCESSORS ===")
        csv_processor = FIFOTradeProcessor(csv_repo)
        supabase_processor = FIFOTradeProcessor(supabase_repo)
        
        # Check lot trackers after initialization
        print(f"CSV lot trackers: {list(csv_processor.lot_trackers.keys())}")
        print(f"Supabase lot trackers: {list(supabase_processor.lot_trackers.keys())}")
        
        # Check FIFO trackers for FIFO ticker
        if "FIFO" in csv_processor.lot_trackers:
            csv_tracker = csv_processor.lot_trackers["FIFO"]
            print(f"CSV FIFO tracker lots: {len(csv_tracker.lots)}")
            for i, lot in enumerate(csv_tracker.lots):
                print(f"  CSV Lot {i}: {lot.shares} shares @ {lot.price} on {lot.purchase_date}")
        
        if "FIFO" in supabase_processor.lot_trackers:
            supabase_tracker = supabase_processor.lot_trackers["FIFO"]
            print(f"Supabase FIFO tracker lots: {len(supabase_tracker.lots)}")
            for i, lot in enumerate(supabase_tracker.lots):
                print(f"  Supabase Lot {i}: {lot.shares} shares @ {lot.price} on {lot.purchase_date}")
        
        # Execute test trades
        print("\n=== EXECUTING TEST TRADES ===")
        test_trades = [
            {
                "ticker": "FIFO",
                "action": "BUY",
                "shares": Decimal("100"),
                "price": Decimal("50.00"),
                "currency": "CAD",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=3)
            },
            {
                "ticker": "FIFO",
                "action": "BUY", 
                "shares": Decimal("50"),
                "price": Decimal("60.00"),
                "currency": "CAD",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=2)
            },
            {
                "ticker": "FIFO",
                "action": "SELL",
                "shares": Decimal("75"),
                "price": Decimal("70.00"),
                "currency": "CAD",
                "timestamp": datetime.now(timezone.utc) - timedelta(days=1)
            }
        ]
        
        for trade_data in test_trades:
            print(f"Executing {trade_data['action']} trade: {trade_data['shares']} {trade_data['ticker']} @ {trade_data['price']}")
            
            if trade_data['action'] == "BUY":
                csv_processor.execute_buy_trade(
                    ticker=trade_data['ticker'],
                    shares=trade_data['shares'],
                    price=trade_data['price'],
                    currency=trade_data['currency']
                )
                supabase_processor.execute_buy_trade(
                    ticker=trade_data['ticker'],
                    shares=trade_data['shares'],
                    price=trade_data['price'],
                    currency=trade_data['currency']
                )
            elif trade_data['action'] == "SELL":
                csv_processor.execute_sell_trade(
                    ticker=trade_data['ticker'],
                    shares=trade_data['shares'],
                    price=trade_data['price'],
                    currency=trade_data['currency']
                )
                supabase_processor.execute_sell_trade(
                    ticker=trade_data['ticker'],
                    shares=trade_data['shares'],
                    price=trade_data['price'],
                    currency=trade_data['currency']
                )
        
        # Check lot trackers after trades
        print("\n=== LOT TRACKERS AFTER TRADES ===")
        if "FIFO" in csv_processor.lot_trackers:
            csv_tracker = csv_processor.lot_trackers["FIFO"]
            print(f"CSV FIFO tracker lots: {len(csv_tracker.lots)}")
            for i, lot in enumerate(csv_tracker.lots):
                print(f"  CSV Lot {i}: {lot.shares} shares @ {lot.price} on {lot.purchase_date}")
        
        if "FIFO" in supabase_processor.lot_trackers:
            supabase_tracker = supabase_processor.lot_trackers["FIFO"]
            print(f"Supabase FIFO tracker lots: {len(supabase_tracker.lots)}")
            for i, lot in enumerate(supabase_tracker.lots):
                print(f"  Supabase Lot {i}: {lot.shares} shares @ {lot.price} on {lot.purchase_date}")
        
        # Get P&L summaries
        print("\n=== P&L SUMMARIES ===")
        csv_pnl_summary = csv_processor.get_realized_pnl_summary("FIFO")
        supabase_pnl_summary = supabase_processor.get_realized_pnl_summary("FIFO")
        
        print(f"CSV P&L Summary: {csv_pnl_summary}")
        print(f"Supabase P&L Summary: {supabase_pnl_summary}")
        
        # Check trade history after execution
        print("\n=== TRADE HISTORY AFTER EXECUTION ===")
        csv_trades_after = csv_repo.get_trade_history()
        supabase_trades_after = supabase_repo.get_trade_history()
        
        print(f"CSV trades after: {len(csv_trades_after)}")
        for trade in csv_trades_after:
            print(f"  CSV Trade: {trade.ticker} {trade.action} {trade.shares} @ {trade.price} on {trade.timestamp}")
        
        print(f"Supabase trades after: {len(supabase_trades_after)}")
        for trade in supabase_trades_after:
            print(f"  Supabase Trade: {trade.ticker} {trade.action} {trade.shares} @ {trade.price} on {trade.timestamp}")
        
    finally:
        # Cleanup
        if test_data_dir.exists():
            try:
                shutil.rmtree(test_data_dir)
            except PermissionError:
                pass

if __name__ == "__main__":
    investigate_fifo_bug()
