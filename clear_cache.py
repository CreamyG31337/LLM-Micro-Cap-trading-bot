#!/usr/bin/env python3
"""
Simple Cache Clearing Script for LLM Trading Bot

This script provides quick access to cache clearing functionality without
going through the full UI menu system.
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.cache_manager import get_cache_manager
from display.console_output import print_header, print_success, print_error, print_info, print_warning


def clear_all_caches():
    """Clear all cache types."""
    print_header("🗑️ Clearing All Caches")
    
    cache_manager = get_cache_manager()
    
    # Initialize components
    if not cache_manager.initialize_components():
        print_error("Failed to initialize cache components")
        return False
    
    # Get status before clearing
    status = cache_manager.get_cache_status()
    if status['total_cache_files'] == 0:
        print_info("No cache files found - nothing to clear.")
        return True
    
    print_info(f"Found {status['total_cache_files']} cache files to clear")
    print_info(f"Total cache size: {status.get('total_cache_size_formatted', 'Unknown')}")
    
    # Clear all caches
    print_info("\nClearing caches...")
    results = cache_manager.clear_all_caches()
    
    # Display results
    success_count = sum(1 for result in results.values() if result['success'])
    total_count = len(results)
    
    print_info(f"\nResults: {success_count}/{total_count} operations successful")
    
    for name, result in results.items():
        if result['success']:
            print_success(f"  ✅ {name}: {result['message']}")
        else:
            print_error(f"  ❌ {name}: {result['message']}")
    
    if success_count > 0:
        print_success("\n🎉 Cache clearing completed!")
        return True
    else:
        print_error("\n❌ Failed to clear caches")
        return False


def clear_price_cache_only():
    """Clear only the price cache (both disk and memory)."""
    print_header("🗑️ Clearing Price Cache Only")
    
    cache_manager = get_cache_manager()
    
    # Initialize components
    if not cache_manager.initialize_components():
        print_error("Failed to initialize cache components")
        return False
    
    print_info("Clearing price cache (disk and memory)...")
    results = cache_manager.clear_specific_cache("price_cache")
    
    # Display results
    success_count = sum(1 for result in results.values() if result['success'])
    total_count = len(results)
    
    print_info(f"\nResults: {success_count}/{total_count} operations successful")
    
    for name, result in results.items():
        if result['success']:
            print_success(f"  ✅ {name}: {result['message']}")
        else:
            print_error(f"  ❌ {name}: {result['message']}")
    
    if success_count > 0:
        print_success("\n🎉 Price cache cleared!")
        return True
    else:
        print_error("\n❌ Failed to clear price cache")
        return False


def show_cache_status():
    """Show current cache status."""
    print_header("📊 Cache Status")
    
    cache_manager = get_cache_manager()
    
    # Initialize components
    if not cache_manager.initialize_components():
        print_error("Failed to initialize cache components")
        return False
    
    # Get cache status
    status = cache_manager.get_cache_status()
    
    print_info(f"Cache Enabled: {'✅' if status['cache_enabled'] else '❌'} {status['cache_enabled']}")
    print_info(f"Total Cache Files: {status['total_cache_files']}")
    
    if status['cache_directories']:
        print_info("\n📁 Cache Directories:")
        for name, info in status['cache_directories'].items():
            status_icon = '✅' if info['exists'] else '❌'
            print_info(f"  {name}: {status_icon} {info['size_formatted']} ({info['file_count']} files)")
    
    # Show detailed price cache stats
    stats = cache_manager.get_cache_stats()
    if 'price_cache' in stats and stats['price_cache'].get('total_entries', 0) > 0:
        print_info("\n📈 Price Cache Details:")
        price_stats = stats['price_cache']
        print_info(f"  Entries: {price_stats.get('total_entries', 0)}")
        print_info(f"  Rows: {price_stats.get('total_rows', 0)}")
    
    return True


def main():
    """Main function with simple command-line interface."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command in ['all', 'clear-all']:
            clear_all_caches()
        elif command in ['price', 'clear-price']:
            clear_price_cache_only()
        elif command in ['status', 'show-status']:
            show_cache_status()
        elif command in ['help', '--help', '-h']:
            print_info("Usage: python clear_cache.py [command]")
            print_info("\nCommands:")
            print_info("  all, clear-all     Clear all cache types")
            print_info("  price, clear-price Clear only price cache")
            print_info("  status, show-status Show current cache status")
            print_info("  help               Show this help message")
            print_info("\nIf no command is provided, you'll get an interactive menu.")
        else:
            print_error(f"Unknown command: {command}")
            print_info("Use 'python clear_cache.py help' for available commands")
    else:
        # Interactive menu
        while True:
            print_header("💾 Cache Management")
            print("\nQuick Actions:")
            print("  [1] 📊 Show Cache Status")
            print("  [2] 🗑️ Clear All Caches")
            print("  [3] 🧹 Clear Price Cache Only")
            print("  [0] ❌ Exit")
            
            try:
                choice = input("\n❓ Select option (0-3): ").strip()
                
                if choice == "0":
                    print_info("Goodbye!")
                    break
                elif choice == "1":
                    show_cache_status()
                elif choice == "2":
                    confirmation = input("\n⚠️ Clear ALL caches? This cannot be undone! (yes/NO): ").strip().lower()
                    if confirmation == "yes":
                        clear_all_caches()
                    else:
                        print_info("Cache clearing cancelled.")
                elif choice == "3":
                    clear_price_cache_only()
                else:
                    print_error("Invalid option. Please try again.")
                
                if choice != "0":
                    input("\n⏎ Press Enter to continue...")
                    
            except KeyboardInterrupt:
                print_info("\nGoodbye!")
                break


if __name__ == "__main__":
    main()