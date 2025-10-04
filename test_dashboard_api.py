#!/usr/bin/env python3
"""
Test web dashboard API directly
"""

import requests
import json

def test_dashboard_api():
    # Test the web dashboard API
    try:
        response = requests.get('http://localhost:5000/api/portfolio?fund=Project%20Chimera', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print('✅ API Response Status: 200')
            print(f'Positions: {len(data.get("positions", []))}')
            print(f'Metrics: {data.get("metrics", {})}')

            if data.get('positions'):
                pos = data['positions'][0]
                print(f'\nSample Position:')
                print(f'  Ticker: {pos.get("ticker")}')
                print(f'  PnL: {pos.get("pnl")}')
                print(f'  PnL %: {pos.get("pnl_pct")}')

                # Check total metrics
                metrics = data.get('metrics', {})
                print(f'\nTotal Metrics:')
                print(f'  Unrealized PnL: {metrics.get("unrealized_pnl")}')
                print(f'  Performance %: {metrics.get("performance_pct")}')
        else:
            print(f'❌ API Error: {response.status_code}')
            print(response.text)
    except Exception as e:
        print(f'❌ Connection Error: {e}')

if __name__ == "__main__":
    test_dashboard_api()
