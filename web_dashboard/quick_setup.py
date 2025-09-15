#!/usr/bin/env python3
"""
Quick setup script for Supabase + Vercel deployment
Guides you through the entire setup process
"""

import os
import sys
import subprocess
from pathlib import Path

def print_header(title):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")

def print_step(step, description):
    """Print a step with formatting"""
    print(f"\n📋 Step {step}: {description}")
    print("-" * 40)

def check_requirements():
    """Check if all requirements are met"""
    print_header("Checking Requirements")
    
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

def setup_environment():
    """Set up Python environment"""
    print_step(1, "Setting up Python environment")
    
    # Install requirements
    print("📦 Installing Python dependencies...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False
    
    return True

def create_env_file():
    """Create .env file template"""
    print_step(2, "Creating environment file")
    
    env_file = Path(".env")
    if env_file.exists():
        print("ℹ️  .env file already exists")
        return True
    
    env_template = """# Supabase Configuration
# Get these values from your Supabase project settings
SUPABASE_URL=your_supabase_url_here
SUPABASE_ANON_KEY=your_supabase_anon_key_here

# Optional: Set to 'true' for debug logging
DEBUG=false
"""
    
    with open(env_file, "w") as f:
        f.write(env_template)
    
    print("✅ Created .env template file")
    print("   Please fill in your Supabase credentials")
    return True

def show_supabase_setup():
    """Show Supabase setup instructions"""
    print_step(3, "Supabase Database Setup")
    
    print("""
🗄️  Supabase Setup Instructions:

1. Go to https://supabase.com
2. Sign up/Login with GitHub
3. Click "New Project"
4. Enter project details:
   - Name: portfolio-dashboard
   - Database Password: (generate strong password)
   - Region: Choose closest to you
5. Wait for project to be ready (2-3 minutes)
6. Go to "SQL Editor" → "New query"
7. Copy and paste the contents of supabase_setup.sql
8. Click "Run" to execute the schema
9. Go to "Settings" → "API"
10. Copy your Project URL and anon public key
11. Update your .env file with these values

📁 Files to reference:
   - supabase_setup.sql (database schema)
   - SUPABASE_SETUP.md (detailed instructions)
""")

def show_vercel_setup():
    """Show Vercel setup instructions"""
    print_step(4, "Vercel Deployment Setup")
    
    print("""
🌐 Vercel Setup Instructions:

1. Go to https://vercel.com
2. Sign in with GitHub
3. Click "New Project"
4. Import your repository
5. Configure:
   - Framework Preset: Other
   - Root Directory: web_dashboard
6. Click "Deploy"
7. Go to "Settings" → "Environment Variables"
8. Add:
   - SUPABASE_URL: (your Supabase URL)
   - SUPABASE_ANON_KEY: (your Supabase key)
9. Redeploy your project

📁 Files to reference:
   - vercel.json (deployment config)
   - SUPABASE_SETUP.md (detailed instructions)
""")

def test_local_setup():
    """Test local setup"""
    print_step(5, "Testing Local Setup")
    
    # Check if .env file has real values
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found. Please create it first.")
        return False
    
    with open(env_file, "r") as f:
        content = f.read()
        if "your_supabase_url_here" in content:
            print("⚠️  Please update .env file with your Supabase credentials first")
            return False
    
    # Test migration
    print("🧪 Testing data migration...")
    try:
        result = subprocess.run([sys.executable, "migrate_to_supabase.py"], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("✅ Data migration test successful")
            return True
        else:
            print(f"❌ Data migration test failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Data migration test timed out")
        return False
    except Exception as e:
        print(f"❌ Data migration test failed: {e}")
        return False

def show_next_steps():
    """Show next steps"""
    print_header("Next Steps")
    
    print("""
🎯 What to do next:

1. ✅ Complete Supabase setup (Step 3)
2. ✅ Complete Vercel deployment (Step 4)
3. ✅ Test your dashboard at your Vercel URL
4. 🔄 Set up data synchronization:
   
   Manual sync (after running trading bot):
   ```bash
   cd web_dashboard
   python sync_to_supabase.py
   ```
   
   Automated sync (GitHub Actions):
   - See SUPABASE_SETUP.md for details

5. 🎉 Share your dashboard URL with friends!

📚 Documentation:
   - SUPABASE_SETUP.md - Detailed setup instructions
   - TODO.md - Project status and tasks
   - DEPLOYMENT_GUIDE.md - Alternative deployment options

🔧 Troubleshooting:
   - Check logs in Vercel dashboard
   - Verify Supabase connection
   - Test locally with: python app.py
""")

def main():
    """Main setup function"""
    print_header("Portfolio Dashboard Quick Setup")
    print("Setting up Supabase + Vercel deployment for your trading bot dashboard")
    
    # Check requirements
    if not check_requirements():
        print("\n❌ Requirements not met. Please fix the issues and try again.")
        return False
    
    # Setup steps
    steps = [
        ("Setting up Python environment", setup_environment),
        ("Creating environment file", create_env_file),
        ("Supabase setup instructions", show_supabase_setup),
        ("Vercel setup instructions", show_vercel_setup),
        ("Testing local setup", test_local_setup),
        ("Next steps", show_next_steps)
    ]
    
    for i, (description, func) in enumerate(steps, 1):
        print(f"\n{'='*60}")
        print(f"Step {i}/{len(steps)}: {description}")
        print(f"{'='*60}")
        
        if not func():
            print(f"\n❌ Step {i} failed. Please fix the issue and try again.")
            return False
    
    print_header("Setup Complete!")
    print("🎉 Your portfolio dashboard is ready for deployment!")
    print("   Follow the instructions above to complete the setup.")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
