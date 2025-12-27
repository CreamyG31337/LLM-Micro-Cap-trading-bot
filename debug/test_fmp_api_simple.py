#!/usr/bin/env python3
"""
Simple FMP API Test
==================

Quick test to find the correct endpoint format.
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Load env
project_root = Path(__file__).parent.parent
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

fmp_api_key = os.getenv("FMP_API_KEY")
if not fmp_api_key:
    print("❌ FMP_API_KEY not found")
    sys.exit(1)

print("Testing FMP API endpoints...")
print(f"API Key: {fmp_api_key[:10]}...{fmp_api_key[-4:]}")
print()

# Use stable API endpoints (not v3/v4 which are legacy)
base_url = "https://financialmodelingprep.com/stable"

endpoints_to_try = [
    "/senate-latest",
    "/house-latest",
]

for endpoint_path in endpoints_to_try:
    endpoint = f"{base_url}{endpoint_path}"
    print(f"Testing: {endpoint}")
    
    # Use page and limit parameters
    params = {
        'page': 0,
        'limit': 10,  # Just test with 10 records
        'apikey': fmp_api_key
    }
    
    try:
        response = requests.get(endpoint, params=params, timeout=10)
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"  ✅ SUCCESS!")
            data = response.json()
            if isinstance(data, list):
                print(f"  Response: List with {len(data)} items")
                if data:
                    sample = data[0]
                    print(f"  All keys in sample: {list(sample.keys())}")
                    print(f"\n  Sample record:")
                    for key, value in sample.items():
                        print(f"    {key}: {value}")
                    print()
            elif isinstance(data, dict):
                print(f"  Response: Dict with keys: {list(data.keys())}")
            print()
            break
        else:
            try:
                error = response.json()
                print(f"  Error: {error}")
            except:
                print(f"  Error: {response.text[:200]}")
            print()
    except Exception as e:
        print(f"  Exception: {e}")
        print()

print("If all endpoints failed, check:")
print("  1. Your API key has access to congress trading data")
print("  2. The endpoint format in FMP documentation")
print("  3. Your subscription tier includes this feature")

