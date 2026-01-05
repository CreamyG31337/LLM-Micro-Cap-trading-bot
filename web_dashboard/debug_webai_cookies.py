#!/usr/bin/env python3
"""
Debug WebAI Cookie Configuration
================================

Diagnostic script to help debug WebAI cookie loading issues.
"""

import os
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'web_dashboard'))

def debug_cookies():
    """Debug cookie configuration."""
    print("=" * 60)
    print("WebAI Cookie Configuration Debug")
    print("=" * 60)
    
    # Check environment variable
    cookies_json = os.getenv("WEBAI_COOKIES_JSON")
    print(f"\n1. WEBAI_COOKIES_JSON environment variable:")
    print(f"   Set: {bool(cookies_json)}")
    
    if cookies_json:
        print(f"   Length: {len(cookies_json)}")
        print(f"   First 100 chars: {repr(cookies_json[:100])}")
        print(f"   Last 100 chars: {repr(cookies_json[-100:])}")
        
        # Try to parse
        try:
            # Clean up like the actual code does
            original = cookies_json
            cleaned = cookies_json.strip()
            
            # Remove outer quotes
            if len(cleaned) >= 2:
                if cleaned.startswith('"') and cleaned.endswith('"') and cleaned[1] in ['{', '[']:
                    cleaned = cleaned[1:-1]
                elif cleaned.startswith("'") and cleaned.endswith("'") and cleaned[1] in ['{', '[']:
                    cleaned = cleaned[1:-1]
            
            # Replace newlines
            cleaned = cleaned.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
            import re
            cleaned = re.sub(r' +', ' ', cleaned)
            
            print(f"\n   After cleaning:")
            print(f"   Length: {len(cleaned)}")
            print(f"   First 200 chars: {repr(cleaned[:200])}")
            
            # Try to parse
            try:
                parsed = json.loads(cleaned)
                print(f"\n   ✅ JSON parsing: SUCCESS")
                print(f"   Has __Secure-1PSID: {'__Secure-1PSID' in parsed}")
                print(f"   Has __Secure-1PSIDTS: {'__Secure-1PSIDTS' in parsed}")
                if '__Secure-1PSID' in parsed:
                    print(f"   __Secure-1PSID length: {len(parsed['__Secure-1PSID'])}")
                    print(f"   __Secure-1PSID starts with: {parsed['__Secure-1PSID'][:20]}...")
            except json.JSONDecodeError as e:
                print(f"\n   ❌ JSON parsing: FAILED")
                print(f"   Error: {e}")
                print(f"   Error position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
                
                # Try double-encoding check
                try:
                    decoded = json.loads(cleaned)
                    if isinstance(decoded, str):
                        print(f"   ⚠️  Value appears to be double-encoded (JSON string)")
                        print(f"   Trying to decode again...")
                        parsed2 = json.loads(decoded)
                        print(f"   ✅ Double-decoding: SUCCESS")
                        print(f"   Has __Secure-1PSID: {'__Secure-1PSID' in parsed2}")
                except:
                    pass
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Check individual env vars
    print(f"\n2. Individual environment variables:")
    print(f"   WEBAI_SECURE_1PSID: {bool(os.getenv('WEBAI_SECURE_1PSID'))}")
    print(f"   WEBAI_SECURE_1PSIDTS: {bool(os.getenv('WEBAI_SECURE_1PSIDTS'))}")
    
    # Check cookie files
    print(f"\n3. Cookie files:")
    cookie_names = ["webai_cookies.json", "ai_service_cookies.json"]
    for name in cookie_names:
        root_cookie = project_root / name
        web_cookie = project_root / "web_dashboard" / name
        
        print(f"\n   {name}:")
        print(f"     Root: {root_cookie.exists()} ({root_cookie})")
        print(f"     Web: {web_cookie.exists()} ({web_cookie})")
        
        for cookie_file in [root_cookie, web_cookie]:
            if cookie_file.exists():
                try:
                    with open(cookie_file, 'r', encoding='utf-8') as f:
                        cookies = json.load(f)
                    print(f"     ✅ Valid JSON")
                    print(f"     Has __Secure-1PSID: {'__Secure-1PSID' in cookies}")
                    print(f"     Has __Secure-1PSIDTS: {'__Secure-1PSIDTS' in cookies}")
                    break
                except Exception as e:
                    print(f"     ❌ Error reading: {e}")
    
    # Test the actual _load_cookies function
    print(f"\n4. Testing _load_cookies() function:")
    try:
        from webai_wrapper import _load_cookies
        
        secure_1psid, secure_1psidts = _load_cookies()
        if secure_1psid:
            print(f"   ✅ Cookies loaded successfully!")
            print(f"   __Secure-1PSID: {secure_1psid[:50]}...")
            print(f"   __Secure-1PSIDTS: {secure_1psidts[:50] if secure_1psidts else 'None'}...")
        else:
            print(f"   ❌ No cookies found")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)
    
    if not cookies_json and not any((project_root / name).exists() or (project_root / "web_dashboard" / name).exists() for name in cookie_names):
        print("1. Set WEBAI_COOKIES_JSON environment variable, OR")
        print("2. Create webai_cookies.json file in project root")
        print("3. Run: python web_dashboard/extract_ai_cookies.py --browser manual")
    
    if cookies_json:
        print("\nIf WEBAI_COOKIES_JSON is set but not working:")
        print("1. Ensure it's a single-line JSON string (no newlines)")
        print("2. Format: {\"__Secure-1PSID\":\"...\",\"__Secure-1PSIDTS\":\"...\"}")
        print("3. Check for extra quotes or escaping issues")
        print("4. In Woodpecker, paste the JSON as a single line without newlines")

if __name__ == "__main__":
    debug_cookies()

