"""
Simple Cash Balance Manager

A lightweight cash balance manager that fixes the CAD/cad duplicate issue
and adds basic transaction logging without the complexity of bulk operations.

This is designed for personal use with a few friends - simple and effective.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

from .calculations import money_to_decimal

logger = logging.getLogger(__name__)


class SimpleCashManager:
    """
    Simple cash balance manager with duplicate handling and basic transaction logging.
    
    This handles the CAD/cad duplicate issue and provides basic transaction history
    without the complexity of bulk operations or enterprise features.
    """
    
    def __init__(self, data_dir: Path):
        """Initialize the simple cash manager.
        
        Args:
            data_dir: Path to the data directory containing cash balance files
        """
        self.data_dir = Path(data_dir)
        self.cash_file = self.data_dir / "cash_balances.json"
        self.transactions_file = self.data_dir / "cash_transactions.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load current balances and transactions
        self._balances = self._load_balances()
        self._transactions = self._load_transactions()
    
    def _load_balances(self) -> Dict[str, Decimal]:
        """Load current cash balances, handling CAD/cad duplicates."""
        if not self.cash_file.exists():
            logger.info("No existing cash balances file found, initializing with zero balances")
            return {'CAD': Decimal('0.00'), 'USD': Decimal('0.00')}
        
        try:
            with open(self.cash_file, 'r') as f:
                data = json.load(f)
            
            # Handle legacy format with inconsistent case - THIS FIXES THE DUPLICATE ISSUE
            cad_amount = Decimal('0.00')
            usd_amount = Decimal('0.00')
            
            for key, value in data.items():
                if key.upper() == 'CAD':
                    cad_amount += money_to_decimal(value)  # Adds both "cad" and "CAD"
                elif key.upper() == 'USD':
                    usd_amount += money_to_decimal(value)  # Adds both "usd" and "USD"
            
            return {'CAD': cad_amount, 'USD': usd_amount}
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error loading cash balances: {e}")
            return {'CAD': Decimal('0.00'), 'USD': Decimal('0.00')}
    
    def _load_transactions(self) -> List[Dict]:
        """Load transaction history from file."""
        if not self.transactions_file.exists():
            return []
        
        try:
            with open(self.transactions_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Error loading transactions: {e}")
            return []
    
    def _save_balances(self) -> None:
        """Save current balances to file."""
        try:
            data = {
                'CAD': float(self._balances['CAD']),
                'USD': float(self._balances['USD']),
                'last_updated': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.cash_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving cash balances: {e}")
            raise
    
    def _save_transactions(self) -> None:
        """Save transaction history to file."""
        try:
            with open(self.transactions_file, 'w') as f:
                json.dump(self._transactions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving transactions: {e}")
            raise
    
    def _add_transaction(self, currency: str, amount: Decimal, description: str) -> None:
        """Add a transaction to the history."""
        transaction = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'currency': currency.upper(),
            'amount': float(amount),
            'balance_after': float(self._balances[currency.upper()]),
            'description': description
        }
        
        self._transactions.append(transaction)
        self._save_transactions()
    
    def get_balances(self) -> Dict[str, Decimal]:
        """Get current cash balances."""
        return self._balances.copy()
    
    def get_balance(self, currency: str) -> Decimal:
        """Get balance for a specific currency."""
        return self._balances[currency.upper()]
    
    def get_transactions(self, limit: int = 10) -> List[Dict]:
        """Get recent transaction history."""
        return self._transactions[-limit:] if self._transactions else []
    
    def add_cash(self, currency: str, amount: Decimal, description: str = "Manual deposit") -> bool:
        """Add cash to the specified currency.
        
        Args:
            currency: Currency code (CAD or USD)
            amount: Amount to add (positive)
            description: Description of the transaction
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            currency = currency.upper()
            if currency not in ['CAD', 'USD']:
                raise ValueError(f"Invalid currency: {currency}")
            
            amount = money_to_decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            # Update balance
            self._balances[currency] += amount
            
            # Record transaction
            self._add_transaction(currency, amount, description)
            
            # Save balances
            self._save_balances()
            
            logger.info(f"Added {amount} {currency}: {description}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding cash: {e}")
            return False
    
    def remove_cash(self, currency: str, amount: Decimal, description: str = "Manual withdrawal", allow_negative: bool = False) -> bool:
        """Remove cash from the specified currency.
        
        Args:
            currency: Currency code (CAD or USD)
            amount: Amount to remove (positive)
            description: Description of the transaction
            allow_negative: Whether to allow negative balances
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            currency = currency.upper()
            if currency not in ['CAD', 'USD']:
                raise ValueError(f"Invalid currency: {currency}")
            
            amount = money_to_decimal(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
            
            # Check if we have sufficient funds
            if not allow_negative and self._balances[currency] < amount:
                raise ValueError(f"Insufficient {currency} balance: {self._balances[currency]} < {amount}")
            
            # Update balance
            self._balances[currency] -= amount
            
            # Record transaction (negative amount for withdrawal)
            self._add_transaction(currency, -amount, description)
            
            # Save balances
            self._save_balances()
            
            logger.info(f"Removed {amount} {currency}: {description}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing cash: {e}")
            return False
    
    def set_balance(self, currency: str, amount: Decimal, description: str = "Manual balance adjustment") -> bool:
        """Set exact balance for a currency.
        
        Args:
            currency: Currency code (CAD or USD)
            amount: New balance amount
            description: Description of the adjustment
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            currency = currency.upper()
            if currency not in ['CAD', 'USD']:
                raise ValueError(f"Invalid currency: {currency}")
            
            amount = money_to_decimal(amount)
            if amount < 0:
                raise ValueError("Balance cannot be negative")
            
            # Get current balance
            current_balance = self._balances[currency]
            difference = amount - current_balance
            
            if difference == 0:
                logger.info(f"No change needed for {currency} balance")
                return True
            
            # Update balance
            self._balances[currency] = amount
            
            # Record transaction
            self._add_transaction(currency, difference, description)
            
            # Save balances
            self._save_balances()
            
            logger.info(f"Set {currency} balance to {amount}: {description}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting balance: {e}")
            return False
    
    def get_summary(self) -> Dict:
        """Get a simple summary of balances and recent transactions."""
        return {
            'balances': {
                'CAD': float(self._balances['CAD']),
                'USD': float(self._balances['USD'])
            },
            'recent_transactions': self.get_transactions(5),
            'total_transactions': len(self._transactions)
        }
