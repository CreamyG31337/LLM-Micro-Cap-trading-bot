#!/usr/bin/env python3
"""Test repository detection and configuration."""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import Settings
from data.repositories.repository_factory import get_repository_container

def test_repository_detection():
    """Test what repository is actually being used."""
    print("🔍 Testing Repository Detection...")
    
    # Set environment variables
    os.environ["SUPABASE_URL"] = "https://injqbxdqyxfvannygadt.supabase.co"
    os.environ["SUPABASE_ANON_KEY"] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImluanFieGRxeXhmdmFubnlnYWR0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgyNjY1MjEsImV4cCI6MjA3Mzg0MjUyMX0.gcR-dNuW8zFd9werFRhM90Z3QvRdmjyPVlmIcQo_9fo"
    
    # Test settings
    print("\n📋 Settings Configuration:")
    settings = Settings()
    repo_config = settings.get_repository_config()
    print(f"   Repository config: {repo_config}")
    
    # Test repository container
    print("\n🗄️ Repository Container:")
    container = get_repository_container()
    print(f"   Container: {container}")
    
    # Try to get repository
    try:
        repository = container.get_repository('default')
        if repository:
            repo_type = type(repository).__name__
            print(f"   Repository type: {repo_type}")
        else:
            print("   No repository found in container")
    except Exception as e:
        print(f"   Error getting repository: {e}")
    
    # Test direct repository creation
    print("\n🔧 Direct Repository Creation:")
    try:
        from data.repositories.supabase_repository import SupabaseRepository
        repo = SupabaseRepository(fund="TEST")
        print(f"   SupabaseRepository created: {type(repo).__name__}")
        
        # Test getting portfolio data
        snapshot = repo.get_latest_portfolio_snapshot()
        if snapshot:
            print(f"   Portfolio snapshot: {len(snapshot.positions)} positions")
            # Show first few tickers
            for i, pos in enumerate(snapshot.positions[:5]):
                print(f"     {pos.ticker}: {pos.company}")
        else:
            print("   No portfolio snapshot found")
    except Exception as e:
        print(f"   Error creating SupabaseRepository: {e}")

if __name__ == "__main__":
    test_repository_detection()
