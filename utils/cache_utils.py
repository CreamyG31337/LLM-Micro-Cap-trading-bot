"""Cache clearing utilities for trade entry operations.

This module provides helper functions for clearing caches related to trade entry,
ensuring fresh data is used after trades are added or modified.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def clear_trade_related_caches(data_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Clear all caches related to trade entry operations.
    
    This function clears:
    - Price cache (market data)
    - Exchange rate cache (currency conversions)
    - Streamlit cache (if in Streamlit context)
    
    Args:
        data_dir: Optional data directory path for currency handler initialization
        
    Returns:
        Dictionary with results of each cache clearing operation:
        {
            "price_cache": {"success": bool, "message": str},
            "exchange_rate_cache": {"success": bool, "message": str},
            "streamlit_cache": {"success": bool, "message": str}
        }
    """
    results = {
        "price_cache": {"success": False, "message": "Not attempted"},
        "exchange_rate_cache": {"success": False, "message": "Not attempted"},
        "streamlit_cache": {"success": False, "message": "Not attempted"}
    }
    
    # Clear price cache
    try:
        from market_data.price_cache import PriceCache
        price_cache = PriceCache()
        price_cache.invalidate_all()
        results["price_cache"] = {"success": True, "message": "Price cache cleared"}
        logger.info("Cleared price cache after trade entry")
    except Exception as e:
        results["price_cache"] = {"success": False, "message": f"Failed to clear price cache: {e}"}
        logger.warning(f"Failed to clear price cache: {e}")
    
    # Clear exchange rate cache
    try:
        from financial.currency_handler import CurrencyHandler
        if data_dir:
            currency_handler = CurrencyHandler(data_dir=data_dir)
        else:
            currency_handler = CurrencyHandler()
        currency_handler.clear_exchange_rate_cache()
        results["exchange_rate_cache"] = {"success": True, "message": "Exchange rate cache cleared"}
        logger.info("Cleared exchange rate cache after trade entry")
    except Exception as e:
        results["exchange_rate_cache"] = {"success": False, "message": f"Failed to clear exchange rate cache: {e}"}
        logger.warning(f"Failed to clear exchange rate cache: {e}")
    
    # Clear Streamlit cache (if in Streamlit context)
    try:
        import streamlit as st
        st.cache_data.clear()
        results["streamlit_cache"] = {"success": True, "message": "Streamlit cache cleared"}
        logger.info("Cleared Streamlit cache after trade entry")
    except ImportError:
        # Not in Streamlit context, that's fine
        results["streamlit_cache"] = {"success": True, "message": "Not in Streamlit context (skipped)"}
    except Exception as e:
        results["streamlit_cache"] = {"success": False, "message": f"Failed to clear Streamlit cache: {e}"}
        logger.warning(f"Failed to clear Streamlit cache: {e}")
    
    return results

