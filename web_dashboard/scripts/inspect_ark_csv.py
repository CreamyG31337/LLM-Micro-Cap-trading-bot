
import requests
import pandas as pd
from io import StringIO

# Download ARKK CSV to see actual columns
url = "https://assets.ark-funds.com/fund-documents/funds-etf-csv/ARK_INNOVATION_ETF_ARKK_HOLDINGS.csv"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

response = requests.get(url, headers=headers, timeout=30)
print("Status:", response.status_code)
print("\nFirst 500 characters of response:")
print(response.text[:500])
print("\n" + "="*60)

# Try to parse it
df = pd.read_csv(StringIO(response.text))
print("\nColumn names:")
for i, col in enumerate(df.columns):
    print(f"  {i}: '{col}'")

print("\nFirst few rows:")
print(df.head())

print("\nData types:")
print(df.dtypes)
