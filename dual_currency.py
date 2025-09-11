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
        """Spend CAD cash - only spends available amount, prevents negative balance"""
        if self.cad >= amount:
            self.cad -= amount
            return True  # Full amount spent
        else:
            # Spend only what's available, balance goes to 0
            self.cad = 0.0
            return False  # Partial amount spent (or none if already 0)
    
    def spend_usd(self, amount: float) -> bool:
        """Spend USD cash - only spends available amount, prevents negative balance"""
        if self.usd >= amount:
            self.usd -= amount
            return True  # Full amount spent
        else:
            # Spend only what's available, balance goes to 0
            self.usd = 0.0
            return False  # Partial amount spent (or none if already 0)
    
    def add_cad(self, amount: float) -> None:
        """Add CAD cash (from sales, etc.)"""
        self.cad += amount
    
    def add_usd(self, amount: float) -> None:
        """Add USD cash (from sales, etc.)"""
        self.usd += amount
    
    def convert_cad_to_usd(self, cad_amount: float, exchange_rate: float = None, fee_rate: float = 0.015) -> Tuple[float, float]:
        """
        Convert CAD to USD at market rate plus fee.
        Returns (usd_received, fee_charged)
        """
        if exchange_rate is None:
            exchange_rate = get_exchange_rate('CAD', 'USD')
        
        # Calculate conversion with fee
        usd_before_fee = cad_amount * exchange_rate
        fee_charged = usd_before_fee * fee_rate
        usd_received = usd_before_fee - fee_charged
        
        # Update balances
        self.cad -= cad_amount
        self.usd += usd_received
        
        return usd_received, fee_charged
    
    def convert_usd_to_cad(self, usd_amount: float, exchange_rate: float = None, fee_rate: float = 0.015) -> Tuple[float, float]:
        """
        Convert USD to CAD at market rate plus fee.
        Returns (cad_received, fee_charged)
        """
        if exchange_rate is None:
            exchange_rate = get_exchange_rate('USD', 'CAD')
        
        # Calculate conversion with fee
        cad_before_fee = usd_amount * exchange_rate
        fee_charged = cad_before_fee * fee_rate
        cad_received = cad_before_fee - fee_charged
        
        # Update balances
        self.usd -= usd_amount
        self.cad += cad_received
        
        return cad_received, fee_charged
    
    def can_convert_cad_to_usd(self, cad_amount: float) -> bool:
        """Check if we have enough CAD to convert"""
        return self.cad >= cad_amount
    
    def can_convert_usd_to_cad(self, usd_amount: float) -> bool:
        """Check if we have enough USD to convert"""
        return self.usd >= usd_amount

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

def get_live_exchange_rate(from_currency: str, to_currency: str) -> float:
    """
    Get live exchange rate from a free API.
    Falls back to static rates if API is unavailable.
    """
    try:
        import requests
        
        # Using exchangerate-api.com (free tier)
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            return data['rates'].get(to_currency, get_exchange_rate(from_currency, to_currency))
        else:
            print(f"⚠️  API unavailable, using static rate for {from_currency} to {to_currency}")
            return get_exchange_rate(from_currency, to_currency)
            
    except Exception as e:
        print(f"⚠️  Error fetching live rate: {e}, using static rate")
        return get_exchange_rate(from_currency, to_currency)

def calculate_conversion_with_fee(amount: float, from_currency: str, to_currency: str, fee_rate: float = 0.015) -> Dict[str, float]:
    """
    Calculate conversion details including fee.
    Returns dict with: amount_before_fee, fee_charged, amount_after_fee, exchange_rate
    """
    exchange_rate = get_live_exchange_rate(from_currency, to_currency)
    amount_before_fee = amount * exchange_rate
    fee_charged = amount_before_fee * fee_rate
    amount_after_fee = amount_before_fee - fee_charged
    
    return {
        'amount_before_fee': amount_before_fee,
        'fee_charged': fee_charged,
        'amount_after_fee': amount_after_fee,
        'exchange_rate': exchange_rate,
        'fee_rate': fee_rate
    }
