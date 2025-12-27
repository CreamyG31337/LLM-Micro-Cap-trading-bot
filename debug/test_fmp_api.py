#!/usr/bin/env python3
"""
Test FMP API Directly
=====================

Quick test to verify FMP API connectivity and response format.
Tests both House and Senate endpoints with pagination.

Usage:
    python debug/test_fmp_api.py
"""

import os
import sys
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
env_path = project_root / 'web_dashboard' / '.env'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

print("=" * 70)
print("FMP API TEST")
print("=" * 70)
print()

# Get API key
fmp_api_key = os.getenv("FMP_API_KEY")
if not fmp_api_key:
    print("❌ ERROR: FMP_API_KEY not found in environment")
    print("   Please add it to web_dashboard/.env file")
    sys.exit(1)

print(f"✅ FMP_API_KEY found: {fmp_api_key[:10]}...{fmp_api_key[-4:]}")
print()

# Base URLs to try
base_urls = [
    "https://financialmodelingprep.com/api/v4",
    "https://financialmodelingprep.com/api/v3",
    "https://api.fmfw.io/v2",
    "https://financialmodelingprep.com/api",
]

# Test endpoints - try different base URLs and endpoint formats
# Note: v4 endpoints are legacy, trying v3 and other formats
endpoint_paths = [
    '/senate-trading',
    '/house-trading',
    '/senate-disclosure',
    '/house-disclosure',
    '/congress-trading',
    '/congress-disclosure',
]

# Calculate cutoff (7 days ago)
cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

print(f"Cutoff date (7 days ago): {cutoff_date.date()}")
print()
print("=" * 70)
print()

