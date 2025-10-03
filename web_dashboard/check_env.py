#!/usr/bin/env python3
"""
Environment Check Script
Checks if the virtual environment is properly activated and all dependencies are available.
"""

import sys
import os
from pathlib import Path

def check_venv():
    """Check if virtual environment is activated"""
    venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if venv_active:
        print("✅ Virtual environment is ACTIVE")
        print(f"   Python executable: {sys.executable}")
        return True
    else:
        print("❌ Virtual environment is NOT active")
        print("🔔 SOLUTION: Activate it first!")
        print("   PowerShell: & '..\\venv\\Scripts\\Activate.ps1'")
        print("   You should see (venv) in your prompt when activated.")
        return False

def check_dependencies():
    """Check if required dependencies are available"""
    dependencies = {
        'flask': 'Flask web framework',
        'pandas': 'Data processing',
        'supabase': 'Database client',
        'dotenv': 'Environment variables'
    }
    
    print("\n=== Dependency Check ===")
    all_good = True
    
    for dep, desc in dependencies.items():
        try:
            __import__(dep)
            print(f"✅ {dep} - {desc}")
        except ImportError:
            print(f"❌ {dep} - {desc} (MISSING)")
            all_good = False
    
    return all_good

def check_env_file():
    """Check if .env file exists"""
    env_file = Path('.env')
    if env_file.exists():
        print("\n✅ .env file found")
        return True
    else:
        print("\n❌ .env file not found")
        print("   Expected location: web_dashboard/.env")
        return False

def main():
    print("=== Web Dashboard Environment Check ===")
    
    # Check virtual environment
    venv_ok = check_venv()
    
    if not venv_ok:
        print("\n🔔 FIRST: Activate the virtual environment, then run this check again.")
        return
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Check .env file
    env_ok = check_env_file()
    
    print("\n=== Summary ===")
    if venv_ok and deps_ok and env_ok:
        print("🎉 ALL CHECKS PASSED!")
        print("\nReady to run:")
        print("   python app.py        # Start web dashboard")
        print("   python test_supabase.py  # Run tests")
    else:
        print("❌ Some issues found. Please fix them first.")
        if not venv_ok:
            print("   1. Activate virtual environment")
        if not deps_ok:
            print("   2. Ensure venv is activated (dependencies are in venv)")
        if not env_ok:
            print("   3. Check .env file location")

if __name__ == "__main__":
    main()