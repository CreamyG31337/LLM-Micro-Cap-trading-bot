#!/usr/bin/env python3
"""Debug: Check Supabase connection status and configuration"""

import sys
from pathlib import Path
import os

# Add web_dashboard to path
sys.path.insert(0, str(Path(__file__).parent.parent / "web_dashboard"))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load from root .env
    load_dotenv(Path("web_dashboard/.env"))  # Also try web_dashboard/.env
except ImportError:
    pass  # dotenv not available

print("="*80)
print("Supabase Connection Diagnostic")
print("="*80)

# Check environment variables
print("\n1. Environment Variables:")
print("-" * 80)
supabase_url = os.getenv("SUPABASE_URL")
supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
supabase_publishable_key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")
supabase_service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

print(f"SUPABASE_URL: {'[OK] Set' if supabase_url else '[MISSING] Not set'}")
if supabase_url:
    print(f"  Value: {supabase_url[:50]}...")

print(f"SUPABASE_ANON_KEY: {'[OK] Set' if supabase_anon_key else '[MISSING] Not set'}")
if supabase_anon_key:
    print(f"  Value: {supabase_anon_key[:20]}...")

print(f"SUPABASE_PUBLISHABLE_KEY: {'[OK] Set' if supabase_publishable_key else '[MISSING] Not set'}")
if supabase_publishable_key:
    print(f"  Value: {supabase_publishable_key[:20]}...")

print(f"SUPABASE_SECRET_KEY: {'[OK] Set' if supabase_secret_key else '[MISSING] Not set'}")
if supabase_secret_key:
    print(f"  Value: {supabase_secret_key[:20]}...")

print(f"SUPABASE_SERVICE_ROLE_KEY: {'[OK] Set' if supabase_service_role_key else '[MISSING] Not set'}")
if supabase_service_role_key:
    print(f"  Value: {supabase_service_role_key[:20]}...")

# Try to import and test Supabase client
print("\n2. Supabase Client Test:")
print("-" * 80)

try:
    from supabase_client import SupabaseClient
    
    # Try with publishable key
    if supabase_url and (supabase_anon_key or supabase_publishable_key):
        try:
            print("Testing connection with publishable key...")
            client = SupabaseClient()
            if client.test_connection():
                print("[SUCCESS] Connection successful with publishable key!")
            else:
                print("[FAILED] Connection test failed with publishable key")
        except Exception as e:
            print(f"[ERROR] Error connecting with publishable key: {e}")
    
    # Try with service role key
    if supabase_url and (supabase_secret_key or supabase_service_role_key):
        try:
            print("\nTesting connection with service role key...")
            client = SupabaseClient(use_service_role=True)
            if client.test_connection():
                print("[SUCCESS] Connection successful with service role key!")
            else:
                print("[FAILED] Connection test failed with service role key")
        except Exception as e:
            print(f"[ERROR] Error connecting with service role key: {e}")
    
except ImportError as e:
    print(f"[ERROR] Failed to import SupabaseClient: {e}")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")

# Check repository configuration
print("\n3. Repository Configuration:")
print("-" * 80)
try:
    import json
    config_file = Path("repository_config.json")
    if config_file.exists():
        with open(config_file, 'r') as f:
            config = json.load(f)
        repo_config = config.get("repository", {})
        repo_type = repo_config.get("type", "csv")
        fund_name = repo_config.get("fund", "Unknown")
        print(f"Repository Type: {repo_type}")
        print(f"Fund Name: {fund_name}")
        
        if repo_type == "supabase-dual-write":
            print("\n[WARNING] Using 'supabase-dual-write' mode but Supabase is unavailable.")
            print("   This mode reads from Supabase, so operations will fail.")
            print("\n   Recommended actions:")
            print("   1. Fix Supabase connection (check credentials)")
            print("   2. Switch to 'dual-write' mode (reads from CSV, writes to both)")
            print("   3. Switch to 'csv' mode (CSV only)")
    else:
        print("[ERROR] repository_config.json not found")
except Exception as e:
    print(f"[ERROR] Error reading repository config: {e}")

print("\n" + "="*80)

