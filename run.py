#!/usr/bin/env python3
"""
Master Script for LLM Micro-Cap Trading Bot
===========================================

This script provides an easy-to-use menu interface for running all available
trading bot scripts. It automatically handles virtual environment activation
and uses sensible defaults for data directories.

Usage:
    python run.py
    
Or on Windows:
    python run.py

Features:
- Automatic virtual environment detection and activation
- Interactive menu system
- Default to 'my trading' folder for private data
- Cross-platform compatibility
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from typing import Optional, List, Tuple

# Import emoji handling
from display.console_output import _safe_emoji

# Project structure
PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / "venv"
MY_TRADING_DIR = PROJECT_ROOT / "trading_data" / "prod"
TEST_DATA_DIR = PROJECT_ROOT / "trading_data" / "dev"
SCRIPTS_DIR = PROJECT_ROOT / "Scripts and CSV Files"
START_YOUR_OWN_DIR = PROJECT_ROOT / "Start Your Own"

# Check if we're in test mode
IS_TEST_MODE = os.environ.get('TEST_DATA_MODE') == '1'
DATA_DIR = TEST_DATA_DIR if IS_TEST_MODE else MY_TRADING_DIR

# Virtual environment paths based on platform
if platform.system() == "Windows":
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
    VENV_ACTIVATE = VENV_DIR / "Scripts" / "activate.bat"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"
    VENV_ACTIVATE = VENV_DIR / "bin" / "activate"

class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_colored(text: str, color: str = Colors.ENDC) -> None:
    """Print colored text to terminal"""
    print(f"{color}{text}{Colors.ENDC}")

def check_venv() -> bool:
    """Check if virtual environment exists"""
    return VENV_DIR.exists() and VENV_PYTHON.exists()

def create_my_trading_dir() -> None:
    """Ensure 'my trading' directory exists"""
    MY_TRADING_DIR.mkdir(exist_ok=True)
    
    # Create README if it doesn't exist
    readme_path = MY_TRADING_DIR / "README.md"
    if not readme_path.exists():
        readme_content = """# My Trading - Private Data Folder

This folder contains your **private trading data** and is excluded from version control.

## What's Stored Here

- `llm_portfolio_update.csv` - Your current portfolio positions and performance
- `llm_trade_log.csv` - Complete history of all your trades
- `cash_balances.json` - Your cash balances (if using dual currency mode)
- Any other personal trading data files

## Privacy & Security

- _safe_emoji('✅') **Git Ignored**: This entire folder is in `.gitignore` so your trading data stays private
- _safe_emoji('✅') **Local Only**: These files never get committed to GitHub or shared publicly
- _safe_emoji('✅') **Default Location**: The trading scripts now use this folder by default

## Getting Started

1. **First Time Setup**: The folder is created automatically when you run the trading script
2. **Default Usage**: Simply run the master script and choose your options
3. **Your Data**: All CSV files will be saved here automatically
4. **Cash Management**: Use option 'u' from the main menu to update your cash balances

---

