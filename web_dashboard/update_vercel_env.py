#!/usr/bin/env python3
"""
Update Vercel environment variables with new Supabase keys
"""

import subprocess
import sys

def update_vercel_env():
    """Update Vercel environment variables"""
    print("Updating Vercel environment variables...")
    
    # New API keys
    anon_key = "SUPABASE_PUBLISHABLE_KEY_REDACTED"
    service_key = "SUPABASE_SECRET_KEY_REDACTED"
    
    # Update SUPABASE_ANON_KEY
    print("Updating SUPABASE_ANON_KEY...")
    try:
        result = subprocess.run([
            "vercel", "env", "add", "SUPABASE_ANON_KEY", 
            "--value", anon_key, "--yes"
        ], capture_output=True, text=True)
        print(f"  Status: {result.returncode}")
        if result.returncode == 0:
            print("  Anon key updated successfully!")
        else:
            print(f"  Error: {result.stderr}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    # Update SUPABASE_SERVICE_ROLE_KEY
    print("Updating SUPABASE_SERVICE_ROLE_KEY...")
    try:
        result = subprocess.run([
            "vercel", "env", "add", "SUPABASE_SERVICE_ROLE_KEY", 
            "--value", service_key, "--yes"
        ], capture_output=True, text=True)
        print(f"  Status: {result.returncode}")
        if result.returncode == 0:
            print("  Service key updated successfully!")
        else:
            print(f"  Error: {result.stderr}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    print("\nEnvironment variables updated!")
    print("Next step: Redeploy the application")

if __name__ == "__main__":
    update_vercel_env()
