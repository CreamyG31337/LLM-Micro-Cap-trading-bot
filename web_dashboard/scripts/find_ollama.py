#!/usr/bin/env python3
"""Find where Ollama is running by testing common URLs."""

import requests
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Common Ollama URLs to test
TEST_URLS = [
    ("http://localhost:11434", "localhost (local installation)"),
    ("http://127.0.0.1:11434", "127.0.0.1 (local IP)"),
    ("http://host.docker.internal:11434", "host.docker.internal (Docker to host)"),
    ("http://ollama:11434", "ollama (Docker container name)"),
]

def test_ollama_url(url: str, description: str) -> tuple[bool, str]:
    """Test if Ollama is accessible at the given URL.
    
    Returns:
        (is_accessible, message)
    """
    try:
        response = requests.get(f"{url}/api/tags", timeout=3)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            model_names = [m.get("name", "") for m in models if m.get("name")]
            return True, f"Found {len(model_names)} models: {', '.join(model_names[:3])}"
        else:
            return False, f"HTTP {response.status_code}"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except requests.exceptions.Timeout:
        return False, "Connection timeout"
    except Exception as e:
        return False, str(e)


def main():
    """Test all common Ollama URLs."""
    print("=" * 70)
    print("Finding Ollama Installation")
    print("=" * 70)
    print("\nTesting common Ollama URLs...\n")
    
    found = []
    not_found = []
    
    for url, description in TEST_URLS:
        print(f"Testing: {url}")
        print(f"  ({description})")
        is_ok, message = test_ollama_url(url, description)
        
        if is_ok:
            print(f"  [OK] Ollama is accessible!")
            print(f"  {message}")
            found.append((url, description, message))
        else:
            print(f"  [FAIL] {message}")
            not_found.append((url, description, message))
        
        print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    
    if found:
        print(f"\n[SUCCESS] Found Ollama at {len(found)} location(s):\n")
        for url, description, message in found:
            print(f"  ✅ {url}")
            print(f"     {description}")
            print(f"     {message}\n")
        
        # Recommend the first one found
        recommended_url, recommended_desc, _ = found[0]
        print(f"\nRecommended: {recommended_url}")
        print(f"\nTo use this, add to your web_dashboard/.env file:")
        print(f"OLLAMA_BASE_URL={recommended_url}")
    else:
        print("\n[FAIL] Ollama not found at any tested location.\n")
        print("Possible reasons:")
        print("  1. Ollama is not running")
        print("  2. Ollama is running on a different port")
        print("  3. Ollama is on a remote server (need to configure URL)")
        print("  4. Firewall is blocking the connection")
        print("\nTo start Ollama:")
        print("  - Local: Download from https://ollama.ai and run 'ollama serve'")
        print("  - Docker: docker run -d -p 11434:11434 ollama/ollama")
    
    print("=" * 70)
    
    return 0 if found else 1


if __name__ == "__main__":
    sys.exit(main())

