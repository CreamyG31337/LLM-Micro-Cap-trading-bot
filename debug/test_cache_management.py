#!/usr/bin/env python3
"""
Test script for cache management functionality.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from utils.cache_manager import get_cache_manager
    from utils.cache_ui import CacheUI

    def test_cache_manager():
        """Test cache manager functionality."""
        print("Testing cache manager...")

        cache_manager = get_cache_manager()

        # Initialize components
        if cache_manager.initialize_components():
            print("✅ Cache manager initialized successfully")

            # Test cache status
            status = cache_manager.get_cache_status()
            print(f"✅ Cache status retrieved: {status['total_cache_files']} files, {status['total_cache_size_formatted']} total")

            # Test cache stats
            stats = cache_manager.get_cache_stats()
            print(f"✅ Cache stats retrieved: {len(stats)} cache types")

            print("\nCache Status Details:")
            for cache_type, info in status['cache_directories'].items():
                if info['exists']:
                    print(f"  {cache_type}: {info['file_count']} files ({info['size_formatted']})")

            return True
        else:
            print("❌ Failed to initialize cache manager")
            return False

    def test_cache_ui():
        """Test cache UI functionality."""
        print("\nTesting cache UI...")

        try:
            cache_ui = CacheUI()
            print("✅ Cache UI initialized successfully")
            return True
        except Exception as e:
            print(f"❌ Cache UI initialization failed: {e}")
            return False

    if __name__ == "__main__":
        print("=" * 60)
        print("CACHE MANAGEMENT TEST")
        print("=" * 60)

        manager_ok = test_cache_manager()
        ui_ok = test_cache_ui()

        print("\n" + "=" * 60)
        if manager_ok and ui_ok:
            print("✅ ALL TESTS PASSED - Cache management is working!")
        else:
            print("❌ SOME TESTS FAILED - Check error messages above")
        print("=" * 60)

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the project root with the virtual environment activated.")
