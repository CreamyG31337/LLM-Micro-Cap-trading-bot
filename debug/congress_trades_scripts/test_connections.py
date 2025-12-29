#!/usr/bin/env python3
"""Test database and Ollama connections."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web_dashboard.postgres_client import PostgresClient
from web_dashboard.ollama_client import get_ollama_client, check_ollama_health
from dotenv import load_dotenv

load_dotenv("web_dashboard/.env")


def test_database():
    """Test database connection."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        client = PostgresClient()
        print("[OK] PostgresClient initialized")
        
        if client.test_connection():
            print("[OK] Database connection successful!")
            
            # Try a simple query
            result = client.execute_query("SELECT COUNT(*) as count FROM research_articles")
            if result:
                count = result[0]['count']
                print(f"[OK] Database query successful! Found {count} articles in research_articles table")
                return True
            else:
                print("[WARN] Database connected but query returned no results")
                return True
        else:
            print("[FAIL] Database connection test failed")
            return False
    except Exception as e:
        print(f"[FAIL] Database connection error: {e}")
        return False


def test_ollama():
    """Test Ollama connection."""
    print("\n" + "=" * 60)
    print("Testing Ollama Connection")
    print("=" * 60)
    
    try:
        # Check health
        if check_ollama_health():
            print("[OK] Ollama health check passed!")
            
            # Get client and list models
            client = get_ollama_client()
            if client:
                print(f"[OK] OllamaClient initialized (base_url: {client.base_url})")
                
                # List available models
                models = client.list_available_models()
                if models:
                    print(f"[OK] Found {len(models)} available models:")
                    for model in models[:5]:  # Show first 5
                        print(f"     - {model}")
                    if len(models) > 5:
                        print(f"     ... and {len(models) - 5} more")
                    return True
                else:
                    print("[WARN] Ollama connected but no models found")
                    print("       You may need to pull a model: ollama pull llama3.2:3b")
                    return True
            else:
                print("[FAIL] Failed to get OllamaClient")
                return False
        else:
            print("[FAIL] Ollama health check failed")
            print("\nTroubleshooting:")
            print("  1. Is Ollama running? Check: ollama serve")
            print("  2. Is Ollama accessible? Check: http://localhost:11434")
            print("  3. If Ollama is in Docker, you may need to use a different hostname")
            print("     Current base_url: host.docker.internal:11434")
            print("     Try: localhost:11434 or your Docker hostname")
            return False
    except Exception as e:
        print(f"[FAIL] Ollama connection error: {e}")
        print("\nTroubleshooting:")
        print("  1. Check if Ollama is running")
        print("  2. Check OLLAMA_BASE_URL in your .env file")
        print("  3. If Ollama is in Docker, try: localhost:11434")
        return False


def main():
    """Run all connection tests."""
    print("\nConnection Test Suite")
    print("=" * 60)
    
    db_ok = test_database()
    ollama_ok = test_ollama()
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Database:  {'[OK]' if db_ok else '[FAIL]'}")
    print(f"Ollama:    {'[OK]' if ollama_ok else '[FAIL]'}")
    
    if db_ok and ollama_ok:
        print("\n[SUCCESS] All connections working! You can run the test scripts.")
        return 0
    else:
        print("\n[WARNING] Some connections failed. Fix issues before running test scripts.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

