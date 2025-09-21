"""Cache Management User Interface.

This module provides user interface functions for cache management operations.
"""

import os
from typing import Dict, Any

from display.console_output import print_header, print_success, print_error, print_warning, print_info, _safe_emoji
from .cache_manager import get_cache_manager, CacheManager


class CacheUI:
    """User interface for cache management operations."""

    def __init__(self):
        """Initialize cache UI."""
        self.cache_manager = get_cache_manager()

    def show_cache_status(self) -> None:
        """Display comprehensive cache status."""
        print_header("📊 Cache Status", _safe_emoji("💾"))

        # Initialize components
        if not self.cache_manager.initialize_components():
            print_error("Failed to initialize cache components")
            return

        # Get cache status
        status = self.cache_manager.get_cache_status()

        print_info(f"Cache Enabled: {_safe_emoji('✅') if status['cache_enabled'] else _safe_emoji('❌')} {status['cache_enabled']}")
        print_info(f"Total Cache Files: {status['total_cache_files']}")
        print_info(f"Total Cache Size: {status['total_cache_size_formatted']}")

        if status['cache_directories']:
            print_info("\n📁 Cache Directories:")
            for name, info in status['cache_directories'].items():
                status_icon = _safe_emoji('✅') if info['exists'] else _safe_emoji('❌')
                print_info(f"  {name}: {status_icon} {info['size_formatted']} ({info['file_count']} files)")

        # Show detailed stats
        stats = self.cache_manager.get_cache_stats()
        if 'price_cache' in stats and stats['price_cache']['total_entries'] > 0:
            print_info("
📈 Price Cache Details:"            price_stats = stats['price_cache']
            print_info(f"  Entries: {price_stats['total_entries']}")
            print_info(f"  Rows: {price_stats['total_rows']}")
            if 'sources' in price_stats and price_stats['sources']:
                print_info(f"  Sources: {', '.join(price_stats['sources'].keys())}")

    def show_cache_menu(self) -> None:
        """Display cache management menu."""
        while True:
            print_header("💾 Cache Management Menu", _safe_emoji("🗂️"))

            print("\nAvailable cache operations:")
            print(f"  [1] {_safe_emoji('📊')} View Cache Status")
            print(f"  [2] {_safe_emoji('🗑️')} Clear All Caches")
            print(f"  [3] {_safe_emoji('🧹')} Clear Specific Cache")
            print(f"  [4] {_safe_emoji('🔄')} Update All Caches")
            print(f"  [0] {_safe_emoji('⬅️')} Back to Main Menu")

            try:
                choice = input(f"\n{_safe_emoji('❓')} Select option (0-4): ").strip()

                if choice == "0":
                    print_info("Returning to main menu...")
                    return
                elif choice == "1":
                    self.show_cache_status()
                elif choice == "2":
                    self.clear_all_caches_menu()
                elif choice == "3":
                    self.clear_specific_cache_menu()
                elif choice == "4":
                    self.update_all_caches_menu()
                else:
                    print_error("Invalid option. Please try again.")

            except KeyboardInterrupt:
                print_info("\nReturning to main menu...")
                return

            input(f"\n{_safe_emoji('⏎')} Press Enter to continue...")

    def clear_all_caches_menu(self) -> None:
        """Menu for clearing all caches."""
        print_header("🗑️ Clear All Caches", _safe_emoji("⚠️"))

        # Show current status first
        status = self.cache_manager.get_cache_status()
        if status['total_cache_files'] == 0:
            print_info("No cache files found - nothing to clear.")
            return

        print_warning("This will clear ALL cache files and data!")
        print_warning(f"Total files to be removed: {status['total_cache_files']}")
        print_warning(f"Total size: {status['total_cache_size_formatted']}")

        print_info("\nAffected caches:")
        for name, info in status['cache_directories'].items():
            if info['exists'] and info['file_count'] > 0:
                print_info(f"  • {name}: {info['file_count']} files ({info['size_formatted']})")

        confirmation = input(f"\n{_safe_emoji('⚠️')} Are you sure you want to clear ALL caches? (yes/NO): ").strip().lower()

        if confirmation == "yes":
            print_info("Clearing all caches...")
            results = self.cache_manager.clear_all_caches()

            # Display results
            success_count = sum(1 for result in results.values() if result['success'])
            total_count = len(results)

            print_info(f"\nClear Results: {success_count}/{total_count} operations successful")

            for name, result in results.items():
                if result['success']:
                    print_success(f"  {_safe_emoji('✅')} {name}: {result['message']}")
                else:
                    print_error(f"  {_safe_emoji('❌')} {name}: {result['message']}")

            if success_count > 0:
                print_success("All caches cleared successfully!")
        else:
            print_info("Cache clearing cancelled.")

    def clear_specific_cache_menu(self) -> None:
        """Menu for clearing specific cache types."""
        print_header("🧹 Clear Specific Cache", _safe_emoji("🎯"))

        print("Available cache types:")
        print("  [1] Price Cache (market data)")
        print("  [2] Fundamentals Cache (company data)")
        print("  [3] Exchange Rate Cache (currency conversions)")

        try:
            choice = input(f"\n{_safe_emoji('❓')} Select cache type to clear (1-3): ").strip()

            cache_types = {
                "1": "price_cache",
                "2": "fundamentals_cache",
                "3": "exchange_rate_cache"
            }

            if choice not in cache_types:
                print_error("Invalid cache type selection.")
                return

            cache_type = cache_types[choice]
            cache_names = {
                "price_cache": "Price Cache",
                "fundamentals_cache": "Fundamentals Cache",
                "exchange_rate_cache": "Exchange Rate Cache"
            }

            confirmation = input(f"\n{_safe_emoji('⚠️')} Clear {cache_names[cache_type]}? (yes/NO): ").strip().lower()

            if confirmation == "yes":
                print_info(f"Clearing {cache_names[cache_type]}...")
                results = self.cache_manager.clear_specific_cache(cache_type)

                success_count = sum(1 for result in results.values() if result['success'])
                total_count = len(results)

                print_info(f"\nClear Results: {success_count}/{total_count} operations successful")

                for name, result in results.items():
                    if result['success']:
                        print_success(f"  {_safe_emoji('✅')} {name}: {result['message']}")
                    else:
                        print_error(f"  {_safe_emoji('❌')} {name}: {result['message']}")

                if success_count > 0:
                    print_success(f"{cache_names[cache_type]} cleared successfully!")
            else:
                print_info("Cache clearing cancelled.")

        except KeyboardInterrupt:
            print_info("Cache clearing cancelled.")

    def update_all_caches_menu(self) -> None:
        """Menu for updating all caches."""
        print_header("🔄 Update All Caches", _safe_emoji("📡"))

        print_info("This will refresh all cache data with current information.")
        print_info("Note: This may take some time depending on market data availability.")

        confirmation = input(f"\n{_safe_emoji('❓')} Update all caches? (yes/NO): ").strip().lower()

        if confirmation == "yes":
            print_info("Updating all caches...")
            results = self.cache_manager.update_all_caches()

            success_count = sum(1 for result in results.values() if result['success'])
            total_count = len(results)

            print_info(f"\nUpdate Results: {success_count}/{total_count} operations successful")

            for name, result in results.items():
                if result['success']:
                    print_success(f"  {_safe_emoji('✅')} {name}: {result['message']}")
                else:
                    print_error(f"  {_safe_emoji('❌')} {name}: {result['message']}")

            if success_count > 0:
                print_success("Cache update completed!")
        else:
            print_info("Cache update cancelled.")


def show_cache_management_menu() -> None:
    """Show the cache management menu (standalone function for easy calling)."""
    cache_ui = CacheUI()
    cache_ui.show_cache_menu()
