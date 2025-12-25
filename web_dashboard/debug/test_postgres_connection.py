#!/usr/bin/env python3
"""
Test Postgres Connection from Different Contexts

This script helps you determine which DATABASE_URL works from your current environment.
It tries multiple common hostname patterns to help you find the right one.

SECURITY NOTE: This script should ONLY be run from the server/command line.
It is NOT accessible via web interface and should never be exposed as a web endpoint.
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv("web_dashboard/.env")

try:
    import psycopg2
    from psycopg2 import OperationalError
except ImportError:
    print("ERROR: psycopg2 not installed. Install with: pip install psycopg2-binary")
    sys.exit(1)


def test_connection(url: str, description: str) -> bool:
    """Test a connection URL"""
    print(f"\nTesting: {description}")
    # Mask password in display
    parsed = urlparse(url)
    safe_url = urlunparse((
        parsed.scheme,
        f"{parsed.username}:***@{parsed.hostname}:{parsed.port or 5432}",
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))
    print(f"   URL: {safe_url}")
    
    try:
        conn = psycopg2.connect(url, connect_timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT version(), current_database(), current_user")
        result = cursor.fetchone()
        conn.close()
        
        print(f"   SUCCESS!")
        print(f"   Version: {result[0].split(',')[0]}")
        print(f"   Database: {result[1]}")
        print(f"   User: {result[2]}")
        return True
    except OperationalError as e:
        print(f"   FAILED: {e}")
        return False
    except Exception as e:
        print(f"   ERROR: {e}")
        return False


def main():
    """Test different connection patterns"""
    # Set UTF-8 encoding for Windows console
    import sys
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("=" * 70)
    print("Postgres Connection Tester")
    print("=" * 70)
    print("\nThis script tests different hostname patterns to find which works")
    print("from your current environment.\n")
    
    # Get base connection info from DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set in environment")
        print("   Set it in web_dashboard/.env first")
        return 1
    
    # Parse the URL
    parsed = urlparse(database_url)
    username = parsed.username or "postgres"
    password = parsed.password or ""
    database = parsed.path.lstrip('/') or "trading_db"
    port = parsed.port or 5432
    
    # Build base URL parts
    auth = f"{username}:{password}@" if password else f"{username}@"
    
    # Test different hostnames
    hostnames_to_test = [
        ("localhost", "localhost (server host)"),
        ("127.0.0.1", "127.0.0.1 (server host IP)"),
        ("host.docker.internal", "host.docker.internal (Docker to host)"),
        ("postgres-17.5", "postgres-17.5 (Docker container name)"),
    ]
    
    # Add the original hostname if it's not already in the list
    original_host = parsed.hostname
    if original_host and original_host not in [h[0] for h in hostnames_to_test]:
        hostnames_to_test.insert(0, (original_host, f"{original_host} (your current setting)"))
    
    print(f"Base connection info:")
    print(f"  Username: {username}")
    print(f"  Database: {database}")
    print(f"  Port: {port}")
    print(f"  Password: {'***' if password else '(none)'}")
    
    results = []
    for hostname, description in hostnames_to_test:
        url = f"postgresql://{auth}{hostname}:{port}/{database}"
        success = test_connection(url, description)
        results.append((hostname, description, success))
    
    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    
    successful = [r for r in results if r[2]]
    failed = [r for r in results if not r[2]]
    
    if successful:
        print("\nWorking connections:")
        for hostname, description, _ in successful:
            print(f"   - {hostname} ({description})")
        
        # Recommend the best one
        if "localhost" in [r[0] for r in successful]:
            recommended = "localhost"
            reason = "Best for server-side applications"
        elif "host.docker.internal" in [r[0] for r in successful]:
            recommended = "host.docker.internal"
            reason = "Best for Docker containers connecting to host"
        elif "postgres-17.5" in [r[0] for r in successful]:
            recommended = "postgres-17.5"
            reason = "Best for Docker-to-Docker connections"
        else:
            recommended = successful[0][0]
            reason = "First working connection"
        
        print(f"\nRecommended: {recommended}")
        print(f"   Reason: {reason}")
        print(f"\n   Update your .env with:")
        print(f"   DATABASE_URL=postgresql://{auth}{recommended}:{port}/{database}")
    else:
        print("\nNo working connections found!")
        print("\nTroubleshooting:")
        print("   1. Make sure Postgres container is running")
        print("   2. Check that port 5432 is accessible")
        print("   3. Verify database 'trading_db' exists")
        print("   4. Check firewall/network settings")
        print("   5. For Tailscale: ensure both devices are on the Tailscale network")
    
    if failed:
        print(f"\nFailed connections ({len(failed)}):")
        for hostname, description, _ in failed:
            print(f"   - {hostname} ({description})")
    
    return 0 if successful else 1


if __name__ == "__main__":
    sys.exit(main())

