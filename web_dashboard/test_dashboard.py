#!/usr/bin/env python3
"""
Test the dashboard functionality
"""

import requests
import time
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_dashboard():
    """Test if the dashboard is working"""
    print("🧪 Testing Portfolio Dashboard...")
    
    # Wait a moment for Flask to start
    print("⏳ Waiting for Flask to start...")
    time.sleep(3)
    
    try:
        # Test the main page
        response = requests.get('http://localhost:5000', timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard main page: OK")
            print(f"   Content length: {len(response.content)} bytes")
        else:
            print(f"❌ Dashboard main page: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to dashboard: {e}")
        print("   Make sure Flask is running: python app.py")
        return False
    
    try:
        # Test the API endpoints
        api_endpoints = [
            '/api/portfolio',
            '/api/trades',
            '/api/cash',
            '/api/performance'
        ]
        
        for endpoint in api_endpoints:
            try:
                response = requests.get(f'http://localhost:5000{endpoint}', timeout=5)
                if response.status_code == 200:
                    print(f"✅ API {endpoint}: OK")
                else:
                    print(f"⚠️  API {endpoint}: HTTP {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"⚠️  API {endpoint}: {e}")
        
        print("\n🎉 Dashboard test completed!")
        print("🌐 Open your browser and go to: http://localhost:5000")
        return True
        
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
        return False

if __name__ == "__main__":
    test_dashboard()