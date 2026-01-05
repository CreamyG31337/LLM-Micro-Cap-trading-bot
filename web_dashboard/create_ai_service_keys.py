#!/usr/bin/env python3
"""
Create AI Service Keys File
============================

Utility to create the obfuscated keys file for AI service URLs.
Uses XOR encryption with a key to prevent simple base64 decoding.

Usage:
    python web_dashboard/create_ai_service_keys.py
"""

import json
import base64
import os
from pathlib import Path


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """XOR encrypt data with key."""
    return bytes(a ^ b for a, b in zip(data, key * ((len(data) // len(key)) + 1)))


def _encode_value(value: str, key: bytes) -> str:
    """
    Encode a value using XOR + base64.
    
    Format: base64(XOR(data, key))
    """
    data_bytes = value.encode('utf-8')
    encrypted = _xor_encrypt(data_bytes, key)
    return base64.b64encode(encrypted).decode('utf-8')


def main():
    """Create the keys file with obfuscated URLs."""
    project_root = Path(__file__).parent.parent
    keys_file = project_root / "ai_service.keys.json"
    
    # Get encryption key (use environment variable or default)
    key = os.getenv("AI_SERVICE_KEY", "default_dev_key_change_in_prod_12345")
    key_bytes = key.encode('utf-8')[:32].ljust(32, b'0')
    
    # URLs to obfuscate (AI service endpoints)
    # Note: WEB_BASE_URL is the actual web interface (for cookie-based access)
    # BASE_URL is the API endpoint (requires API key, which Pro accounts don't have)
    urls = {
        "BASE_URL": "https://generativelanguage.googleapis.com",  # API endpoint (not used without API key)
        "WEB_BASE_URL": "https://gemini.google.com/app",  # Web interface URL (will be obfuscated)
        "API_V1BETA": "/v1beta/models",
        "API_V1": "/v1/models",
        "MODEL_NAME": "gemini-pro",  # Model identifier (obfuscated)
        "GENERATE_ENDPOINT": ":generateContent",
        # Model display names (obfuscated for privacy)
        "MODEL_DISPLAY_2_5_FLASH": "Gemini 2.5 Flash",
        "MODEL_DISPLAY_2_5_PRO": "Gemini 2.5 Pro",
        "MODEL_DISPLAY_3_0_PRO": "Gemini 3.0 Pro",
        "MODEL_DISPLAY_3_PRO": "Gemini 3 Pro",
    }
    
    # Create obfuscated dictionary
    obfuscated = {}
    for key_name, url in urls.items():
        obfuscated[key_name] = _encode_value(url, key_bytes)
        # Add decoded version as comment (for reference, not used by code)
        obfuscated[f"_{key_name}_DECODED"] = url
    
    # Add metadata
    obfuscated["_NOTE"] = "Obfuscated AI service URLs. Do not commit to git."
    obfuscated["_KEY_SOURCE"] = "Set AI_SERVICE_KEY environment variable for production"
    
    # Write to file
    with open(keys_file, 'w', encoding='utf-8') as f:
        json.dump(obfuscated, f, indent=2)
    
    print(f"[OK] Created keys file: {keys_file}")
    print(f"  Added {len(urls)} obfuscated URLs")
    print(f"\n[NOTE] Add to .gitignore if not already there:")
    print(f"   ai_service.keys.json")
    print(f"\n[WARNING] Set AI_SERVICE_KEY environment variable in production!")


if __name__ == "__main__":
    main()
