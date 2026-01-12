#!/usr/bin/env python3
"""
Clear Flask cache - Utility script to invalidate cached data.

Usage:
    python web_dashboard/debug/clear_cache.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 80)
print("Clear Flask Cache")
print("=" * 80)
print()

try:
    # Option 1: Bump cache version (invalidates all cached functions)
    from cache_version import bump_cache_version, get_cache_version
    
    print("Current cache version:", get_cache_version())
    print("\nBumping cache version...")
    bump_cache_version()
    print("New cache version:", get_cache_version())
    print("\n[OK] Cache version bumped - all cached functions will re-fetch data on next call")
    
except Exception as e:
    print(f"[ERROR] Failed to bump cache version: {e}")
    import traceback
    traceback.print_exc()

try:
    # Option 2: Clear all caches directly
    from flask_cache_utils import clear_all_caches
    
    print("\nClearing all caches...")
    clear_all_caches()
    print("[OK] All caches cleared")
    
except Exception as e:
    print(f"[ERROR] Failed to clear caches: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*80)
print("Done")
print("="*80)
print("\nNote: If Flask app is running, you may need to restart it for cache clearing to take effect.")
print("Or wait for the TTL to expire (typically 5 minutes for portfolio data).")
