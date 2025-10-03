#!/usr/bin/env python3
"""
Test Supabase fund switching functionality
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    print("=== Testing Supabase Connection ===")
    try:
        from supabase_client import SupabaseClient
        client = SupabaseClient()
        print("✅ Supabase client initialized")
        
        # Test connection
        success = client.test_connection()
        print(f"Connection test result: {success}")
        
        # Test getting available funds
        funds = client.get_available_funds()
        print(f"Available funds from Supabase: {funds}")
        
        # Test getting data for Project Chimera
        positions = client.get_current_positions(fund="Project Chimera")
        trades = client.get_trade_log(limit=10, fund="Project Chimera")
        print(f"Project Chimera positions: {len(positions)}")
        print(f"Project Chimera trades: {len(trades)}")
        
        # Test getting data for Webull fund
        positions_webull = client.get_current_positions(fund="RRSP Lance Webull")
        trades_webull = client.get_trade_log(limit=10, fund="RRSP Lance Webull")
        print(f"RRSP Lance Webull positions: {len(positions_webull)}")
        print(f"RRSP Lance Webull trades: {len(trades_webull)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Supabase: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fund_loading():
    print("\n=== Testing Fund Data Loading ===")
    try:
        from app import load_portfolio_data
        
        # Test Project Chimera (should work in Supabase)
        print("1. Testing Project Chimera fund:")
        chimera_data = load_portfolio_data('Project Chimera')
        print(f"   Portfolio records: {len(chimera_data['portfolio'])}")
        print(f"   Trade records: {len(chimera_data['trades'])}")
        print(f"   Available funds: {chimera_data.get('available_funds', [])}")
        print(f"   Current fund: {chimera_data.get('current_fund')}")
        
        print()
        # Test RRSP Lance Webull (should fallback to CSV)
        print("2. Testing RRSP Lance Webull fund:")
        webull_data = load_portfolio_data('RRSP Lance Webull')
        print(f"   Portfolio records: {len(webull_data['portfolio'])}")
        print(f"   Trade records: {len(webull_data['trades'])}")
        print(f"   Available funds: {webull_data.get('available_funds', [])}")
        print(f"   Current fund: {webull_data.get('current_fund')}")
        
        # Check if we got different data
        if not chimera_data['portfolio'].empty and not webull_data['portfolio'].empty:
            print()
            print("3. Data comparison:")
            if 'ticker' in chimera_data['portfolio'].columns:
                chimera_tickers = set(chimera_data['portfolio']['ticker'].tolist())
            else:
                chimera_tickers = set(chimera_data['portfolio']['Ticker'].tolist())
                
            if 'ticker' in webull_data['portfolio'].columns:
                webull_tickers = set(webull_data['portfolio']['ticker'].tolist())
            else:
                webull_tickers = set(webull_data['portfolio']['Ticker'].tolist())
                
            print(f"   Chimera tickers: {len(chimera_tickers)}")
            print(f"   Webull tickers: {len(webull_tickers)}")
            print(f"   Different data: {chimera_tickers != webull_tickers}")
            
            if chimera_tickers == webull_tickers:
                print("   ⚠️  WARNING: Both funds returning same data!")
            else:
                print("   ✅ SUCCESS: Funds returning different data!")
                print(f"   Sample Chimera tickers: {sorted(list(chimera_tickers))[:5]}")
                print(f"   Sample Webull tickers: {sorted(list(webull_tickers))[:5]}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing fund data: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=== Supabase Fund Switching Test ===")
    print()
    
    # Test Supabase connection
    supabase_ok = test_supabase_connection()
    
    # Test fund loading
    fund_loading_ok = test_fund_loading()
    
    print()
    print("=== Test Summary ===")
    print(f"Supabase connection: {'✅ PASS' if supabase_ok else '❌ FAIL'}")
    print(f"Fund loading: {'✅ PASS' if fund_loading_ok else '❌ FAIL'}")

if __name__ == "__main__":
    main()