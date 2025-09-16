import pandas as pd
from datetime import datetime

# Load and examine the latest portfolio data
df = pd.read_csv('trading_data/prod/llm_portfolio_update.csv')
print('🔍 Debugging Latest Portfolio Data')
print('=' * 50)

df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df['Date_Only'] = df['Date'].dt.date
df['Total Value'] = pd.to_numeric(df['Total Value'], errors='coerce')

print(f"📊 Total rows in CSV: {len(df)}")
print(f"📅 Date range: {df['Date_Only'].min()} to {df['Date_Only'].max()}")

# Show the last 20 rows to see what's happening recently
print(f"\n🔍 Last 20 rows of data:")
recent_data = df.tail(20)[['Date', 'Ticker', 'Total Value', 'Action']].copy()
recent_data['Date_Only'] = recent_data['Date'].dt.date
print(recent_data.to_string(index=False))

# Check what dates we have and their totals
print(f"\n📈 Daily portfolio totals (last 5 days):")
for date_only, date_group in df.groupby('Date_Only'):
    if pd.isna(date_only):
        continue
    
    # Get final positions for this date
    final_positions = []
    for ticker, ticker_group in date_group.groupby('Ticker'):
        latest_entry = ticker_group.loc[ticker_group['Date'].idxmax()]
        if latest_entry['Total Value'] > 0:
            final_positions.append(latest_entry)
    
    if final_positions:
        total_market_value = sum(pos['Total Value'] for pos in final_positions)
        total_cost_basis = sum(pos['Cost Basis'] for pos in final_positions)
        performance_pct = ((total_market_value - total_cost_basis) / total_cost_basis) * 100 if total_cost_basis > 0 else 0
        
        print(f"  {date_only}: ${total_market_value:,.2f} ({performance_pct:+.2f}%) - {len(final_positions)} positions")

# Check if today's data exists
today = datetime.now().date()
today_data = df[df['Date_Only'] == today]
print(f"\n🗓️  Data for today ({today}): {len(today_data)} rows")
if len(today_data) > 0:
    print("Today's data:")
    print(today_data[['Date', 'Ticker', 'Total Value', 'Action']].to_string(index=False))
else:
    print("❌ No data found for today - this might be why the graph looks flat!")
    
# Check the most recent date in the data
most_recent_date = df['Date_Only'].max()
print(f"\n📅 Most recent data date: {most_recent_date}")
if most_recent_date < today:
    print(f"⚠️  Most recent data is from {most_recent_date}, but today is {today}")
    print("   The graph won't show today's changes until the portfolio is updated!")