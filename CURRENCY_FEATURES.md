# Currency Conversion and Negative Balance Features

This document describes the new currency conversion and negative balance features added to the LLM Micro-Cap Trading Bot.

## Features Added

### 1. Currency Conversion
- **Automatic CAD to USD conversion** when CAD balance is insufficient for USD trades
- **Market rate + 1.5% fee** for all conversions
- **Live exchange rate fetching** (with fallback to static rates)
- **Real-time conversion calculations** showing fees and amounts

### 2. Negative Balance Support
- **Option to allow negative balances** for trades that exceed available cash
- **Manual balance correction** using the `update_cash.py` script
- **Flexible balance management** for temporary shortfalls

## How It Works

### When Insufficient Funds Are Detected

When a trade requires more cash than available, the system now offers **4 options**:

1. **Add more cash** - Traditional option to add funds to the account
2. **Convert from other currency** - Convert CAD to USD (or vice versa) at market rate + 1.5% fee
3. **Allow negative balance** - Proceed with the trade, resulting in negative balance
4. **Cancel purchase** - Cancel the trade entirely

### Currency Conversion Details

- **Exchange Rate Source**: Live rates from exchangerate-api.com (free tier)
- **Fallback**: Static rates if API is unavailable
- **Fee Structure**: 1.5% fee on converted amount
- **Example**: Converting $100 CAD to USD at 0.74 rate:
  - Amount before fee: $74.00 USD
  - Fee (1.5%): $1.11 USD
  - Amount received: $72.89 USD

### Negative Balance Mode

- **Toggle**: Use `update_cash.py` script with option 'n'
- **Temporary**: Can be enabled/disabled as needed
- **Manual Correction**: Use `update_cash.py` to correct negative balances later
- **Flexibility**: Allows trades to proceed when you know you'll add funds later

## Usage Examples

### Scenario 1: CAD Insufficient for USD Trade
```
Need: $500.00 USD
Have: CAD $1,000.00, USD $200.00
Short: $300.00 USD

Options:
1. Add more USD cash
2. Convert CAD to USD (would get ~$740.00 USD)
3. Allow negative balance and proceed
4. Cancel this purchase
```

### Scenario 2: Both Currencies Insufficient
```
Need: $1,000.00 CAD
Have: CAD $100.00, USD $50.00
Short: $900.00 CAD

Options:
1. Add more CAD cash
2. Convert USD to CAD (would get ~$67.50 CAD)
3. Allow negative balance and proceed
4. Cancel this purchase
```

## Technical Implementation

### Files Modified
- `dual_currency.py` - Added conversion methods and negative balance support
- `trading_script.py` - Enhanced insufficient funds handling
- `update_cash.py` - Added negative balance toggle option

### New Functions
- `convert_cad_to_usd()` - Convert CAD to USD with fee
- `convert_usd_to_cad()` - Convert USD to CAD with fee
- `calculate_conversion_with_fee()` - Calculate conversion details
- `get_live_exchange_rate()` - Fetch live exchange rates

### Data Storage
- `allow_negative` flag stored in `cash_balances.json`
- Backward compatible with existing balance files

## Benefits

1. **Flexibility**: No more blocked trades due to currency mismatches
2. **Cost Control**: 1.5% fee is reasonable compared to broker conversion fees
3. **Real-time Rates**: Uses live exchange rates when available
4. **Manual Override**: Option to proceed with negative balances when needed
5. **Easy Correction**: Simple tools to fix negative balances later

## Best Practices

1. **Monitor Balances**: Check balances regularly to avoid excessive negative amounts
2. **Use Conversion Wisely**: Consider the 1.5% fee when deciding between conversion and adding cash
3. **Correct Negatives**: Use `update_cash.py` to correct negative balances promptly
4. **Plan Ahead**: Add sufficient funds to avoid frequent conversions or negative balances

## Testing

The features have been tested with various scenarios:
- ✅ Currency conversion calculations
- ✅ Negative balance functionality
- ✅ Insufficient funds handling
- ✅ Exchange rate fetching (with fallback)
- ✅ Balance persistence and loading

All tests pass successfully, confirming the features work as expected.
