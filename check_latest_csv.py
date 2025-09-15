import pandas as pd
from datetime import datetime

# Load CSV and check the very latest entries
df = pd.read_csv('trading_data/prod/llm_portfolio_update.csv')
print('📊 Checking for latest data after trading script run...')

# Convert dates
df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
df['Date_Only'] = df['Date'].dt.date

# Show the very last entries
print('🔍 Last 5 entries in CSV:')
print(df.tail(5)[['Date', 'Ticker', 'Total Value', 'PnL', 'Current Price']].to_string(index=False))

# Check today's timestamp
today = datetime.now().date()
today_data = df[df['Date_Only'] == today]
print(f'\n📅 Entries for today ({today}): {len(today_data)}')

if len(today_data) > 0:
    latest_timestamp = today_data['Date'].max()
    print(f'📅 Latest timestamp today: {latest_timestamp}')
    
    # Calculate today's totals manually
    latest_today = []
    for ticker, group in today_data.groupby('Ticker'):
        latest_entry = group.loc[group['Date'].idxmax()]
        if latest_entry['Total Value'] > 0:
            latest_today.append(latest_entry)
    
    total_value = sum(pos['Total Value'] for pos in latest_today)
    total_cost = sum(pos['Cost Basis'] for pos in latest_today)
    total_pnl = sum(pos['PnL'] for pos in latest_today)
    
    print(f'📊 Today totals:')
    print(f'   Market Value: ${total_value:,.2f}')
    print(f'   Cost Basis: ${total_cost:,.2f}')  
    print(f'   P&L: ${total_pnl:,.2f}')
    print(f'   Performance: {(total_pnl/total_cost)*100:+.2f}%')
    
    # Compare with yesterday
    yesterday_data = df[df['Date_Only'] < today]
    if len(yesterday_data) > 0:
        prev_date = yesterday_data['Date_Only'].max()
        prev_day_data = yesterday_data[yesterday_data['Date_Only'] == prev_date]
        
        prev_positions = []
        for ticker, group in prev_day_data.groupby('Ticker'):
            latest_entry = group.loc[group['Date'].idxmax()]
            if latest_entry['Total Value'] > 0:
                prev_positions.append(latest_entry)
        
        prev_value = sum(pos['Total Value'] for pos in prev_positions)
        change = total_value - prev_value
        
        print(f'\n📈 Change from {prev_date}:')
        print(f'   Previous: ${prev_value:,.2f}')
        print(f'   Current: ${total_value:,.2f}')
        print(f'   Change: ${change:,.2f}')
else:
    print('❌ No data found for today!')

print(f'\n🔍 Total rows in CSV: {len(df)}')
print(f'🔍 Date range: {df["Date_Only"].min()} to {df["Date_Only"].max()}')