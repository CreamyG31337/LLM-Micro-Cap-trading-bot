"""
Analyze the actual magnitude of float conversion errors in P&L calculations.
"""

import sys
from pathlib import Path
sys.path.append('.')

import tempfile
import shutil
from datetime import datetime, timezone
from decimal import Decimal
from dotenv import load_dotenv

from data.repositories.csv_repository import CSVRepository
from data.repositories.supabase_repository import SupabaseRepository
from data.models.portfolio import Position, PortfolioSnapshot

# Load Supabase credentials
load_dotenv("web_dashboard/.env")

def analyze_precision_errors():
    """Analyze the actual magnitude of precision errors."""
    print("=== PRECISION ERROR ANALYSIS ===")
    
    # Create temporary directory for CSV tests
    test_data_dir = Path(tempfile.mkdtemp(prefix="precision_analysis_"))
    test_fund = "PRECISION_TEST"
    
    try:
        # Create repositories
        csv_repo = CSVRepository(str(test_data_dir))
        supabase_repo = SupabaseRepository(fund=test_fund)
        
        # Test cases with different precision scenarios
        test_cases = [
            {
                "name": "Simple Round Numbers",
                "shares": Decimal("100"),
                "avg_price": Decimal("50.00"),
                "current_price": Decimal("55.00"),
                "expected_pnl": Decimal("500.00")
            },
            {
                "name": "Precise Decimals",
                "shares": Decimal("150.5"),
                "avg_price": Decimal("33.333"),
                "current_price": Decimal("35.789"),
                "expected_pnl": Decimal("369.70")
            },
            {
                "name": "High Precision",
                "shares": Decimal("123.456789"),
                "avg_price": Decimal("12.3456789"),
                "current_price": Decimal("13.4567890"),
                "expected_pnl": Decimal("137.174074")
            },
            {
                "name": "Very Small Amounts",
                "shares": Decimal("0.001"),
                "avg_price": Decimal("0.01"),
                "current_price": Decimal("0.02"),
                "expected_pnl": Decimal("0.00001")
            },
            {
                "name": "Large Numbers",
                "shares": Decimal("1000000"),
                "avg_price": Decimal("100.00"),
                "current_price": Decimal("100.01"),
                "expected_pnl": Decimal("10000.00")
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            print(f"\n--- Test Case {i+1}: {test_case['name']} ---")
            
            # Calculate expected values
            cost_basis = test_case['shares'] * test_case['avg_price']
            market_value = test_case['shares'] * test_case['current_price']
            expected_pnl = market_value - cost_basis
            
            print(f"Shares: {test_case['shares']}")
            print(f"Avg Price: {test_case['avg_price']}")
            print(f"Current Price: {test_case['current_price']}")
            print(f"Expected P&L: {expected_pnl}")
            
            # Create position
            position = Position(
                ticker=f"PREC{i}",
                shares=test_case['shares'],
                avg_price=test_case['avg_price'],
                cost_basis=cost_basis,
                currency="CAD",
                company=f"Precision Test {i+1}",
                current_price=test_case['current_price'],
                market_value=market_value,
                unrealized_pnl=expected_pnl
            )
            
            # Create snapshot
            snapshot = PortfolioSnapshot(
                positions=[position],
                timestamp=datetime.now(timezone.utc),
                total_value=market_value
            )
            
            # Save to both repositories
            csv_repo.save_portfolio_snapshot(snapshot)
            supabase_repo.save_portfolio_snapshot(snapshot)
            
            # Retrieve and compare
            csv_snapshots = csv_repo.get_portfolio_data()
            supabase_snapshots = supabase_repo.get_portfolio_data()
            
            csv_snapshot = csv_snapshots[-1]
            supabase_snapshot = supabase_snapshots[-1]
            
            csv_position = csv_snapshot.positions[0]
            supabase_position = supabase_snapshot.positions[0]
            
            # Calculate differences
            pnl_diff = csv_position.unrealized_pnl - supabase_position.unrealized_pnl if csv_position.unrealized_pnl and supabase_position.unrealized_pnl else None
            market_value_diff = csv_position.market_value - supabase_position.market_value if csv_position.market_value and supabase_position.market_value else None
            cost_basis_diff = csv_position.cost_basis - supabase_position.cost_basis if csv_position.cost_basis and supabase_position.cost_basis else None
            
            # Calculate percentage differences
            pnl_pct_diff = None
            if pnl_diff is not None and csv_position.unrealized_pnl and csv_position.unrealized_pnl != 0:
                pnl_pct_diff = (pnl_diff / csv_position.unrealized_pnl) * 100
            
            market_value_pct_diff = None
            if market_value_diff is not None and csv_position.market_value and csv_position.market_value != 0:
                market_value_pct_diff = (market_value_diff / csv_position.market_value) * 100
            
            cost_basis_pct_diff = None
            if cost_basis_diff is not None and csv_position.cost_basis and csv_position.cost_basis != 0:
                cost_basis_pct_diff = (cost_basis_diff / csv_position.cost_basis) * 100
            
            print(f"CSV P&L: {csv_position.unrealized_pnl}")
            print(f"Supabase P&L: {supabase_position.unrealized_pnl}")
            print(f"P&L Difference: {pnl_diff}")
            print(f"P&L % Difference: {pnl_pct_diff}%" if pnl_pct_diff is not None else "P&L % Difference: N/A")
            
            print(f"CSV Market Value: {csv_position.market_value}")
            print(f"Supabase Market Value: {supabase_position.market_value}")
            print(f"Market Value Difference: {market_value_diff}")
            print(f"Market Value % Difference: {market_value_pct_diff}%" if market_value_pct_diff is not None else "Market Value % Difference: N/A")
            
            print(f"CSV Cost Basis: {csv_position.cost_basis}")
            print(f"Supabase Cost Basis: {supabase_position.cost_basis}")
            print(f"Cost Basis Difference: {cost_basis_diff}")
            print(f"Cost Basis % Difference: {cost_basis_pct_diff}%" if cost_basis_pct_diff is not None else "Cost Basis % Difference: N/A")
            
            # Determine if differences are significant
            significant_differences = []
            if pnl_diff and abs(pnl_diff) > Decimal('0.01'):  # More than 1 cent
                significant_differences.append(f"P&L: {pnl_diff}")
            if market_value_diff and abs(market_value_diff) > Decimal('0.01'):
                significant_differences.append(f"Market Value: {market_value_diff}")
            if cost_basis_diff and abs(cost_basis_diff) > Decimal('0.01'):
                significant_differences.append(f"Cost Basis: {cost_basis_diff}")
            
            if significant_differences:
                print(f"⚠️  SIGNIFICANT DIFFERENCES: {', '.join(significant_differences)}")
            else:
                print("✅ No significant differences (all < 1 cent)")
    
    finally:
        # Cleanup
        if test_data_dir.exists():
            try:
                shutil.rmtree(test_data_dir)
            except PermissionError:
                pass

if __name__ == "__main__":
    analyze_precision_errors()
