#!/usr/bin/env python3
"""
Test script for the portfolio dashboard
Verifies that all components work correctly
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    try:
        import pandas
        print("✅ Pandas imported successfully")
    except ImportError as e:
        print(f"❌ Pandas import failed: {e}")
        return False
    
    try:
        import plotly
        print("✅ Plotly imported successfully")
    except ImportError as e:
        print(f"❌ Plotly import failed: {e}")
        return False
    
    try:
        import yfinance
        print("✅ yfinance imported successfully")
    except ImportError as e:
        print(f"❌ yfinance import failed: {e}")
        return False
    
    return True

def test_data_loading():
    """Test that data can be loaded from CSV files"""
    print("\n🧪 Testing data loading...")
    
    try:
        from app import load_portfolio_data
        data = load_portfolio_data()
        
        print(f"✅ Portfolio data loaded: {len(data['portfolio'])} entries")
        print(f"✅ Trade data loaded: {len(data['trades'])} entries")
        print(f"✅ Cash balances: {data['cash_balances']}")
        
        return True
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        return False

def test_metrics_calculation():
    """Test that performance metrics can be calculated"""
    print("\n🧪 Testing metrics calculation...")
    
    try:
        from app import load_portfolio_data, calculate_performance_metrics
        data = load_portfolio_data()
        metrics = calculate_performance_metrics(data['portfolio'], data['trades'])
        
        print(f"✅ Total value: ${metrics['total_value']}")
        print(f"✅ Performance: {metrics['performance_pct']}%")
        print(f"✅ Unrealized P&L: ${metrics['unrealized_pnl']}")
        print(f"✅ Total trades: {metrics['total_trades']}")
        
        return True
    except Exception as e:
        print(f"❌ Metrics calculation failed: {e}")
        return False

def test_chart_generation():
    """Test that performance charts can be generated"""
    print("\n🧪 Testing chart generation...")
    
    try:
        from app import load_portfolio_data, create_performance_chart
        data = load_portfolio_data()
        chart_data = create_performance_chart(data['portfolio'])
        
        if chart_data and chart_data != '{}':
            print("✅ Performance chart generated successfully")
        else:
            print("⚠️  No chart data (empty portfolio)")
        
        return True
    except Exception as e:
        print(f"❌ Chart generation failed: {e}")
        return False

def test_flask_app():
    """Test that the Flask app can be created"""
    print("\n🧪 Testing Flask app creation...")
    
    try:
        from app import app
        print("✅ Flask app created successfully")
        
        # Test that routes exist
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✅ Main route works")
            else:
                print(f"❌ Main route failed: {response.status_code}")
                return False
            
            response = client.get('/api/portfolio')
            if response.status_code == 200:
                print("✅ Portfolio API works")
            else:
                print(f"❌ Portfolio API failed: {response.status_code}")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Flask app test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Portfolio Dashboard Tests\n")
    
    tests = [
        test_imports,
        test_data_loading,
        test_metrics_calculation,
        test_chart_generation,
        test_flask_app
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dashboard is ready to deploy.")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
