
import requests
import pandas as pd
from io import StringIO

url = "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/csv,application/csv;q=0.9,*/*;q=0.8',
}

print(f"Downloading IVV from {url}...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    content = response.text
    print("\n--- First 30 lines of content ---")
    lines = content.split('\n')
    for i, line in enumerate(lines[:30]):
        print(f"{i}: {line}")
    print("---------------------------------")
    
    print("\nAttempting parse...")
    # Try to find header
    header_row = 0
    for i, line in enumerate(lines[:30]):
        if 'Ticker' in line and 'Name' in line:
            header_row = i
            print(f"Found header at line {i}")
            break
            
    df = pd.read_csv(StringIO(content), skiprows=header_row)
    print(f"\nColumns: {df.columns.tolist()}")
    print(f"Row count: {len(df)}")
    
except Exception as e:
    print(f"Error: {e}")
