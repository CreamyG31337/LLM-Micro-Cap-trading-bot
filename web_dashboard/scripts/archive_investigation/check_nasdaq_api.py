import requests
import json
import time

def check_nasdaq_dividend(symbol):
    print(f"\n--- Checking Nasdaq API for {symbol} ---")
    url = f"https://api.nasdaq.com/api/quote/{symbol}/dividends?assetclass=stocks"
    
    # Nasdaq requires User-Agent headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.nasdaq.com',
        'Referer': f'https://www.nasdaq.com/market-activity/stocks/{symbol.lower()}/dividend-history'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Pretty print key parts
        if data and data.get('data') and data['data'].get('dividends'):
            divs = data['data']['dividends']
            if divs and 'rows' in divs:
                print(f"Found {len(divs['rows'])} dividend records.")
                # Show first 2 records
                for i, row in enumerate(divs['rows'][:2]):
                    print(f"Record {i+1}: Ex-Date={row.get('exOrEffDate')}, Pay-Date={row.get('paymentDate')}, Amount={row.get('amount')}")
            else:
                print("No dividend rows found in data.")
        else:
            print("No dividend data structure found.")
            # print(json.dumps(data, indent=2)) # Debug
            
    except Exception as e:
        print(f"Error fetching data: {e}")

if __name__ == "__main__":
    check_nasdaq_dividend("AAPL")
    time.sleep(1)
    check_nasdaq_dividend("MSFT")
    time.sleep(1)
    # Test a Canadian ticker (Not expecting this to work on Nasdaq US site directly, but worth a shot)
    check_nasdaq_dividend("SHOP") 