*This folder was automatically created by the LLM Micro-Cap Trading Bot system.*
"""
        with open(readme_path, 'w') as f:
            f.write(readme_content)

def run_with_venv(script_path: Path, args: List[str] = None) -> int:
    """Run a Python script with the virtual environment activated"""
    if args is None:
        args = []
    
    if not check_venv():
        print_colored(f"{_safe_emoji('❌')} Virtual environment not found!", Colors.RED)
        print_colored(f"Expected location: {VENV_DIR}", Colors.YELLOW)
        print_colored("Please create a virtual environment first:", Colors.YELLOW)
        print_colored("  python -m venv venv", Colors.CYAN)
        print_colored("  # Then activate and install requirements:", Colors.CYAN)
        if platform.system() == "Windows":
            print_colored("  venv\\Scripts\\activate", Colors.CYAN)
        else:
            print_colored("  source venv/bin/activate", Colors.CYAN)
        print_colored("  pip install -r requirements.txt", Colors.CYAN)
        return 1
    
    # Prepare command
    cmd = [str(VENV_PYTHON), str(script_path)] + args
    
    print_colored(f"{_safe_emoji('🚀')} Running: {' '.join(cmd)}", Colors.CYAN)
    print_colored("=" * 60, Colors.BLUE)
    
    # Run the command
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        return result.returncode
    except KeyboardInterrupt:
        print_colored(f"\n\n{_safe_emoji('⚠️')}  Script interrupted by user", Colors.YELLOW)
        return 130
    except Exception as e:
        print_colored(f"\n{_safe_emoji('❌')} Error running script: {e}", Colors.RED)
        return 1

def get_menu_options() -> List[Tuple[str, str, str, List[str]]]:
    """Get available menu options with (key, title, description, args)"""
    data_folder_name = "trading_data/dev" if IS_TEST_MODE else "trading_data/prod"
    return [
        ("1", "🔄 Main Trading Script", 
         f"Run the main portfolio management and trading script (uses '{data_folder_name}' folder)", 
         ["--data-dir", str(DATA_DIR)]),
        
        ("2", f"{_safe_emoji('🤖')} Simple Automation", 
         f"Run LLM-powered automated trading (requires OpenAI API key) (uses '{data_folder_name}' folder)", 
         ["--data-dir", str(DATA_DIR)]),
        
        ("3", "📊 Generate Performance Graph", 
         f"Create performance comparison charts from your trading data (uses '{data_folder_name}' folder)", 
         ["--data-dir", str(DATA_DIR)]),
        
        ("4", "📈 Process Portfolio (Scripts folder)", 
         "Process portfolio using the Scripts and CSV Files folder", 
         []),
        
        ("5", "📊 Generate Graph (Scripts folder)", 
         "Generate performance graph using Scripts and CSV Files folder", 
         []),
        
        ("6", "🏁 Start Your Own - Process Portfolio", 
         "Process portfolio using the Start Your Own template folder", 
         []),
        
        ("7", "📈 Start Your Own - Generate Graph", 
         "Generate performance graph using Start Your Own template folder", 
         []),
        
        ("8", "🐛 Debug Instructions", 
         "Show debug information and instructions", 
         []),
        
        ("9", "💡 Show Prompt", 
         "Display the current LLM prompt template", 
         []),
        
        ("d", "📋 Generate Daily Trading Prompt",
         f"Generate daily trading prompt with current portfolio data (uses '{data_folder_name}' folder) - runs prompt_generator.py",
         ["--data-dir", str(DATA_DIR)]),
        
        ("w", "🔬 Generate Weekly Deep Research Prompt", 
         f"Generate weekly deep research prompt for comprehensive portfolio analysis (uses '{data_folder_name}' folder)", 
         ["--data-dir", str(DATA_DIR)]),
        
        ("u", "💰 Update Cash Balances", 
         f"Manually update your CAD/USD cash balances (deposits, withdrawals, corrections) (uses '{data_folder_name}' folder)", 
         ["--data-dir", str(DATA_DIR)]),
        
        ("m", "👥 Manage Contributors", 
         f"Edit contributor names and email addresses (uses '{data_folder_name}' folder)", 
         ["--data-dir", str(DATA_DIR)]),
        
        ("e", "📧 Add Trade from Email",
         f"Parse and add trades from email notifications (uses '{data_folder_name}' folder) - runs email trade parser",
         ["--data-dir", str(DATA_DIR)]),
        
        ("c", "⚙️  Configure", 
         "Configuration options and setup", 
         []),
        
        ("q", "🚪 Quit", 
         "Exit the application", 
         [])
    ]

def show_menu() -> None:
    """Display the main menu"""
    print_colored("\n" + "=" * 80, Colors.HEADER)
    print_colored(f"{_safe_emoji('🤖')} LLM MICRO-CAP TRADING BOT - MASTER CONTROL", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 80, Colors.HEADER)
    
    options = get_menu_options()
    
    for key, title, description, _ in options:
        # Format: [key] title - description (all on one line with different colors)
        print(f"{Colors.CYAN}{Colors.BOLD}[{key}] {title} - {Colors.ENDC}{description}")
    
    print_colored("\n" + "=" * 80, Colors.HEADER)

def handle_configuration() -> None:
    """Handle configuration menu"""
    print_colored("\n⚙️  CONFIGURATION OPTIONS", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 40, Colors.HEADER)
    
    print_colored("\n[1] Check Virtual Environment Status", Colors.CYAN)
    print_colored("[2] Show Project Structure", Colors.CYAN)
    print_colored("[3] Check Data Directories", Colors.CYAN)
    print_colored("[4] Return to Main Menu", Colors.CYAN)
    
    choice = input(f"\n{Colors.YELLOW}Select option (1-4): {Colors.ENDC}").strip()
    
    if choice == "1":
        print_colored(f"\n📍 Virtual Environment Status:", Colors.BLUE + Colors.BOLD)
        if check_venv():
            print_colored(f"{_safe_emoji('✅')} Found: {VENV_PYTHON}", Colors.GREEN)
        else:
            print_colored(f"{_safe_emoji('❌')} Not found: {VENV_PYTHON}", Colors.RED)
            print_colored("Run the following commands to create it:", Colors.YELLOW)
            print_colored("  python -m venv venv", Colors.CYAN)
            if platform.system() == "Windows":
                print_colored("  venv\\Scripts\\activate", Colors.CYAN)
            else:
                print_colored("  source venv/bin/activate", Colors.CYAN)
            print_colored("  pip install -r requirements.txt", Colors.CYAN)
    
    elif choice == "2":
        print_colored(f"\n📁 Project Structure:", Colors.BLUE + Colors.BOLD)
        print_colored(f"Project Root: {PROJECT_ROOT}", Colors.ENDC)
        print_colored(f"Virtual Env:  {VENV_DIR} {_safe_emoji('✅') if VENV_DIR.exists() else _safe_emoji('❌')}", Colors.ENDC)
        print_colored(f"My Trading:   {MY_TRADING_DIR} {_safe_emoji('✅') if MY_TRADING_DIR.exists() else _safe_emoji('❌')}", Colors.ENDC)
        print_colored(f"Scripts Dir:  {SCRIPTS_DIR} {_safe_emoji('✅') if SCRIPTS_DIR.exists() else _safe_emoji('❌')}", Colors.ENDC)
        print_colored(f"Start Your Own: {START_YOUR_OWN_DIR} {_safe_emoji('✅') if START_YOUR_OWN_DIR.exists() else _safe_emoji('❌')}", Colors.ENDC)
    
    elif choice == "3":
        print_colored(f"\n📂 Data Directory Status:", Colors.BLUE + Colors.BOLD)
        create_my_trading_dir()  # Ensure it exists
        
        # Check for key files
        portfolio_file = MY_TRADING_DIR / "llm_portfolio_update.csv"
        trade_log_file = MY_TRADING_DIR / "llm_trade_log.csv"
        cash_file = MY_TRADING_DIR / "cash_balances.json"
        
        print_colored(f"📁 {MY_TRADING_DIR}", Colors.CYAN)
        print_colored(f"  {_safe_emoji('📄')} Portfolio: {_safe_emoji('✅') if portfolio_file.exists() else _safe_emoji('❌')} {portfolio_file.name}", Colors.ENDC)
        print_colored(f"  {_safe_emoji('📄')} Trade Log: {_safe_emoji('✅') if trade_log_file.exists() else _safe_emoji('❌')} {trade_log_file.name}", Colors.ENDC)
        print_colored(f"  {_safe_emoji('📄')} Cash Balances: {_safe_emoji('✅') if cash_file.exists() else _safe_emoji('❌')} {cash_file.name}", Colors.ENDC)
        print_colored(f"\n💡 Tip: Use option 'u' from the main menu to update cash balances!", Colors.YELLOW)
    
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

def get_script_path(option: str) -> Optional[Path]:
    """Get the script path for a given menu option"""
    script_map = {
        "1": PROJECT_ROOT / "trading_script.py",
        "2": PROJECT_ROOT / "simple_automation.py", 
        "3": SCRIPTS_DIR / "Generate_Graph.py",
        "4": SCRIPTS_DIR / "ProcessPortfolio.py",
        "5": SCRIPTS_DIR / "Generate_Graph.py",
        "6": START_YOUR_OWN_DIR / "ProcessPortfolio.py",
        "7": START_YOUR_OWN_DIR / "Generate_Graph.py",
        "8": PROJECT_ROOT / "debug_instructions.py",
        "9": PROJECT_ROOT / "show_prompt.py",
        "d": PROJECT_ROOT / "prompt_generator.py",
        "w": PROJECT_ROOT / "prompt_generator.py",
        "u": PROJECT_ROOT / "update_cash.py",
        "m": PROJECT_ROOT / "menu_actions.py",
        "e": PROJECT_ROOT / "add_trade_from_email.py"
    }
    
    return script_map.get(option)

def main() -> None:
    """Main application loop"""
    if IS_TEST_MODE:
        print_colored("🧪 Initializing LLM Micro-Cap Trading Bot in TEST MODE...", Colors.YELLOW)
        print_colored(f"📁 Using test data folder: {DATA_DIR}", Colors.CYAN)
    else:
        print_colored(f"{_safe_emoji('🚀')} Initializing LLM Micro-Cap Trading Bot...", Colors.GREEN)
        print_colored(f"📁 Using production data folder: {DATA_DIR}", Colors.CYAN)
    
    # Ensure data directory exists
    if IS_TEST_MODE:
        DATA_DIR.mkdir(exist_ok=True)
    else:
        create_my_trading_dir()
    
    # Check venv status
    if not check_venv():
        print_colored(f"{_safe_emoji('⚠️')} Virtual environment not detected", Colors.YELLOW)
    else:
        print_colored(f"{_safe_emoji('✅')} Virtual environment ready", Colors.GREEN)
    
    options = get_menu_options()
    
    while True:
        show_menu()
        
        choice = input(f"\n{Colors.YELLOW}Select an option: {Colors.ENDC}").strip().lower()
        
        if choice == "q":
            print_colored("\n👋 Thanks for using LLM Micro-Cap Trading Bot!", Colors.GREEN)
            break
        
        elif choice == "c":
            handle_configuration()
            continue
        
        # Handle script execution options
        script_path = get_script_path(choice)
        if script_path:
            # Find the matching option for args
            selected_option = next((opt for opt in options if opt[0] == choice), None)
            if selected_option:
                _, title, _, args = selected_option
                print_colored(f"\n🎯 Selected: {title}", Colors.GREEN + Colors.BOLD)
                
                # Special handling for automation script
                if choice == "2":
                    api_key = input(f"\n{Colors.YELLOW}Enter OpenAI API Key (or press Enter to skip): {Colors.ENDC}").strip()
                    if api_key:
                        args.extend(["--api-key", api_key])
                    
                    dry_run = input(f"{Colors.YELLOW}Run in dry-run mode? (y/N): {Colors.ENDC}").strip().lower()
                    if dry_run == "y":
                        args.append("--dry-run")
                
                # Special handling for prompt generator
                elif choice == "d":
                    # Daily prompt - no additional args needed (defaults to daily)
                    pass
                elif choice == "w":
                    args.extend(["--type", "weekly"])
                
                # Special handling for email trade parser
                elif choice == "e":
                    # Email trade parser - no additional args needed, uses quick_add_trade.py
                    pass
                
                # Run the script
                return_code = run_with_venv(script_path, args)
                
                print_colored("\n" + "=" * 60, Colors.BLUE)
                if return_code == 0:
                    print_colored(f"{_safe_emoji('✅')} Script completed successfully!", Colors.GREEN)
                else:
                    print_colored(f"{_safe_emoji('❌')} Script exited with code: {return_code}", Colors.RED)
                
                input(f"\n{Colors.YELLOW}Press Enter to return to menu...{Colors.ENDC}")
            else:
                print_colored(f"{_safe_emoji('❌')} Invalid option selected", Colors.RED)
        else:
            print_colored(f"{_safe_emoji('❌')} Invalid option. Please try again.", Colors.RED)
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 Goodbye!", Colors.GREEN)
    except Exception as e:
        print_colored(f"\n{_safe_emoji('❌')} Unexpected error: {e}", Colors.RED)
        sys.exit(1)
