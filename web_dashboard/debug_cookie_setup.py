#!/usr/bin/env python3
"""
Debug Cookie Setup
==================

Quick script to check cookie configuration and file locations.
Run this in the main container to debug cookie issues.
"""

import os
import json
from pathlib import Path

print("=" * 60)
print("Cookie Setup Debug")
print("=" * 60)

# Check environment variables
print("\n1. Environment Variables:")
webai_cookies_json = os.getenv("WEBAI_COOKIES_JSON")
if webai_cookies_json:
    print(f"   ✅ WEBAI_COOKIES_JSON is set (length: {len(webai_cookies_json)})")
    try:
        cookies = json.loads(webai_cookies_json)
        print(f"   ✅ JSON is valid")
        print(f"   ✅ Has __Secure-1PSID: {'__Secure-1PSID' in cookies}")
        print(f"   ✅ Has __Secure-1PSIDTS: {'__Secure-1PSIDTS' in cookies}")
    except Exception as e:
        print(f"   ❌ JSON is invalid: {e}")
else:
    print("   ⚠️  WEBAI_COOKIES_JSON is NOT set")

secure_1psid = os.getenv("WEBAI_SECURE_1PSID")
secure_1psidts = os.getenv("WEBAI_SECURE_1PSIDTS")
if secure_1psid:
    print(f"   ✅ WEBAI_SECURE_1PSID is set")
if secure_1psidts:
    print(f"   ✅ WEBAI_SECURE_1PSIDTS is set")

# Check shared volume
print("\n2. Shared Volume (/shared/cookies):")
shared_cookie_file = Path("/shared/cookies/webai_cookies.json")
if shared_cookie_file.exists():
    print(f"   ✅ Cookie file exists: {shared_cookie_file}")
    try:
        with open(shared_cookie_file, 'r') as f:
            cookies = json.load(f)
        print(f"   ✅ File is valid JSON")
        print(f"   ✅ Has __Secure-1PSID: {'__Secure-1PSID' in cookies}")
        print(f"   ✅ Has __Secure-1PSIDTS: {'__Secure-1PSIDTS' in cookies}")
        if '__Secure-1PSID' in cookies:
            print(f"   ✅ __Secure-1PSID value: {cookies['__Secure-1PSID'][:50]}...")
    except Exception as e:
        print(f"   ❌ File exists but is invalid: {e}")
else:
    print(f"   ❌ Cookie file does NOT exist: {shared_cookie_file}")
    # Check if directory exists
    if shared_cookie_file.parent.exists():
        print(f"   ℹ️  Directory exists: {shared_cookie_file.parent}")
        print(f"   ℹ️  Directory contents: {list(shared_cookie_file.parent.iterdir())}")
    else:
        print(f"   ❌ Directory does NOT exist: {shared_cookie_file.parent}")

# Check local cookie files
print("\n3. Local Cookie Files:")
project_root = Path(__file__).parent.parent
local_files = [
    project_root / "webai_cookies.json",
    project_root / "ai_service_cookies.json",
    project_root / "web_dashboard" / "webai_cookies.json",
    project_root / "web_dashboard" / "ai_service_cookies.json",
]

for cookie_file in local_files:
    if cookie_file.exists():
        print(f"   ✅ Found: {cookie_file}")
    else:
        print(f"   ⚠️  Not found: {cookie_file}")

# Check what _load_cookies would return
print("\n4. Testing _load_cookies() function:")
try:
    from webai_wrapper import _load_cookies
    secure_1psid, secure_1psidts = _load_cookies()
    if secure_1psid:
        print(f"   ✅ _load_cookies() returned cookies!")
        print(f"   ✅ __Secure-1PSID: {secure_1psid[:50]}...")
        print(f"   ✅ __Secure-1PSIDTS: {secure_1psidts[:50] if secure_1psidts else 'None'}...")
    else:
        print(f"   ❌ _load_cookies() returned None - no cookies found")
except Exception as e:
    print(f"   ❌ Error calling _load_cookies(): {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("Debug Complete")
print("=" * 60)

