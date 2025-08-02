"""Wrapper for the shared trading script using local data directory."""

from pathlib import Path
import sys

# Allow importing the shared module from the repository root
sys.path.append(str(Path(__file__).resolve().parents[1]))

from trading_script import main


if __name__ == "__main__":
    cash = 100
    chatgpt_portfolio = [
        {"ticker": "ABEO", "shares": 6, "stop_loss": 4.9, "buy_price": 5.77, "cost_basis": 34.62},
        {"ticker": "IINN", "shares": 14, "stop_loss": 1.1, "buy_price": 1.5, "cost_basis": 21.0},
        {"ticker": "ACTU", "shares": 6, "stop_loss": 4.89, "buy_price": 5.75, "cost_basis": 34.5},
    ]

    data_dir = Path(__file__).resolve().parent
    main(chatgpt_portfolio, cash, data_dir)

