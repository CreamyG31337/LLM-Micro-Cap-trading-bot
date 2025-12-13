#!/usr/bin/env python3
"""
Update Guest Test Account Password
Generates a new secure password and updates it in Supabase
"""

import os
import sys
import json
import secrets
import string
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

from supabase import create_client


def generate_secure_password(length: int = 20) -> str:
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password


def update_user_password(email: str, new_password: str) -> bool:
    """Update user password using Supabase Admin API"""
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not service_key:
        print("[ERROR] SUPABASE_URL and SUPABASE_SECRET_KEY must be set in .env")
        return False
    
    try:
        # Use service role client for admin operations
        supabase = create_client(supabase_url, service_key)
        
        # Get user by email - list_users returns a list
        users_response = supabase.auth.admin.list_users()
        user = None
        # users_response might be a list or have a .users attribute
        users_list = users_response if isinstance(users_response, list) else getattr(users_response, 'users', [])
        
        for u in users_list:
            user_email = u.email if hasattr(u, 'email') else u.get('email') if isinstance(u, dict) else None
            if user_email == email:
                user = u
                break
        
        if not user:
            print(f"[ERROR] User with email {email} not found")
            return False
        
        # Get user ID
        user_id = user.id if hasattr(user, 'id') else user.get('id') if isinstance(user, dict) else None
        if not user_id:
            print(f"[ERROR] Could not get user ID")
            return False
        
        # Update password using admin API
        update_response = supabase.auth.admin.update_user_by_id(
            user_id,
            {"password": new_password}
        )
        
        if update_response and update_response.user:
            print(f"[OK] Password updated successfully for {email}")
            return True
        else:
            print(f"[ERROR] Failed to update password")
            return False
            
    except Exception as e:
        print(f"[ERROR] Error updating password: {e}")
        return False


def main():
    """Main function to update guest password"""
    print("=" * 60)
    print("[INFO] Updating Guest Test Account Password")
    print("=" * 60)
    
    guest_email = "guest.test@tradingbot.local"
    new_password = generate_secure_password(20)
    
    print(f"\n[INFO] Generating new password...")
    print(f"[INFO] New password: {new_password}")
    
    # Update password in Supabase
    print(f"\n[INFO] Updating password in Supabase...")
    if not update_user_password(guest_email, new_password):
        print("[ERROR] Failed to update password in Supabase")
        sys.exit(1)
    
    # Update test_credentials.json
    credentials_file = Path(__file__).parent / "test_credentials.json"
    try:
        if credentials_file.exists():
            with open(credentials_file, 'r') as f:
                credentials = json.load(f)
        else:
            credentials = {}
        
        if "guest" not in credentials:
            credentials["guest"] = {}
        
        credentials["guest"]["email"] = guest_email
        credentials["guest"]["password"] = new_password
        credentials["guest"]["role"] = "user"
        
        with open(credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        
        print(f"\n[OK] Updated {credentials_file}")
        print("\n" + "=" * 60)
        print("[OK] Password update complete!")
        print("=" * 60)
        print(f"\n[INFO] New password saved to: {credentials_file}")
        print("[WARNING] Remember: test_credentials.json is gitignored for security")
        
    except Exception as e:
        print(f"[ERROR] Failed to update credentials file: {e}")
        print(f"[INFO] New password: {new_password}")
        print("[WARNING] Please manually update test_credentials.json")
        sys.exit(1)


if __name__ == "__main__":
    main()

