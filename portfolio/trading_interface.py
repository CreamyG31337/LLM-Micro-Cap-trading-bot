"""Trading interface module.

This module provides the user interface layer for trading actions,
connecting menu selections to the underlying trade processing functions.
"""

import logging
from decimal import Decimal
from pathlib import Path
from typing import Optional, Dict, Any, List
import pandas as pd

from data.repositories.base_repository import BaseRepository
from portfolio.trade_processor import TradeProcessor
from display.console_output import print_success, print_error, print_info, print_warning

logger = logging.getLogger(__name__)


class TradingInterface:
    """Handles user interface for trading actions."""
    
    def __init__(self, repository: BaseRepository, trade_processor: TradeProcessor):
        """Initialize trading interface.
        
        Args:
            repository: Repository for data access
            trade_processor: Trade processor for executing trades
        """
        self.repository = repository
        self.trade_processor = trade_processor
        logger.info("Trading interface initialized")
    
    def log_contribution(self) -> bool:
        """Handle contribution logging action.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Log Fund Contribution", "_safe_emoji('💵')")
            
            # Get contributor name
            contributor = input("Enter contributor name: ").strip()
            if not contributor:
                print_error("Contributor name cannot be empty")
                return False
            
            # Get contribution amount
            try:
                amount_str = input("Enter contribution amount: $").strip()
                amount = float(amount_str)
                if amount <= 0:
                    print_error("Contribution amount must be positive")
                    return False
            except ValueError:
                print_error("Invalid amount format")
                return False
            
            # Save contribution to CSV
            contribution_data = {
                'Contributor': contributor,
                'Amount': amount,
                'Type': 'CONTRIBUTION',
                'Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._save_contribution(contribution_data)
            print_success(f"Contribution of ${amount:,.2f} logged for {contributor}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging contribution: {e}")
            print_error(f"Failed to log contribution: {e}")
            return False
    
    def log_withdrawal(self) -> bool:
        """Handle withdrawal logging action.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Log Fund Withdrawal", "_safe_emoji('💸')")
            
            # Get contributor name
            contributor = input("Enter contributor name: ").strip()
            if not contributor:
                print_error("Contributor name cannot be empty")
                return False
            
            # Get withdrawal amount
            try:
                amount_str = input("Enter withdrawal amount: $").strip()
                amount = float(amount_str)
                if amount <= 0:
                    print_error("Withdrawal amount must be positive")
                    return False
            except ValueError:
                print_error("Invalid amount format")
                return False
            
            # Save withdrawal to CSV (as negative contribution)
            withdrawal_data = {
                'Contributor': contributor,
                'Amount': amount,
                'Type': 'WITHDRAWAL',
                'Date': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            self._save_contribution(withdrawal_data)
            print_success(f"Withdrawal of ${amount:,.2f} logged for {contributor}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging withdrawal: {e}")
            print_error(f"Failed to log withdrawal: {e}")
            return False
    
    def update_cash_balances(self) -> bool:
        """Handle cash balance update action.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Update Cash Balances", "_safe_emoji('🔄')")
            
            # Load current cash balances
            cash_file = Path(self.repository.data_dir) / "cash_balances.json"
            current_balances = {}
            
            if cash_file.exists():
                import json
                with open(cash_file, 'r') as f:
                    current_balances = json.load(f)
            
            print("Current cash balances:")
            for currency, balance in current_balances.items():
                print(f"  {currency}: ${balance:,.2f}")
            
            # Get new balance
            currency = input("Enter currency (CAD/USD): ").strip().upper()
            if currency not in ['CAD', 'USD']:
                print_error("Currency must be CAD or USD")
                return False
            
            try:
                balance_str = input(f"Enter new {currency} balance: $").strip()
                balance = float(balance_str)
                if balance < 0:
                    print_error("Cash balance cannot be negative")
                    return False
            except ValueError:
                print_error("Invalid balance format")
                return False
            
            # Update and save balances
            current_balances[currency] = balance
            
            import json
            with open(cash_file, 'w') as f:
                json.dump(current_balances, f, indent=2)
            
            print_success(f"{currency} balance updated to ${balance:,.2f}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating cash balances: {e}")
            print_error(f"Failed to update cash balances: {e}")
            return False
    
    def buy_stock(self) -> bool:
        """Handle stock purchase action.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Buy Stock", "_safe_emoji('🛒')")
            
            # Get order type
            order_type = input("Order type (limit/market): ").strip().lower()
            if order_type not in ['limit', 'market']:
                print_error("Order type must be 'limit' or 'market'")
                return False
            
            # Get ticker
            ticker = input("Enter ticker symbol: ").strip().upper()
            if not ticker:
                print_error("Ticker symbol cannot be empty")
                return False
            
            # Get shares
            try:
                shares_str = input("Enter number of shares: ").strip()
                shares = Decimal(shares_str)
                if shares <= 0:
                    print_error("Number of shares must be positive")
                    return False
            except (ValueError, TypeError):
                print_error("Invalid shares format")
                return False
            
            # Get price
            try:
                if order_type == 'limit':
                    price_str = input("Enter limit price: $").strip()
                else:
                    price_str = input("Enter market price: $").strip()
                price = Decimal(price_str)
                if price <= 0:
                    print_error("Price must be positive")
                    return False
            except (ValueError, TypeError):
                print_error("Invalid price format")
                return False
            
            # Get optional stop loss
            stop_loss = None
            stop_loss_str = input("Enter stop loss price (optional): $").strip()
            if stop_loss_str:
                try:
                    stop_loss = Decimal(stop_loss_str)
                    if stop_loss <= 0:
                        print_error("Stop loss must be positive")
                        return False
                except (ValueError, TypeError):
                    print_error("Invalid stop loss format")
                    return False
            
            # Execute trade
            trade = self.trade_processor.execute_buy_trade(
                ticker=ticker,
                shares=shares,
                price=price,
                stop_loss=stop_loss,
                reason=f"{order_type.title()} order"
            )
            
            if trade:
                print_success(f"Buy order executed: {shares} shares of {ticker} at ${price}")
                return True
            else:
                print_error("Failed to execute buy order")
                return False
            
        except Exception as e:
            logger.error(f"Error executing buy order: {e}")
            print_error(f"Failed to execute buy order: {e}")
            return False
    
    def sell_stock(self) -> bool:
        """Handle stock sale action.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Sell Stock", "_safe_emoji('📤')")
            
            # Get ticker
            ticker = input("Enter ticker symbol: ").strip().upper()
            if not ticker:
                print_error("Ticker symbol cannot be empty")
                return False
            
            # Get shares
            try:
                shares_str = input("Enter number of shares to sell: ").strip()
                shares = Decimal(shares_str)
                if shares <= 0:
                    print_error("Number of shares must be positive")
                    return False
            except (ValueError, TypeError):
                print_error("Invalid shares format")
                return False
            
            # Get price
            try:
                price_str = input("Enter limit price: $").strip()
                price = Decimal(price_str)
                if price <= 0:
                    print_error("Price must be positive")
                    return False
            except (ValueError, TypeError):
                print_error("Invalid price format")
                return False
            
            # Execute trade
            trade = self.trade_processor.execute_sell_trade(
                ticker=ticker,
                shares=shares,
                price=price,
                reason="Limit sell order"
            )
            
            if trade:
                print_success(f"Sell order executed: {shares} shares of {ticker} at ${price}")
                return True
            else:
                print_error("Failed to execute sell order")
                return False
            
        except Exception as e:
            logger.error(f"Error executing sell order: {e}")
            print_error(f"Failed to execute sell order: {e}")
            return False
    
    def sync_fund_contributions(self) -> bool:
        """Handle fund contribution sync action.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print_info("Sync Fund Contributions", "_safe_emoji('🔗')")
            print_warning("Fund contribution sync not yet implemented")
            print_info("This feature will sync contributions from external sources")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing fund contributions: {e}")
            print_error(f"Failed to sync fund contributions: {e}")
            return False
    
    def _save_contribution(self, contribution_data: Dict[str, Any]) -> None:
        """Save contribution data to CSV file.
        
        Args:
            contribution_data: Dictionary containing contribution information
        """
        fund_file = Path(self.repository.data_dir) / "fund_contributions.csv"
        
        # Create DataFrame with new contribution
        new_df = pd.DataFrame([contribution_data])
        
        # Append to existing file or create new one
        if fund_file.exists():
            existing_df = pd.read_csv(fund_file)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Save to CSV
        combined_df.to_csv(fund_file, index=False)
        logger.info(f"Contribution saved to {fund_file}")