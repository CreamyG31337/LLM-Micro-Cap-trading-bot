import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import trading_script as ts  # noqa: E402


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    csv_path = root / "test_data" / "llm_portfolio_update.csv"
    print(f"Using CSV: {csv_path}")

    df = pd.read_csv(csv_path)
    df2 = ts.normalize_portfolio_columns(df)
    print("COLUMNS:", ",".join(map(str, df2.columns)))
    print("ROWS:", len(df2))

    p, c = ts.load_latest_portfolio_state(str(csv_path))
    print("portfolio_cols=", list(p.columns))
    print("cash=", c)


if __name__ == "__main__":
    main()


