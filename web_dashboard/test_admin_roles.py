#!/usr/bin/env python3
"""
Test script for admin role management functions
Tests grant_admin_role and revoke_admin_role SQL functions
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from streamlit_utils import get_supabase_client
from auth_utils import get_user_email

load_dotenv()

def test_admin_role_functions():
    """Test admin role management functions"""
    print("Testing Admin Role Management Functions\n")
    print("=" * 60)
    
    client = get_supabase_client()
    if not client:
        print("❌ Failed to get Supabase client")
        return False
    
    # First, list all users with their current roles
    print("\n1. Listing all users and their roles:")
    print("-" * 60)
    try:
        users_result = client.supabase.rpc('list_users_with_funds').execute()
        users = users_result.data if users_result.data else []
        
        if not users:
            print("❌ No users found")
            return False
        
        print(f"Found {len(users)} users:\n")
        for user in users:
            email = user.get('email', 'N/A')
            role = user.get('role', 'user')
            funds = user.get('funds', [])
            role_icon = "🔑" if role == 'admin' else "👤"
            print(f"  {role_icon} {email:40} | Role: {role:10} | Funds: {', '.join(funds) if funds else 'None'}")
        
        # Select a test user (first non-admin user)
        test_user = None
        admin_user = None
        
        for user in users:
            if user.get('role') == 'admin':
                admin_user = user
            elif user.get('role') != 'admin' and not test_user:
                test_user = user
        
        if not test_user:
            print("\n⚠️ Warning: No non-admin users found to test with")
            print("   Creating a test would require a non-admin user in the system")
            return True  # Not a failure, just can't test
        
        if not admin_user:
            print("\n❌ No admin users found - cannot proceed with tests")
            return False
        
        test_email = test_user.get('email')
        print(f"\n✓ Test user selected: {test_email}")
        
    except Exception as e:
        print(f"❌ Error listing users: {e}")
        return False
    
    # Test 1: Grant admin role
    print(f"\n2. Testing grant_admin_role for {test_email}:")
    print("-" * 60)
    try:
        result = client.supabase.rpc(
            'grant_admin_role',
            {'user_email': test_email}
        ).execute()
        
        result_data = result.data
        if isinstance(result_data, list) and len(result_data) > 0:
            result_data = result_data[0]
        
        if result_data and result_data.get('success'):
            print(f"✅ {result_data.get('message')}")
        else:
            print(f"❌ {result_data.get('message')}")
            return False
    except Exception as e:
        print(f"❌ Error granting admin role: {e}")
        return False
    
    # Verify the role was changed
    print(f"\n3. Verifying role change:")
    print("-" * 60)
    try:
        users_result = client.supabase.rpc('list_users_with_funds').execute()
        users = users_result.data if users_result.data else []
        
        updated_user = next((u for u in users if u.get('email') == test_email), None)
        if updated_user and updated_user.get('role') == 'admin':
            print(f"✅ Successfully verified: {test_email} is now an admin")
        else:
            print(f"❌ Role verification failed")
            return False
    except Exception as e:
        print(f"❌ Error verifying role: {e}")
        return False
    
    # Test 2: Try granting admin again (should fail with already_admin)
    print(f"\n4. Testing duplicate grant (should fail gracefully):")
    print("-" * 60)
    try:
        result = client.supabase.rpc(
            'grant_admin_role',
            {'user_email': test_email}
        ).execute()
        
        result_data = result.data
        if isinstance(result_data, list) and len(result_data) > 0:
            result_data = result_data[0]
        
        if result_data and result_data.get('already_admin'):
            print(f"✅ Correctly rejected: {result_data.get('message')}")
        else:
            print(f"⚠️ Unexpected response: {result_data}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Revoke admin role
    print(f"\n5. Testing revoke_admin_role for {test_email}:")
    print("-" * 60)
    try:
        result = client.supabase.rpc(
            'revoke_admin_role',
            {'user_email': test_email}
        ).execute()
        
        result_data = result.data
        if isinstance(result_data, list) and len(result_data) > 0:
            result_data = result_data[0]
        
        if result_data and result_data.get('success'):
            print(f"✅ {result_data.get('message')}")
        else:
            print(f"❌ {result_data.get('message')}")
            return False
    except Exception as e:
        print(f"❌ Error revoking admin role: {e}")
        return False
    
    # Verify the role was changed back
    print(f"\n6. Verifying role revocation:")
    print("-" * 60)
    try:
        users_result = client.supabase.rpc('list_users_with_funds').execute()
        users = users_result.data if users_result.data else []
        
        reverted_user = next((u for u in users if u.get('email') == test_email), None)
        if reverted_user and reverted_user.get('role') == 'user':
            print(f"✅ Successfully verified: {test_email} is back to regular user")
        else:
            print(f"❌ Role revocation verification failed")
            return False
    except Exception as e:
        print(f"❌ Error verifying revocation: {e}")
        return False
    
    # Test 4: Try to revoke the last admin (should fail)
    print(f"\n7. Testing last admin protection:")
    print("-" * 60)
    
    # Count admins
    admin_count = sum(1 for u in users if u.get('role') == 'admin')
    print(f"   Current admin count: {admin_count}")
    
    if admin_count == 1 and admin_user:
        admin_email = admin_user.get('email')
        print(f"   Attempting to revoke last admin: {admin_email}")
        try:
            result = client.supabase.rpc(
                'revoke_admin_role',
                {'user_email': admin_email}
            ).execute()
            
            result_data = result.data
            if isinstance(result_data, list) and len(result_data) > 0:
                result_data = result_data[0]
            
            if result_data and not result_data.get('success'):
                print(f"✅ Correctly protected: {result_data.get('message')}")
            else:
                print(f"❌ SECURITY ISSUE: Should not allow removing last admin!")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
    else:
        print(f"   ℹ️ Skipping test (multiple admins exist)")
    
    print("\n" + "=" * 60)
    print("✅ All tests passed successfully!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_admin_role_functions()
    sys.exit(0 if success else 1)
