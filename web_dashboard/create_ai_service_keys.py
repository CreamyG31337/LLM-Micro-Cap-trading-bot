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

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Try web_dashboard/.env first, then project root .env
    project_root = Path(__file__).parent.parent
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    elif (project_root / ".env").exists():
        load_dotenv(project_root / ".env")
    else:
        load_dotenv()  # Fallback to current directory
except ImportError:
    # python-dotenv not installed, skip .env loading
    pass


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
    if key == "default_dev_key_change_in_prod_12345":
        print("\n[WARNING] Using default encryption key - this is INSECURE!")
        print("  The default key is exposed in git and provides no security.")
        print("  Set AI_SERVICE_KEY environment variable with a secure random key.")
        print("  Example: python -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    key_bytes = key.encode('utf-8')[:32].ljust(32, b'0')
    
    # URLs to obfuscate (AI service endpoints)
    # Note: All values come from environment variables to avoid hardcoding sensitive names
    # WEB_BASE_URL is the actual web interface (for cookie-based access)
    urls = {
        "WEB_BASE_URL": os.getenv("AI_SERVICE_WEB_URL", "https://webai.google.com/app"),  # Generic fallback
        "API_V1BETA": "/v1beta/models",
        "API_V1": "/v1/models",
        "MODEL_NAME": os.getenv("AI_SERVICE_MODEL_NAME", "ai-pro"),  # Generic fallback
        "GENERATE_ENDPOINT": ":generateContent",
        # Model display names (from environment variables, generic fallbacks if not set)
        "MODEL_DISPLAY_2_5_FLASH": os.getenv("MODEL_DISPLAY_2_5_FLASH", "AI Model 2.5 Flash"),
        "MODEL_DISPLAY_2_5_PRO": os.getenv("MODEL_DISPLAY_2_5_PRO", "AI Model 2.5 Pro"),
        "MODEL_DISPLAY_3_0_PRO": os.getenv("MODEL_DISPLAY_3_0_PRO", "AI Model 3.0 Pro"),
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
    if key == "default_dev_key_change_in_prod_12345":
        print(f"\n[CRITICAL] You are using the default encryption key!")
        print(f"  This key is exposed in git and provides NO security.")
        print(f"  Anyone with repo access can decode your obfuscated values.")
        print(f"  Set AI_SERVICE_KEY in .env file with a secure random key.")
    else:
        print(f"\n[OK] Using custom encryption key from AI_SERVICE_KEY environment variable")
    print(f"\n[INFO] To customize display names and URLs, set these environment variables:")
    print(f"   AI_SERVICE_WEB_URL, AI_SERVICE_MODEL_NAME")
    print(f"   MODEL_DISPLAY_2_5_FLASH, MODEL_DISPLAY_2_5_PRO, MODEL_DISPLAY_3_0_PRO")
    print(f"   See .env.example for details")


if __name__ == "__main__":
    main()