# Try each base URL with each endpoint path
for base_url in base_urls:
    print(f"Testing base URL: {base_url}")
    print()
    
    for endpoint_path in endpoint_paths:
        endpoint = f"{base_url}{endpoint_path}"
        chamber = endpoint_path.replace('/', '').replace('-', ' ').title()
        
        if 'senate' in endpoint_path.lower() or 'house' in endpoint_path.lower():
            # Only test senate/house specific endpoints
            pass
        elif 'congress' in endpoint_path.lower():
            # Test congress endpoints
            pass
        else:
            continue
    print(f"Testing {chamber} endpoint...")
    print(f"URL: {endpoint}")
    print()
    
    # Test first page - try different parameter formats
    page = 0
    
    # Try different parameter formats
    param_formats = [
        {'page': page, 'apikey': fmp_api_key},
        {'page': page, 'apiKey': fmp_api_key},
        {'page': page, 'APIkey': fmp_api_key},
    ]
    
    # Also try with API key in header
    headers = {
        'apikey': fmp_api_key,
        'APIkey': fmp_api_key,
    }
    
    response = None
    params_used = None
    last_error = None
    
    for params in param_formats:
        try:
            print(f"  Trying params: {list(params.keys())}...")
            test_response = requests.get(endpoint, params=params, timeout=10)
            if test_response.status_code == 200:
                response = test_response
                params_used = params
                print(f"  ✅ Got 200 response with params: {list(params.keys())}")
                break
            elif test_response.status_code != 403:
                # Got a different error, might be progress
                print(f"  Got status {test_response.status_code} (not 403)")
                response = test_response
                params_used = params
                break
            else:
                # 403 - check error message
                try:
                    error_data = test_response.json()
                    last_error = error_data
                except:
                    last_error = test_response.text[:200]
        except Exception as e:
            last_error = str(e)
            continue
    
    # If params didn't work, try with headers
    if not response or response.status_code == 403:
        try:
            print(f"  Trying with API key in headers...")
            test_response = requests.get(endpoint, params={'page': page}, headers=headers, timeout=10)
            if test_response.status_code == 200:
                response = test_response
                params_used = {'page': page, 'api_key_in_header': True}
            elif test_response.status_code != 403:
                response = test_response
                params_used = {'page': page, 'api_key_in_header': True}
        except Exception as e:
            last_error = str(e)
    
    if not response or response.status_code == 403:
        print(f"  ❌ All authentication methods failed (403 Forbidden)")
        if last_error:
            print(f"  Last error: {last_error}")
        print()
        print("=" * 70)
        print()
        continue
    
    try:
        response.raise_for_status()
        
        print(f"  Status: {response.status_code}")
        print(f"  Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        print(f"  Content-Length: {len(response.content)} bytes")
        print()
        
        # Try to parse as JSON
        try:
            data = response.json()
            print(f"  ✅ Response is JSON")
            
            # Check structure
            if isinstance(data, list):
                print(f"  ✅ Response is a list with {len(data)} items")
                trades = data
            elif isinstance(data, dict):
                print(f"  ✅ Response is a dict with keys: {list(data.keys())}")
                trades = data.get('results', data.get('data', []))
            else:
                print(f"  ⚠️  Unexpected response type: {type(data)}")
                trades = []
            
            if trades:
                print(f"  Found {len(trades)} trades on page {page}")
                print()
                print("  Sample trade (first item):")
                sample = trades[0]
                if isinstance(sample, dict):
                    for key, value in list(sample.items())[:10]:  # Show first 10 fields
                        print(f"    {key}: {value}")
                    if len(sample) > 10:
                        print(f"    ... ({len(sample) - 10} more fields)")
                else:
                    print(f"    {sample}")
                print()
                
                # Check for date fields
                date_fields = ['disclosureDate', 'disclosure_date', 'date', 'transactionDate', 'transaction_date', 'trade_date']
                found_dates = []
                for field in date_fields:
                    if field in sample:
                        found_dates.append(field)
                        print(f"  ✅ Found date field: {field} = {sample[field]}")
                
                if not found_dates:
                    print("  ⚠️  No standard date fields found in sample")
                    print(f"     Available fields: {list(sample.keys()) if isinstance(sample, dict) else 'N/A'}")
                
                # Check for ticker field
                ticker_fields = ['ticker', 'symbol', 'stock']
                found_ticker = False
                for field in ticker_fields:
                    if field in sample:
                        found_ticker = True
                        print(f"  ✅ Found ticker field: {field} = {sample[field]}")
                        break
                
                if not found_ticker:
                    print("  ⚠️  No ticker field found")
                    print(f"     Available fields: {list(sample.keys()) if isinstance(sample, dict) else 'N/A'}")
                
            else:
                print(f"  ⚠️  No trades found on page {page}")
            
            # Test pagination - try page 1
            if page == 0:
                print()
                print(f"  Testing pagination (page 1)...")
                params['page'] = 1
                response2 = requests.get(endpoint, params=params, timeout=30)
                response2.raise_for_status()
                data2 = response2.json()
                
                if isinstance(data2, list):
                    trades2 = data2
                elif isinstance(data2, dict):
                    trades2 = data2.get('results', data2.get('data', []))
                else:
                    trades2 = []
                
                if trades2:
                    print(f"  ✅ Page 1 returned {len(trades2)} trades")
                    if len(trades2) != len(trades):
                        print(f"  ✅ Different number of trades (pagination working)")
                    else:
                        print(f"  ⚠️  Same number of trades (may be duplicates or end of data)")
                else:
                    print(f"  ⚠️  Page 1 returned no trades")
            
        except json.JSONDecodeError:
            print(f"  ⚠️  Response is not JSON, trying XML/RSS...")
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(response.content)
                print(f"  ✅ Response is XML")
                print(f"  Root tag: {root.tag}")
                items = root.findall('.//item')
                print(f"  Found {len(items)} <item> elements")
                if items:
                    print("  Sample item structure:")
                    for child in items[0][:5]:  # Show first 5 children
                        print(f"    {child.tag}: {child.text[:100] if child.text else 'None'}")
            except Exception as xml_error:
                print(f"  ❌ Failed to parse as XML: {xml_error}")
                print(f"  First 500 chars of response:")
                print(f"  {response.text[:500]}")
        
        print()
        print("=" * 70)
        print()
        
    except requests.exceptions.RequestException as e:
        print(f"  ❌ Request failed: {e}")
        print()
        print("=" * 70)
        print()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 70)
        print()

print("Test complete!")
print()
print("Next steps:")
print("  1. If API works, run: python debug/test_congress_trades_job.py")
print("  2. Check the response format matches what the job expects")
print("  3. Verify date parsing works with the actual date format")

