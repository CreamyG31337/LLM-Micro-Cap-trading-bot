"""Cache Management System.

This module provides comprehensive cache management functionality for the trading bot,
including status display, deletion, and update operations for all cache types.
"""

import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from config.settings import Settings, get_settings
from market_data.price_cache import PriceCache
from market_data.data_fetcher import MarketDataFetcher
from financial.currency_handler import CurrencyHandler

logger = logging.getLogger(__name__)


class CacheManager:
    """Comprehensive cache management system."""

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize cache manager.

        Args:
            settings: Optional settings instance
        """
        self.settings = settings or get_settings()
        self.price_cache: Optional[PriceCache] = None
        self.data_fetcher: Optional[MarketDataFetcher] = None
        self.currency_handler: Optional[CurrencyHandler] = None

    def get_cache_directories(self) -> Dict[str, Path]:
        """Get all cache directory paths.

        Returns:
            Dictionary mapping cache names to their directory paths
        """
        try:
            data_dir = Path(self.settings.get_data_directory())
        except Exception:
            # Fallback to current directory if data directory not available
            data_dir = Path.cwd()

        return {
            "price_cache": data_dir / ".cache",
            "fundamentals_cache": data_dir / ".cache",
            "exchange_rates_cache": data_dir / ".cache",
            "main_cache_dir": data_dir / ".cache"
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics for all cache types
        """
        stats = {}

        # Price cache stats
        if self.price_cache:
            stats["price_cache"] = self.price_cache.get_cache_stats()
        else:
            stats["price_cache"] = {"total_entries": 0, "total_rows": 0}

        # Cache directory stats
        cache_dirs = self.get_cache_directories()
        for name, cache_dir in cache_dirs.items():
            if cache_dir.exists():
                files = list(cache_dir.rglob("*"))
                file_stats = {
                    "total_files": len(files),
                    "total_size": sum(f.stat().st_size for f in files if f.is_file()),
                    "oldest_file": None,
                    "newest_file": None
                }

                if files:
                    file_stats["oldest_file"] = min(files, key=lambda f: f.stat().st_mtime)
                    file_stats["newest_file"] = max(files, key=lambda f: f.stat().st_mtime)

                stats[name] = file_stats
            else:
                stats[name] = {"total_files": 0, "total_size": 0}

        return stats

    def get_cache_status(self) -> Dict[str, Any]:
        """Get overall cache status.

        Returns:
            Dictionary with cache status information
        """
        cache_dirs = self.get_cache_directories()
        stats = self.get_cache_stats()

        status = {
            "cache_enabled": self.settings.get('market_data.cache_enabled', True),
            "cache_directories": {},
            "total_cache_files": 0,
            "total_cache_size": 0,
            "cache_types": []
        }

        for name, cache_dir in cache_dirs.items():
            if cache_dir.exists():
                files = list(cache_dir.rglob("*"))
                size = sum(f.stat().st_size for f in files if f.is_file())
                status["total_cache_files"] += len(files)
                status["total_cache_size"] += size
                status["cache_directories"][name] = {
                    "path": str(cache_dir),
                    "exists": True,
                    "file_count": len(files),
                    "size_bytes": size,
                    "size_formatted": self._format_size(size)
                }
                status["cache_types"].append(name)
            else:
                status["cache_directories"][name] = {
                    "path": str(cache_dir),
                    "exists": False,
                    "file_count": 0,
                    "size_bytes": 0,
                    "size_formatted": "0 B"
                }

        # Add formatted total size
        status["total_cache_size_formatted"] = self._format_size(status["total_cache_size"])

        return status

    def clear_all_caches(self) -> Dict[str, Any]:
        """Clear all cache types.

        Returns:
            Dictionary with results of cache clearing operations
        """
        results = {}
        cache_dirs = self.get_cache_directories()

        for name, cache_dir in cache_dirs.items():
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    results[name] = {"success": True, "message": f"Cleared {name}"}
                except Exception as e:
                    results[name] = {"success": False, "message": f"Failed to clear {name}: {e}"}
            else:
                results[name] = {"success": True, "message": f"{name} already clear"}

        # Clear in-memory caches
        try:
            if self.price_cache:
                self.price_cache.invalidate_all()
            results["price_cache_memory"] = {"success": True, "message": "Cleared price cache"}
        except Exception as e:
            results["price_cache_memory"] = {"success": False, "message": f"Failed to clear price cache: {e}"}

        try:
            if self.currency_handler:
                self.currency_handler.clear_exchange_rate_cache()
            results["exchange_rate_cache"] = {"success": True, "message": "Cleared exchange rate cache"}
        except Exception as e:
            results["exchange_rate_cache"] = {"success": False, "message": f"Failed to clear exchange rate cache: {e}"}

        return results

    def clear_specific_cache(self, cache_type: str) -> Dict[str, Any]:
        """Clear specific cache type.

        Args:
            cache_type: Type of cache to clear (price_cache, fundamentals_cache, etc.)

        Returns:
            Dictionary with results of cache clearing operation
        """
        results = {}

        if cache_type == "price_cache":
            # Clear disk cache
            cache_dirs = self.get_cache_directories()
            cache_dir = cache_dirs["price_cache"]
            if cache_dir.exists():
                try:
                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir(parents=True, exist_ok=True)
                    results["disk_cache"] = {"success": True, "message": "Cleared price cache disk files"}
                except Exception as e:
                    results["disk_cache"] = {"success": False, "message": f"Failed to clear disk cache: {e}"}

            # Clear in-memory cache
            try:
                if self.price_cache:
                    self.price_cache.invalidate_all()
                results["memory_cache"] = {"success": True, "message": "Cleared price cache memory"}
            except Exception as e:
                results["memory_cache"] = {"success": False, "message": f"Failed to clear memory cache: {e}"}

        elif cache_type == "fundamentals_cache":
            cache_dirs = self.get_cache_directories()
            cache_dir = cache_dirs["fundamentals_cache"]
            if cache_dir.exists():
                try:
                    # Remove only fundamentals cache files
                    fundamentals_files = list(cache_dir.glob("fundamentals*"))
                    for file in fundamentals_files:
                        file.unlink()
                    results["fundamentals"] = {"success": True, "message": f"Removed {len(fundamentals_files)} fundamentals cache files"}
                except Exception as e:
                    results["fundamentals"] = {"success": False, "message": f"Failed to clear fundamentals cache: {e}"}

        elif cache_type == "exchange_rate_cache":
            try:
                if self.currency_handler:
                    self.currency_handler.clear_exchange_rate_cache()
                results["exchange_rates"] = {"success": True, "message": "Cleared exchange rate cache"}
            except Exception as e:
                results["exchange_rates"] = {"success": False, "message": f"Failed to clear exchange rate cache: {e}"}

        return results

    def update_all_caches(self) -> Dict[str, Any]:
        """Update all cache types with fresh data.

        Returns:
            Dictionary with results of cache update operations
        """
        results = {}

        # Ensure components are initialized
        if not (self.price_cache and self.data_fetcher and self.currency_handler):
            try:
                logger.info("Initializing cache components for update...")
                self.initialize_components()
            except Exception as e:
                results["initialization"] = {"success": False, "message": f"Failed to initialize components: {e}"}
                return results

        # Update price cache by clearing it (forces fresh data on next access)
        try:
            if self.price_cache:
                self.price_cache.invalidate_all()
                results["price_cache"] = {"success": True, "message": "Price cache cleared - will fetch fresh data"}
            else:
                results["price_cache"] = {"success": False, "message": "Price cache not available"}
        except Exception as e:
            results["price_cache"] = {"success": False, "message": f"Failed to update price cache: {e}"}

        # Update exchange rates by clearing the cache
        try:
            if self.currency_handler:
                self.currency_handler.clear_exchange_rate_cache()
                results["exchange_rates"] = {"success": True, "message": "Exchange rate cache cleared - will fetch fresh rates"}
            else:
                results["exchange_rates"] = {"success": False, "message": "Currency handler not available"}
        except Exception as e:
            results["exchange_rates"] = {"success": False, "message": f"Failed to update exchange rates: {e}"}

        # Clear file-based caches to force fresh data
        try:
            cache_dirs = self.get_cache_directories()
            for cache_name, cache_dir in cache_dirs.items():
                if cache_dir.exists():
                    # Clear specific cache files that should be refreshed
                    cache_files = list(cache_dir.glob("*.pkl")) + list(cache_dir.glob("*.json")) + list(cache_dir.glob("*.csv"))
                    if cache_files:
                        for cache_file in cache_files:
                            try:
                                cache_file.unlink()
                            except Exception:
                                pass  # Ignore individual file errors
                        results[f"file_cache_{cache_name}"] = {"success": True, "message": f"Cleared {len(cache_files)} cache files in {cache_name}"}
                    else:
                        results[f"file_cache_{cache_name}"] = {"success": True, "message": f"No cache files to clear in {cache_name}"}
        except Exception as e:
            results["file_caches"] = {"success": False, "message": f"Failed to clear file caches: {e}"}

        return results

    def initialize_components(self) -> bool:
        """Initialize cache manager components.

        Returns:
            True if initialization successful
        """
        try:
            # Initialize price cache
            self.price_cache = PriceCache(settings=self.settings)

            # Initialize data fetcher with cache
            self.data_fetcher = MarketDataFetcher(cache_instance=self.price_cache)

            # Initialize currency handler
            data_dir = self.settings.get_data_directory()
            self.currency_handler = CurrencyHandler(data_dir)

            return True
        except Exception as e:
            logger.warning(f"Failed to initialize cache components: {e}")
            return False

    def _format_size(self, size_bytes: int) -> str:
        """Format size in bytes to human-readable format.

        Args:
            size_bytes: Size in bytes

        Returns:
            Formatted size string
        """
        if size_bytes == 0:
            return "0 B"

        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024.0 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1

        return f"{size_bytes:.1f} {size_names[i]}"


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance.

    Returns:
        Global cache manager instance
    """
    return CacheManager()
