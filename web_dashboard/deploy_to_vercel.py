#!/usr/bin/env python3
"""
Deploy portfolio dashboard to Vercel
"""

import os
import subprocess
import sys
from pathlib import Path

def deploy_to_vercel():
    """Deploy the dashboard to Vercel"""
    print("🚀 Deploying Portfolio Dashboard to Vercel")
    print("=" * 50)

    # Check if Vercel CLI is installed
    try:
        result = subprocess.run(['vercel', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Vercel CLI not installed")
            print("Install with: npm install -g vercel")
            return False
        print(f"✅ Vercel CLI version: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ Vercel CLI not found")
        print("Install with: npm install -g vercel")
        return False

    # Check if git repository
    if not Path('.git').exists():
        print("❌ Not a git repository")
        print("Initialize git: git init")
        return False

    # Check if there are uncommitted changes
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    if result.stdout.strip():
        print("⚠️  Uncommitted changes detected")
        print("Commit changes: git add . && git commit -m 'Ready for deployment'")
        return False

    print("✅ Repository ready for deployment")

    # Deploy to Vercel
    print("\n🚀 Starting Vercel deployment...")
    try:
        # Run vercel deployment
        result = subprocess.run(['vercel', '--prod'], capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ Deployment successful!")
            print(result.stdout)

            # Extract the deployment URL from output
            lines = result.stdout.split('\n')
            for line in lines:
                if 'https://' in line and 'vercel.app' in line:
                    print(f"\n🌐 Your dashboard is live at: {line.strip()}")
                    break

            return True
        else:
            print("❌ Deployment failed")
            print("Error output:", result.stderr)
            return False

    except Exception as e:
        print(f"❌ Deployment error: {e}")
        return False

def main():
    deploy_to_vercel()

if __name__ == "__main__":
    main()
