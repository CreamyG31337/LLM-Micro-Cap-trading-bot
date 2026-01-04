#!/usr/bin/env python3
"""
Test the performance chart functionality locally
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_performance_chart_locally():
    """Test performance chart by running the Flask app locally"""
    print("Testing performance chart locally...")
    
    # Start the Flask app in the background
    import subprocess
    import time
    import signal
    
    try:
        # Start Flask app
        process = subprocess.Popen([
            "python", "app.py"
        ], cwd=os.getcwd())
        
        # Wait for app to start
        time.sleep(5)
        
        # Test the performance chart endpoint
        url = "http://localhost:5000/api/performance-chart"
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, headers=headers)
            print(f"Performance chart status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print("Chart data received!")
                print(f"Data keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
            else:
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Exception: {e}")
        
        # Stop the Flask app
        process.terminate()
        process.wait()
        
    except Exception as e:
        print(f"Error testing locally: {e}")

def test_performance_data_directly():
    """Test performance data directly from database"""
    print("Testing performance data directly...")
    
    url = "https://injqbxdqyxfvannygadt.supabase.co/rest/v1/performance_metrics"
    headers = {
        "apikey": "SUPABASE_PUBLISHABLE_KEY_REDACTED",
        "Authorization": "Bearer SUPABASE_PUBLISHABLE_KEY_REDACTED",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        print(f"Performance data status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Performance records: {len(data)}")
            if len(data) > 0:
                print("Sample record:", data[0])
                return True
            else:
                print("No performance data found")
                return False
        else:
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {e}")
        return False

if __name__ == "__main__":
    print("Performance Chart Test")
    print("=" * 40)
    
    # Test performance data first
    if test_performance_data_directly():
        print("\nPerformance data exists, testing chart endpoint...")
        test_performance_chart_locally()
    else:
        print("\nNo performance data - this is the problem!")
