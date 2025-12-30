#!/usr/bin/env python3
"""
Test API response directly
"""

import requests

def test_api_response():
    # Test the web dashboard API
    try:
        response = requests.get('http://localhost:5000/api/portfolio?fund=Project%20Chimera', timeout=10)
        print(f'Status Code: {response.status_code}')
        print(f'Response Headers: {dict(response.headers)}')
        print(f'Response Text: {response.text[:500]}')

        if response.status_code == 200:
            data = response.json()
            print(f'Success! Positions: {len(data.get("positions", []))}')
            if data.get('positions'):
                pos = data['positions'][0]
                print(f'Sample PnL: {pos.get("pnl")}')
                print(f'Sample PnL %: {pos.get("pnl_pct")}')
        else:
            print(f'Error: {response.status_code}')

    except Exception as e:
        print(f'Request Error: {e}')

if __name__ == "__main__":
    test_api_response()
