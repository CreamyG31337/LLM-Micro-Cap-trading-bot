#!/usr/bin/env python3
"""
Test web dashboard API endpoint
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

def test_api_endpoint():
    # Add project root to path
    project_root = Path.cwd()
    sys.path.insert(0, str(project_root))

    # Test the web dashboard API endpoint directly
    sys.path.append(str(project_root / 'web_dashboard'))

    # Import Flask app and test the API
    from app import app

    print('=== Testing Web Dashboard API Endpoint ===')
    with app.test_client() as client:
        try:
            # Test the portfolio API
            response = client.get('/api/portfolio?fund=Project Chimera')
            if response.status_code == 200:
                data = response.get_json()
                print(f'API response status: {response.status_code}')
                print(f'Positions count: {len(data.get("positions", []))}')

                if data.get('positions'):
                    pos = data['positions'][0]
                    print(f'Sample position keys: {list(pos.keys())}')
                    print(f'Sample position PnL: {pos.get("pnl")}')
                    print(f'Sample position PnL %: {pos.get("pnl_pct")}')

                    # Check if PnL values are correct
                    positions_with_pnl = [p for p in data['positions'] if p.get('pnl', 0) != 0]
                    print(f'Positions with non-zero PnL: {len(positions_with_pnl)}')

                    if positions_with_pnl:
                        sample = positions_with_pnl[0]
                        print(f'Sample non-zero PnL: {sample["ticker"]} - ${sample["pnl"]} ({sample["pnl_pct"]}%)')
            else:
                print(f'API error: {response.status_code}')
                print(response.get_json())

        except Exception as e:
            print(f'Error testing API: {e}')
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_api_endpoint()
