#!/usr/bin/env python3
"""
Quick deployment script for the portfolio dashboard
Automates the setup and deployment process
"""

import os
import sys
import subprocess
import json
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_requirements():
    """Check if all requirements are met"""
    print("🔍 Checking requirements...")
    
    # Check if we're in the right directory
    if not Path("app.py").exists():
        print("❌ Please run this script from the web_dashboard directory")
        return False
    
    # Check if trading data exists
    trading_data_dir = Path("../trading_data/prod")
    if not trading_data_dir.exists():
        print("❌ Trading data directory not found. Please ensure trading_data/prod exists")
        return False
    
    # Check for required CSV files
    required_files = ["llm_portfolio_update.csv", "llm_trade_log.csv"]
    missing_files = []
    
    for file in required_files:
        if not (trading_data_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"⚠️  Missing files: {', '.join(missing_files)}")
        print("   The dashboard will work but with limited data")
    
    print("✅ Requirements check completed")
    return True

def sync_data():
    """Sync trading data to web dashboard"""
    print("📊 Syncing trading data...")
    return run_command("python sync_data.py", "Data sync")

def test_dashboard():
    """Test the dashboard functionality"""
    print("🧪 Testing dashboard...")
    return run_command("python test_dashboard.py", "Dashboard test")

def setup_git():
    """Set up git repository if needed"""
    print("📁 Setting up git repository...")
    
    # Check if git is initialized
    if not Path(".git").exists():
        if not run_command("git init", "Git initialization"):
            return False
    
    # Add all files
    if not run_command("git add .", "Adding files to git"):
        return False
    
    # Commit changes
    if not run_command('git commit -m "Add portfolio dashboard"', "Committing changes"):
        return False
    
    print("✅ Git setup completed")
    return True

def show_deployment_options():
    """Show deployment options to the user"""
    print("\n🚀 Deployment Options:")
    print("\n1. Vercel (Recommended - Easiest)")
    print("   - Go to https://vercel.com")
    print("   - Sign in with GitHub")
    print("   - Import your repository")
    print("   - Set root directory to 'web_dashboard'")
    print("   - Deploy!")
    print("   - Cost: Free")
    
    print("\n2. Railway (Best for persistent storage)")
    print("   - Go to https://railway.app")
    print("   - Sign in with GitHub")
    print("   - Deploy from GitHub repo")
    print("   - Set root directory to 'web_dashboard'")
    print("   - Cost: $5/month free credit")
    
    print("\n3. Netlify (Static site)")
    print("   - Go to https://netlify.com")
    print("   - Connect GitHub repository")
    print("   - Set build command: 'python generate_static.py'")
    print("   - Cost: Free")
    
    print("\n4. Local Development")
    print("   - Run: python app.py")
    print("   - Visit: http://localhost:5000")

def main():
    """Main deployment function"""
    print("🚀 Portfolio Dashboard Quick Deploy\n")
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Requirements not met. Please fix the issues and try again.")
        return False
    
    # Sync data
    if not sync_data():
        print("\n❌ Data sync failed. Please check your trading data files.")
        return False
    
    # Test dashboard
    if not test_dashboard():
        print("\n❌ Dashboard test failed. Please fix the issues before deploying.")
        return False
    
    # Setup git
    if not setup_git():
        print("\n❌ Git setup failed. Please check your git configuration.")
        return False
    
    print("\n🎉 Dashboard is ready for deployment!")
    show_deployment_options()
    
    print("\n📚 For detailed instructions, see DEPLOYMENT_GUIDE.md")
    print("🔧 To run locally: python app.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
