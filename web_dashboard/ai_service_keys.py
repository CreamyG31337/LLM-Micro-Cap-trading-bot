#!/usr/bin/env python3
"""
AI Service Key Loader
=====================

Utility to load obfuscated URLs and keys for AI service integration.
Uses XOR encryption with a key to prevent simple base64 decoding.
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict


def _xor_decrypt(data: bytes, key: bytes) -> bytes:
    """XOR decrypt data with key."""
    return bytes(a ^ b for a, b in zip(data, key * ((len(data) // len(key)) + 1)))


def _load_key_file() -> Path:
    """Get the path to the keys file."""
    # Try project root first, then web_dashboard
    project_root = Path(__file__).parent.parent
    root_keys = project_root / "ai_service.keys.json"
    web_keys = Path(__file__).parent / "ai_service.keys.json"
    
    if root_keys.exists():
        return root_keys
    elif web_keys.exists():
        return web_keys
    else:
        return root_keys  # Return expected location for error message


def _get_encryption_key() -> bytes:
    """
    Get the encryption key from environment or use a default.
    In production, this should come from environment variables.
    """
    key = os.getenv("AI_SERVICE_KEY", "default_dev_key_change_in_prod_12345")
    return key.encode('utf-8')[:32].ljust(32, b'0')  # Pad to 32 bytes


def _decode_value(encoded: str, key: bytes) -> str:
    """
    Decode an obfuscated value.
    
    Format: base64(XOR(data, key))
    """
    import base64
    try:
        # Decode base64 first
        encrypted = base64.b64decode(encoded)
        # Then XOR decrypt
        decrypted = _xor_decrypt(encrypted, key)
        return decrypted.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decode value: {e}")


_KEYS_CACHE: Optional[Dict[str, str]] = None


def _load_keys() -> Dict[str, str]:
    """Load and decode all keys from the keys file."""
    global _KEYS_CACHE
    
    if _KEYS_CACHE is not None:
        return _KEYS_CACHE
    
    keys_file = _load_key_file()
    if not keys_file.exists():
        raise FileNotFoundError(
            f"AI service keys file not found: {keys_file}\n"
            "Create ai_service.keys.json with obfuscated URLs."
        )
    
    with open(keys_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    key = _get_encryption_key()
    _KEYS_CACHE = {}
    
    # Decode all non-comment keys
    for key_name, value in data.items():
        if not key_name.startswith('_') and isinstance(value, str):
            try:
                decoded = _decode_value(value, key)
                _KEYS_CACHE[key_name] = decoded
            except Exception as e:
                # If decoding fails, log warning but continue
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to decode key {key_name}: {e}")
    
    return _KEYS_CACHE


def get_service_url(key: str) -> str:
    """
    Get a service URL by key.
    
    Args:
        key: Key name from ai_service.keys.json
        
    Returns:
        Decoded URL string
        
    Raises:
        KeyError: If key not found
        FileNotFoundError: If keys file doesn't exist
    """
    keys = _load_keys()
    if key not in keys:
        raise KeyError(
            f"Key '{key}' not found in ai_service.keys.json. "
            f"Available keys: {list(keys.keys())}"
        )
    return keys[key]


def get_model_display_name(model_id: str) -> str:
    """
    Get obfuscated model display name by model identifier.
    
    Args:
        model_id: Model identifier (e.g., "gemini-2.5-flash")
        
    Returns:
        Display name for the model (obfuscated from keys file)
        
    Raises:
        KeyError: If model not found or keys file missing
    """
    keys = _load_keys()
    
    # Map model IDs to key names
    model_key_map = {
        "gemini-2.5-flash": "MODEL_DISPLAY_2_5_FLASH",
        "gemini-2.5-pro": "MODEL_DISPLAY_2_5_PRO",
        "gemini-3.0-pro": "MODEL_DISPLAY_3_0_PRO",
    }
    
    key_name = model_key_map.get(model_id)
    if not key_name:
        # Fallback to model_id if not found
        return model_id
    
    if key_name not in keys:
        # Fallback if keys file doesn't have display names yet
        return model_id
    
    return keys[key_name]


def get_model_display_name_short() -> str:
    """
    Get short obfuscated model display name.
    
    Returns:
        Short display name (obfuscated from keys file)
    """
    keys = _load_keys()
    return keys.get("MODEL_DISPLAY_3_PRO", "WebAI Pro")


def list_service_keys() -> Dict[str, str]:
    """
    List all available service keys (for debugging).
    
    Returns:
        Dictionary of all keys (decoded)
    """
    return _load_keys().copy()

