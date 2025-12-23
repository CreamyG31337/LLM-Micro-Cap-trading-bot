"""
Simplified script to manually fetch and insert today's portfolio prices.
This bypasses the scheduler completely and does the core logic directly.
"""
import os
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

# Add project paths
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

def load_todays_prices():
    from web_dashboard.supabase_client import SupabaseClient
    
    client = SupabaseClient(use_service_role=True)
    today = date.today()
    
    print(f"Loading portfolio prices for {today}")
    print("=" * 60)
    
    # Get Fund info
    funds_result = client.supabase.table("funds") \
        .select("name, base_currency") \
        .eq("is_production", True) \
        .execute()
    
    if not funds_result.data:
        print("No production funds found!")
        return
    
    fund = funds_result.data[0]
    fund_name = fund['name']
    base_currency = fund.get('base_currency', 'CAD')
    
    print(f"Processing fund: {fund_name} (base: {base_currency})")
    
    # Get latest positions from DB
    positions_result = client.supabase.table("portfolio_positions") \
        .select("ticker, shares, cost_basis, currency, fund") \
        .eq("fund", fund_name) \
        .order("date", desc=True) \
        .limit(100) \
        .execute()
    
    if not positions_result.data:
        print("No positions found!")
        return
    
    # Get unique tickers from latest snapshot
    import pandas as pd
    positions_df = pd.DataFrame(positions_result.data)
    latest_date = positions_df['date'].max() if 'date' in positions_df.columns else None
    
    # Group by ticker to get current holdings
    holdings = {}
    for ticker in positions_df['ticker'].unique():
        ticker_data = positions_df[positions_df['ticker'] == ticker].iloc[0]
        holdings[ticker] = {
            'shares': Decimal(str(ticker_data['shares'])),
            'cost': Decimal(str(ticker_data['cost_basis'])),
            'currency': ticker_data['currency']
        }
    
    print(f"Found {len(holdings)} active positions")
    print(f"Tickers: {list(holdings.keys())}")
    
    # Fetch TODAY's prices
    from market_data.data_fetcher import MarketDataFetcher
    from market_data.price_cache import PriceCache
    
    fetcher = MarketDataFetcher()
    cache = PriceCache()
    
    current_prices = {}
    failed_tickers = []
    
    print("\nFetching prices...")
    for ticker in holdings.keys():
        try:
            # Fetch for today
            result = fetcher.fetch_price_data(ticker, start=datetime.combine(today, datetime.min.time()), 
                                             end=datetime.combine(today, datetime.max.time()))
            
            if result and result.df is not None and not result.df.empty:
                latest_price = Decimal(str(result.df['Close'].iloc[-1]))
                current_prices[ticker] = latest_price
                print(f"  ✅ {ticker}: ${latest_price:.2f}")
            else:
                # Try cache
                cached = cache.get_cached_price(ticker)
                if cached is not None and not cached.empty:
                    latest_price = Decimal(str(cached['Close'].iloc[-1]))
                    current_prices[ticker] = latest_price
                    print(f"  ⚠️  {ticker}: ${latest_price:.2f} (from cache)")
                else:
                    failed_tickers.append(ticker)
                    print(f"  ❌ {ticker}: Failed to fetch")
        except Exception as e:
            failed_tickers.append(ticker)
            print(f"  ❌ {ticker}: Error - {e}")
    
    if not current_prices:
        print("\n❌ All price fetches failed - ABORTING")
        return
    
    print(f"\nSuccessfully fetched {len(current_prices)}/{len(holdings)} prices")
    
    # Get exchange rate
    from web_dashboard.scheduler.exchange_rates_utils import get_exchange_rate_for_date_from_db
    
    exchange_rate = Decimal('1.0')
    if base_currency != 'USD':
        rate = get_exchange_rate_for_date_from_db(
            datetime.combine(today, datetime.min.time()),
            'USD',
            base_currency
        )
        if rate:
            exchange_rate = Decimal(str(rate))
            print(f"\nExchange rate USD→{base_currency}: {exchange_rate}")
    
    # Create position records
    positions_to_insert = []
    total_value = Decimal('0')
    
    print("\nCreating position records...")
    for ticker, price in current_prices.items():
        holding = holdings[ticker]
        shares = holding['shares']
        cost_basis = holding['cost']
        curr = holding['currency']
        
        market_value = shares * price
        pnl = market_value - cost_basis
        
        # Convert to base currency if needed
        if curr == 'USD' and base_currency != 'USD':
            market_value_base = market_value * exchange_rate
            cost_basis_base = cost_basis * exchange_rate
            pnl_base = pnl * exchange_rate
            conv_rate = exchange_rate
        elif curr == base_currency:
            market_value_base = market_value
            cost_basis_base = cost_basis
            pnl_base = pnl
            conv_rate = Decimal('1.0')
        else:
            market_value_base = market_value
            cost_basis_base = cost_basis
            pnl_base = pnl
            conv_rate = Decimal('1.0')
        
        total_value += market_value_base
        
        positions_to_insert.append({
            'fund': fund_name,
            'ticker': ticker,
            'shares': float(shares),
            'price': float(price),
            'cost_basis': float(cost_basis),
            'pnl': float(pnl),
            'currency': curr,
            'date': datetime.combine(today, datetime.min.time().replace(hour=16, minute=0)).isoformat(),
            'base_currency': base_currency,
            'total_value_base': float(market_value_base),
            'cost_basis_base': float(cost_basis_base),
            'pnl_base': float(pnl_base),
            'exchange_rate': float(conv_rate)
        })
    
    print(f"Total portfolio value: ${total_value:,.2f} {base_currency}")
    
    # DELETE existing data for today (if any)
    print(f"\nDeleting existing {today} data...")
    start_of_day = datetime.combine(today, datetime.min.time()).isoformat()
    end_of_day = datetime.combine(today, datetime.max.time()).isoformat()
    
    delete_result = client.supabase.table("portfolio_positions") \
        .delete() \
        .eq("fund", fund_name) \
        .gte("date", start_of_day) \
        .lte("date", end_of_day) \
        .execute()
    
    print(f"Deleted {len(delete_result.data) if delete_result.data else 0} existing records")
    
    # INSERT new data
    print(f"\nInserting {len(positions_to_insert)} new positions...")
    insert_result = client.supabase.table("portfolio_positions") \
        .insert(positions_to_insert) \
        .execute()
    
    inserted_count = len(insert_result.data) if insert_result.data else 0
    print(f"✅ Inserted {inserted_count} positions for {today}")
    
    print("\n" + "=" * 60)
    print("DONE - Now refresh your dashboard and check if graph is corrupted!")

if __name__ == "__main__":
    load_todays_prices()
