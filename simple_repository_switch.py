#!/usr/bin/env python3
"""
Simple Repository Switch Utility
Switch between CSV and Supabase repositories without emojis
"""

import os
import sys
import json
from pathlib import Path

def create_config_file(repo_type: str, **kwargs):
    """Create a configuration file for the specified repository type."""
    
    if repo_type == "csv":
        config = {
            "repository": {
                "type": "csv",
                "data_directory": kwargs.get("data_directory", "trading_data/funds/Project Chimera")
            }
        }
    elif repo_type == "supabase":
        config = {
            "repository": {
                "type": "supabase",
                "supabase": {
                    "url": kwargs.get("supabase_url", os.getenv("SUPABASE_URL")),
                    "key": kwargs.get("supabase_key", os.getenv("SUPABASE_ANON_KEY")),
                    "fund": kwargs.get("fund", "Project Chimera")
                }
            }
        }
    else:
        raise ValueError(f"Unsupported repository type: {repo_type}")
    
    return config

def switch_to_csv(data_directory: str = None):
    """Switch to CSV repository."""
    print("Switching to CSV repository...")
    
    if not data_directory:
        data_directory = "trading_data/funds/Project Chimera"
    
    config = create_config_file("csv", data_directory=data_directory)
    
    # Save configuration
    config_file = Path("repository_config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"OK: Switched to CSV repository")
    print(f"   Data directory: {data_directory}")
    print(f"   Config saved to: {config_file}")
    
    return config

def switch_to_supabase(supabase_url: str = None, supabase_key: str = None, fund: str = None):
    """Switch to Supabase repository."""
    print("Switching to Supabase repository...")
    
    if not supabase_url:
        supabase_url = os.getenv("SUPABASE_URL")
    if not supabase_key:
        supabase_key = os.getenv("SUPABASE_ANON_KEY")
    
    if not supabase_url or not supabase_key:
        print("ERROR: Supabase URL and key must be provided")
        print("   Set SUPABASE_URL and SUPABASE_ANON_KEY environment variables")
        return None
    
    if not fund:
        fund = "Project Chimera"
    
    config = create_config_file("supabase", 
                               supabase_url=supabase_url, 
                               supabase_key=supabase_key, 
                               fund=fund)
    
    # Save configuration
    config_file = Path("repository_config.json")
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"OK: Switched to Supabase repository")
    print(f"   Supabase URL: {supabase_url}")
    print(f"   Fund: {fund}")
    print(f"   Config saved to: {config_file}")
    
    return config

def test_repository():
    """Test the current repository configuration."""
    print("Testing repository configuration...")
    
    try:
        from data.repositories.repository_factory import RepositoryFactory
        
        # Load configuration
        config_file = Path("repository_config.json")
        if not config_file.exists():
            print("ERROR: No repository configuration found")
            print("   Run: python simple_repository_switch.py csv")
            print("   Or: python simple_repository_switch.py supabase")
            return False
        
        with open(config_file, "r") as f:
            config = json.load(f)
        
        repo_type = config["repository"]["type"]
        repo_config = {k: v for k, v in config["repository"].items() if k != "type"}
        
        print(f"   Repository type: {repo_type}")
        print(f"   Configuration: {repo_config}")
        
        # Create repository instance
        repository = RepositoryFactory.create_repository(repo_type, **repo_config)
        print(f"OK: Repository created successfully: {type(repository).__name__}")
        
        # Test basic operations
        if repo_type == "csv":
            # Test CSV operations
            print("   Testing CSV operations...")
            # Add CSV-specific tests here
            
        elif repo_type == "supabase":
            # Test Supabase operations
            print("   Testing Supabase connection...")
            try:
                # Test basic connection
                result = repository.supabase.table("portfolio_positions").select("id").limit(1).execute()
                print(f"   OK: Supabase connection successful")
            except Exception as e:
                print(f"   ERROR: Supabase connection failed: {e}")
                return False
        
        print("OK: Repository test passed")
        return True
        
    except Exception as e:
        print(f"ERROR: Repository test failed: {e}")
        return False

def show_status():
    """Show current repository status."""
    print("Repository Status")
    print("=" * 40)
    
    config_file = Path("repository_config.json")
    if not config_file.exists():
        print("ERROR: No repository configuration found")
        print("   Run: python simple_repository_switch.py csv")
        print("   Or: python simple_repository_switch.py supabase")
        return
    
    with open(config_file, "r") as f:
        config = json.load(f)
    
    repo_type = config["repository"]["type"]
    repo_config = config["repository"][repo_type]
    
    print(f"Current repository: {repo_type}")
    print(f"Configuration: {json.dumps(repo_config, indent=2)}")
    
    # Test connection
    if test_repository():
        print("OK: Repository is working")
    else:
        print("ERROR: Repository has issues")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Repository Switch Utility")
        print("=" * 30)
        print("Usage:")
        print("  python simple_repository_switch.py csv [data_directory]")
        print("  python simple_repository_switch.py supabase [url] [key] [fund]")
        print("  python simple_repository_switch.py test")
        print("  python simple_repository_switch.py status")
        print("")
        print("Examples:")
        print("  python simple_repository_switch.py csv")
        print("  python simple_repository_switch.py csv 'trading_data/funds/TEST'")
        print("  python simple_repository_switch.py supabase")
        print("  python simple_repository_switch.py test")
        return
    
    command = sys.argv[1].lower()
    
    if command == "csv":
        data_directory = sys.argv[2] if len(sys.argv) > 2 else None
        switch_to_csv(data_directory)
        
    elif command == "supabase":
        supabase_url = sys.argv[2] if len(sys.argv) > 2 else None
        supabase_key = sys.argv[3] if len(sys.argv) > 3 else None
        fund = sys.argv[4] if len(sys.argv) > 4 else None
        switch_to_supabase(supabase_url, supabase_key, fund)
        
    elif command == "test":
        test_repository()
        
    elif command == "status":
        show_status()
        
    else:
        print(f"Unknown command: {command}")
        print("Use: csv, supabase, test, or status")

if __name__ == "__main__":
    main()
