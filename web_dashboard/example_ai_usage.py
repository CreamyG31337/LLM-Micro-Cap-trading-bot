#!/usr/bin/env python3
"""
Example: Using AI Service Client
=================================

Simple example showing how to use the AI service client in your code.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

from ai_service_client import AIServiceClient


def main():
    # Try to find cookies file in project root or web_dashboard
    project_root = Path(__file__).parent.parent
    cookie_names = ["webai_cookies.json", "ai_service_cookies.json"]
    
    cookies_file = None
    for name in cookie_names:
        root_cookie = project_root / name
        web_cookie = project_root / "web_dashboard" / name
        if root_cookie.exists():
            cookies_file = root_cookie
            break
        elif web_cookie.exists():
            cookies_file = web_cookie
            break
    
    if not cookies_file:
        print("❌ Cookie file not found!")
        print(f"   Checked locations:")
        for name in cookie_names:
            print(f"   - {project_root / name}")
            print(f"   - {project_root / 'web_dashboard' / name}")
        print("\n   Please extract cookies first:")
        print("   python web_dashboard/extract_ai_cookies.py --browser manual")
        return 1
    
    # Initialize client
    print(f"[OK] Initializing AI service client...")
    print(f"   Using cookies from: {cookies_file}")
    client = AIServiceClient(cookies_file=str(cookies_file))
    
    # Test authentication
    print("🧪 Testing authentication...")
    if not client.test_authentication():
        print("❌ Authentication failed!")
        print("   Your cookies may have expired.")
        print("   Please extract fresh cookies:")
        print("   python web_dashboard/extract_ai_cookies.py --browser manual")
        return 1
    
    print("✅ Authentication successful!\n")
    
    # Example 1: Simple query
    print("=" * 60)
    print("Example 1: Simple Query")
    print("=" * 60)
    response = client.query("What is Python in one sentence?")
    if response:
        print(response)
    else:
        print("❌ Failed to get response")
    
    print("\n" + "=" * 60)
    print("Example 2: Trading Analysis Query")
    print("=" * 60)
    
    # Example 2: Trading-related query (like your use case)
    trading_prompt = """
    Analyze this trading scenario:
    - Stock: AAPL
    - Current Price: $150
    - 52-week high: $200
    - 52-week low: $120
    - Volume: Above average
    
    Provide a brief analysis and recommendation.
    """
    
    response = client.query(trading_prompt)
    if response:
        print(response)
    else:
        print("❌ Failed to get response")
    
    print("\n" + "=" * 60)
    print("✅ Examples complete!")
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

