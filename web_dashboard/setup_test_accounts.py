#!/usr/bin/env python3
"""
Setup Test Accounts for Web Dashboard
Creates admin and guest test accounts with secure credentials
"""

import os
import sys
import json
import secrets
import string
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

try:
    from supabase import create_client
    from admin_utils import get_admin_supabase_client
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the web_dashboard directory and dependencies are installed")
    sys.exit(1)


def generate_secure_password(length: int = 16) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def create_test_user(email: str, password: str, full_name: str, is_admin_user: bool = False) -> dict:
    """Create a test user account using Supabase Admin API"""
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not service_key:
        raise ValueError("SUPABASE_URL and SUPABASE_SECRET_KEY must be set")
    
    # Use service role client for admin operations
    supabase = create_client(supabase_url, service_key)
    
    try:
        # Create user using admin API (bypasses email confirmation)
        response = supabase.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True,  # Auto-confirm email
            "user_metadata": {
                "full_name": full_name
            }
        })
        
        if not response.user:
            raise Exception("User creation failed - no user returned")
        
        user_id = response.user.id
        
        # Create user profile with role
        client = get_admin_supabase_client()
        if not client:
            raise Exception("Failed to get admin Supabase client")
        
        # Insert user profile
        profile_data = {
            "user_id": user_id,
            "email": email,
            "full_name": full_name,
            "role": "admin" if is_admin_user else "user"
        }
        
        profile_result = client.supabase.table("user_profiles").upsert(
            profile_data,
            on_conflict="user_id"
        ).execute()
        
        if not profile_result.data:
            raise Exception("Failed to create user profile")
        
        return {
            "user_id": user_id,
            "email": email,
            "password": password,
            "role": "admin" if is_admin_user else "user",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise Exception(f"Failed to create user {email}: {e}")


def assign_funds_to_user(user_id: str, fund_names: list, client) -> int:
    """Assign funds to a user"""
    assigned_count = 0
    
    for fund_name in fund_names:
        try:
            result = client.supabase.table("user_funds").upsert({
                "user_id": user_id,
                "fund_name": fund_name
            }, on_conflict="user_id,fund_name").execute()
            
            if result.data:
                assigned_count += 1
        except Exception as e:
            print(f"  ⚠️  Warning: Could not assign fund {fund_name}: {e}")
    
    return assigned_count


def get_available_funds(client) -> list:
    """Get list of available funds from portfolio_positions"""
    try:
        result = client.supabase.table("portfolio_positions").select("fund").execute()
        if result.data:
            funds = list(set([row['fund'] for row in result.data if row.get('fund')]))
            return sorted(funds)
        return []
    except Exception as e:
        print(f"⚠️  Warning: Could not fetch funds: {e}")
        return []


def main():
    """Main function to create test accounts"""
    print("=" * 60)
    print("🧪 Test Accounts Setup")
    print("=" * 60)
    
    # Check admin access
    client = get_admin_supabase_client()
    if not client:
        print("❌ Error: Failed to get admin Supabase client")
        print("Make sure SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY is set in .env")
        return False
    
    # Get available funds
    print("\n📋 Fetching available funds...")
    available_funds = get_available_funds(client)
    if not available_funds:
        print("⚠️  Warning: No funds found in database")
        print("   Test accounts will be created but no funds will be assigned")
        available_funds = []
    else:
        print(f"✅ Found {len(available_funds)} funds: {', '.join(available_funds)}")
    
    # Create admin test account
    print("\n👑 Creating Admin Test Account...")
    admin_email = "admin.test@tradingbot.local"
    admin_password = generate_secure_password(20)
    
    try:
        admin_user = create_test_user(
            email=admin_email,
            password=admin_password,
            full_name="Admin Test User",
            is_admin_user=True
        )
        print(f"✅ Admin account created: {admin_user['user_id']}")
        
        # Assign all funds to admin
        if available_funds:
            print(f"💰 Assigning {len(available_funds)} funds to admin...")
            assigned = assign_funds_to_user(admin_user['user_id'], available_funds, client)
            print(f"✅ Assigned {assigned}/{len(available_funds)} funds")
        
    except Exception as e:
        print(f"❌ Failed to create admin account: {e}")
        return False
    
    # Create guest test account
    print("\n👤 Creating Guest Test Account...")
    guest_email = "guest.test@tradingbot.local"
    guest_password = generate_secure_password(20)
    
    try:
        guest_user = create_test_user(
            email=guest_email,
            password=guest_password,
            full_name="Guest Test User",
            is_admin_user=False
        )
        print(f"✅ Guest account created: {guest_user['user_id']}")
        
        # Assign first fund to guest (if available)
        if available_funds:
            print(f"💰 Assigning first fund to guest...")
            assigned = assign_funds_to_user(guest_user['user_id'], [available_funds[0]], client)
            print(f"✅ Assigned {assigned} fund(s)")
        
    except Exception as e:
        print(f"❌ Failed to create guest account: {e}")
        return False
    
    # Save credentials to file
    credentials = {
        "admin": {
            "email": admin_email,
            "password": admin_password,
            "role": "admin",
            "created_at": admin_user['created_at']
        },
        "guest": {
            "email": guest_email,
            "password": guest_password,
            "role": "user",
            "created_at": guest_user['created_at']
        }
    }
    
    credentials_file = Path(__file__).parent / "test_credentials.json"
    try:
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        print(f"\n✅ Credentials saved to: {credentials_file}")
    except Exception as e:
        print(f"⚠️  Warning: Could not save credentials file: {e}")
        print("\n📋 Credentials (save these manually):")
        print(json.dumps(credentials, indent=2))
        return False
    
    print("\n" + "=" * 60)
    print("✅ Test Accounts Setup Complete!")
    print("=" * 60)
    print(f"\n📁 Credentials saved to: {credentials_file}")
    print("📖 See TEST_CREDENTIALS.md for usage instructions")
    print("📖 See AGENTS.md for AI agent access information")
    print("\n⚠️  Note: test_credentials.json is gitignored for security")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

