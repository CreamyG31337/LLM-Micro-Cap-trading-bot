"""
Dual Currency Cash Management

Handles CAD and USD cash balances for North American trading.
"""

import json
from pathlib import Path
from typing import Dict, Tuple
from dataclasses import dataclass

@dataclass
class CashBalances:
    """Container for dual currency cash balances"""
    cad: float = 0.0
    usd: float = 0.0
    
    def total_cad_equivalent(self, usd_to_cad_rate: float = 1.35) -> float:
        """Calculate total cash in CAD equivalent"""
        return self.cad + (self.usd * usd_to_cad_rate)
    
    def total_usd_equivalent(self, cad_to_usd_rate: float = 0.74) -> float:
        """Calculate total cash in USD equivalent"""
        return self.usd + (self.cad * cad_to_usd_rate)
    
    def can_afford_cad(self, amount: float) -> bool:
        """Check if we have enough CAD cash"""
        return self.cad >= amount
    
    def can_afford_usd(self, amount: float) -> bool:
        """Check if we have enough USD cash"""
        return self.usd >= amount
    
    def spend_cad(self, amount: float) -> bool:
        """Spend CAD cash if available"""
        if self.can_afford_cad(amount):
            self.cad -= amount
            return True
        return False
    
    def spend_usd(self, amount: float) -> bool:
        """Spend USD cash if available"""
        if self.can_afford_usd(amount):
            self.usd -= amount
            return True
        return False
    
    def add_cad(self, amount: float) -> None:
        """Add CAD cash (from sales, etc.)"""
        self.cad += amount
    
    def add_usd(self, amount: float) -> None:
        """Add USD cash (from sales, etc.)"""
        self.usd += amount

def is_canadian_ticker(ticker: str) -> bool:
    """Determine if ticker is Canadian based on suffix"""
    ticker = ticker.upper()
    return ticker.endswith('.TO') or ticker.endswith('.V') or ticker.endswith('.CN')

def is_us_ticker(ticker: str) -> bool:
    """Determine if ticker is US based on format"""
    ticker = ticker.upper()
    # US tickers typically have no suffix, or specific US suffixes
    return not is_canadian_ticker(ticker) and not ticker.startswith('^')

def get_ticker_currency(ticker: str) -> str:
    """Get the currency for a ticker"""
    if is_canadian_ticker(ticker):
        return 'CAD'
    elif is_us_ticker(ticker):
        return 'USD'
    else:
        return 'USD'  # Default to USD for unknown formats

def prompt_for_dual_currency_cash() -> CashBalances:
    """Prompt user for starting CAD and USD cash amounts"""
    print("\n=== Dual Currency Cash Setup ===")
    print("You're using North American trading (both CAD and USD positions).")
    print("Please enter your starting cash amounts for both currencies:")
    
    while True:
        try:
            cad_cash = float(input("Starting CAD cash amount: $"))
            if cad_cash < 0:
                print("Please enter a positive amount.")
                continue
            break
        except ValueError:
            print("Please enter a valid number for CAD amount.")
    
    while True:
        try:
            usd_cash = float(input("Starting USD cash amount: $"))
            if usd_cash < 0:
                print("Please enter a positive amount.")
                continue
            break
        except ValueError:
            print("Please enter a valid number for USD amount.")
    
    balances = CashBalances(cad=cad_cash, usd=usd_cash)
    
    print(f"\n✅ Cash balances set:")
    print(f"   CAD: ${balances.cad:,.2f}")
    print(f"   USD: ${balances.usd:,.2f}")
    print(f"   Total (CAD equiv): ${balances.total_cad_equivalent():,.2f}")
    
    return balances

def save_cash_balances(balances: CashBalances, data_dir: Path) -> None:
    """Save cash balances to JSON file"""
    cash_file = data_dir / "cash_balances.json"
    data = {
        "cad": balances.cad,
        "usd": balances.usd
    }
    with open(cash_file, 'w') as f:
        json.dump(data, f, indent=2)

def load_cash_balances(data_dir: Path) -> CashBalances:
    """Load cash balances from JSON file"""
    cash_file = data_dir / "cash_balances.json"
    
    if not cash_file.exists():
        return CashBalances()
    
    try:
        with open(cash_file, 'r') as f:
            data = json.load(f)
        return CashBalances(
            cad=data.get('cad', 0.0),
            usd=data.get('usd', 0.0)
        )
    except Exception:
        return CashBalances()

def format_cash_display(balances: CashBalances) -> str:
    """Format cash balances for display"""
    return f"CAD ${balances.cad:,.2f} | USD ${balances.usd:,.2f}"

def get_trade_currency_info(ticker: str, shares: float, price: float) -> Dict[str, any]:
    """Get currency info for a trade"""
    currency = get_ticker_currency(ticker)
    cost = shares * price
    
    return {
        'ticker': ticker,
        'currency': currency,
        'shares': shares,
        'price': price,
        'cost': cost,
        'is_canadian': currency == 'CAD',
        'is_us': currency == 'USD'
    }

# Conversion rates (you might want to fetch these from an API)
def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    """Get exchange rate (simplified - in production you'd fetch real rates)"""
    rates = {
        ('USD', 'CAD'): 1.35,
        ('CAD', 'USD'): 0.74,
        ('USD', 'USD'): 1.0,
        ('CAD', 'CAD'): 1.0
    }
    return rates.get((from_currency, to_currency), 1.0)
