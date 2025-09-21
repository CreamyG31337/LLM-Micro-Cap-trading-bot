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
SCRIPTS_DIR = PROJECT_ROOT / "Scripts and CSV Files"

# Legacy directories (for backward compatibility)
LEGACY_MY_TRADING_DIR = PROJECT_ROOT / "trading_data" / "prod"
LEGACY_TEST_DATA_DIR = PROJECT_ROOT / "trading_data" / "dev"

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
    # Get active fund data directory
    try:
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        if fund_info["exists"] and fund_info["data_directory"]:
            data_folder_name = fund_info["data_directory"]
            data_dir_path = Path(data_folder_name)
        else:
            # No active fund, use fallback
            data_folder_name = "trading_data/funds/Project Chimera"
            data_dir_path = Path(data_folder_name)
    except ImportError:
        # Fund management not available, use fallback
        data_folder_name = "trading_data/funds/Project Chimera"
        data_dir_path = Path(data_folder_name)
    
    return [
        ("1", "🔄 Main Trading Script",
         f"Run the main portfolio management and trading script (uses '{data_folder_name}' folder) - runs trading_script.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("2", f"{_safe_emoji('🤖')} Simple Automation",
         f"Run LLM-powered automated trading (requires OpenAI API key) (uses '{data_folder_name}' folder) - runs simple_automation.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("3", f"{_safe_emoji('📊')} Generate Performance Graph",
         f"Create performance comparison charts from your trading data (uses '{data_folder_name}' folder) - runs Generate_Graph.py",
         ["--data-dir", str(data_dir_path)]),
        
        
        
        ("8", "🐛 Debug Instructions",
         "Show debug information and instructions - runs debug_instructions.py",
         []),
        
        ("9", "💡 Show Prompt",
         "Display the current LLM prompt template - runs show_prompt.py",
         []),
        
        ("d", "📋 Generate Daily Trading Prompt",
         f"Generate daily trading prompt with current portfolio data (uses '{data_folder_name}' folder) - runs prompt_generator.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("w", "🔬 Generate Weekly Deep Research Prompt",
         f"Generate weekly deep research prompt for comprehensive portfolio analysis (uses '{data_folder_name}' folder) - runs prompt_generator.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("u", "💰 Update Cash Balances",
         f"Manually update your CAD/USD cash balances (deposits, withdrawals, corrections) (uses '{data_folder_name}' folder) - runs update_cash.py",
         ["--data-dir", str(data_dir_path)]),

        ("m", "👥 Manage Contributors",
         f"Edit contributor names and email addresses (uses '{data_folder_name}' folder) - runs menu_actions.py",
         ["--data-dir", str(data_dir_path)]),

        ("x", "📧 Get Contributor Emails",
         f"Output all contributor email addresses (semicolon-separated for mail programs) (uses '{data_folder_name}' folder) - runs get_emails.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("e", "📧 Add Trade from Email",
         f"Parse and add trades from email notifications (uses '{data_folder_name}' folder) - runs add_trade_from_email.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("r", "🔧 Rebuild Portfolio",
         f"Rebuild portfolio CSV from trade log (fixes display issues) (uses '{data_folder_name}' folder) - runs rebuild_portfolio_from_scratch.py",
         ["--data-dir", str(data_dir_path)]),
        
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
    
    # Show current fund information
    try:
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        if fund_info["exists"]:
            print_colored(f"{_safe_emoji('📊')} Active Fund: {fund_info['name']}", Colors.GREEN + Colors.BOLD)
        else:
            print_colored(f"{_safe_emoji('📊')} Active Fund: No Active Fund", Colors.YELLOW + Colors.BOLD)
        print_colored("-" * 80, Colors.HEADER)
    except ImportError:
        # Fund management not available, show fallback
        print_colored(f"{_safe_emoji('📊')} Active Fund: Fund Management Not Available", Colors.YELLOW + Colors.BOLD)
        print_colored("-" * 80, Colors.HEADER)
    
    options = get_menu_options()
    
    for key, title, description, _ in options:
        # Format: [key] title - description (all on one line with different colors)
        print(f"{Colors.CYAN}{Colors.BOLD}[{key}] {title} - {Colors.ENDC}{description}")
    
    print_colored("\n" + "=" * 80, Colors.HEADER)

def handle_benchmark_selection() -> str:
    """Handle benchmark selection submenu"""
    print_colored(f"\n{_safe_emoji('📊')} BENCHMARK SELECTION", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 40, Colors.HEADER)
    
    benchmark_options = [
        ("1", "📈 QQQ (Nasdaq-100)", "Technology-focused benchmark - ideal for growth/tech portfolios", "qqq"),
        ("2", f"{_safe_emoji('📊')} S&P 500", "Broad market benchmark - 500 largest US companies", "sp500"),
        ("3", "📉 Russell 2000", "Small-cap benchmark - smaller US companies", "russell2000"),
        ("4", "📋 VTI (Total Market)", "Complete US stock market benchmark", "vti"),
        ("5", f"{_safe_emoji('📊')} All Benchmarks", "Show all benchmarks on one chart for comprehensive comparison", "all"),
        ("6", "🔙 Back to Main Menu", "Return without generating graph", "back")
    ]
    
    for key, title, description, _ in benchmark_options:
        print(f"{Colors.CYAN}{Colors.BOLD}[{key}] {title} - {Colors.ENDC}{description}")
    
    while True:
        choice = input(f"\n{Colors.YELLOW}Select benchmark (1-6): {Colors.ENDC}").strip()
        
        if choice in ["1", "2", "3", "4", "5", "6"]:
            selected = next((opt for opt in benchmark_options if opt[0] == choice), None)
            if selected:
                return selected[3]  # Return the benchmark code
        
        print_colored(f"{_safe_emoji('❌')} Invalid choice. Please select 1-6.", Colors.RED)


def handle_configuration() -> None:
    """Handle configuration menu"""
    print_colored("\n⚙️  CONFIGURATION OPTIONS", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 40, Colors.HEADER)
    
    print_colored("\n[1] Check Virtual Environment Status", Colors.CYAN)
    print_colored("[2] Show Project Structure", Colors.CYAN)
    print_colored("[3] Check Data Directories", Colors.CYAN)
    print_colored("[4] 🏦 Fund Management", Colors.CYAN)
    print_colored("[5] Return to Main Menu", Colors.CYAN)
    
    choice = input(f"\n{Colors.YELLOW}Select option (1-5): {Colors.ENDC}").strip()
    
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
        print_colored(f"Scripts Dir:  {SCRIPTS_DIR} {_safe_emoji('✅') if SCRIPTS_DIR.exists() else _safe_emoji('❌')}", Colors.ENDC)
        
        # Show fund information
        try:
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            if fund_info["exists"]:
                print_colored(f"Active Fund:  {fund_info['name']} ({fund_info['data_directory']}) {_safe_emoji('✅')}", Colors.ENDC)
            else:
                print_colored(f"Active Fund:  No Active Fund {_safe_emoji('❌')}", Colors.ENDC)
        except ImportError:
            print_colored(f"Active Fund:  Fund Management Not Available {_safe_emoji('❌')}", Colors.ENDC)
    
    elif choice == "3":
        print_colored(f"\n📂 Data Directory Status:", Colors.BLUE + Colors.BOLD)
        
        # Check current fund data directory
        try:
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            if fund_info["exists"] and fund_info["data_directory"]:
                data_dir = Path(fund_info["data_directory"])
                print_colored(f"📁 Active Fund: {fund_info['name']} ({data_dir})", Colors.CYAN)
                
                # Check for key files
                portfolio_file = data_dir / "llm_portfolio_update.csv"
                trade_log_file = data_dir / "llm_trade_log.csv"
                cash_file = data_dir / "cash_balances.json"
                
                print_colored(f"  {_safe_emoji('📄')} Portfolio: {_safe_emoji('✅') if portfolio_file.exists() else _safe_emoji('❌')} {portfolio_file.name}", Colors.ENDC)
                print_colored(f"  {_safe_emoji('📄')} Trade Log: {_safe_emoji('✅') if trade_log_file.exists() else _safe_emoji('❌')} {trade_log_file.name}", Colors.ENDC)
                print_colored(f"  {_safe_emoji('📄')} Cash Balances: {_safe_emoji('✅') if cash_file.exists() else _safe_emoji('❌')} {cash_file.name}", Colors.ENDC)
            else:
                print_colored("📁 No Active Fund", Colors.YELLOW)
        except ImportError:
            print_colored("📁 Fund Management Not Available", Colors.YELLOW)
        
        print_colored(f"\n💡 Tip: Use option 'u' from the main menu to update cash balances!", Colors.YELLOW)
    
    elif choice == "4":
        try:
            from utils.fund_ui import show_fund_management_menu
            show_fund_management_menu()
        except ImportError as e:
            print_colored(f"{_safe_emoji('❌')} Fund management not available: {e}", Colors.RED)
            print_colored("This feature requires the fund management module.", Colors.YELLOW)
        return  # Don't show "Press Enter" after fund management
    
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

def get_script_path(option: str) -> Optional[Path]:
    """Get the script path for a given menu option"""
    script_map = {
        "1": PROJECT_ROOT / "trading_script.py",
        "2": PROJECT_ROOT / "simple_automation.py",
        "3": SCRIPTS_DIR / "Generate_Graph.py",
        "8": PROJECT_ROOT / "debug_instructions.py",
        "9": PROJECT_ROOT / "show_prompt.py",
        "d": PROJECT_ROOT / "prompt_generator.py",
        "w": PROJECT_ROOT / "prompt_generator.py",
        "u": PROJECT_ROOT / "update_cash.py",
        "m": PROJECT_ROOT / "menu_actions.py",
        "x": PROJECT_ROOT / "get_emails.py",
        "e": PROJECT_ROOT / "add_trade_from_email.py",
        "r": PROJECT_ROOT / "debug" / "rebuild_portfolio_from_scratch.py"
    }
    
    return script_map.get(option)

def main() -> None:
    """Main application loop"""
    print_colored(f"{_safe_emoji('🚀')} Initializing LLM Micro-Cap Trading Bot...", Colors.GREEN)
    
    # Show current fund information
    try:
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        if fund_info["exists"]:
            print_colored(f"📁 Using fund data folder: {fund_info['data_directory']}", Colors.CYAN)
        else:
            print_colored("📁 Using fallback data folder: trading_data/funds/Project Chimera", Colors.YELLOW)
    except ImportError:
        print_colored("📁 Using fallback data folder: trading_data/funds/Project Chimera", Colors.YELLOW)
    
    # Ensure legacy directories exist for backward compatibility
    LEGACY_MY_TRADING_DIR.mkdir(exist_ok=True)
    LEGACY_TEST_DATA_DIR.mkdir(exist_ok=True)
    
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
                
                # Special handling for graph generation with benchmark selection
                elif choice == "3":
                    benchmark = handle_benchmark_selection()
                    if benchmark == "back":
                        continue  # Return to main menu
                    args.extend(["--benchmark", benchmark])
                    print_colored(f"\n{_safe_emoji('📊')} Generating graph with {benchmark.upper()} benchmark...", Colors.CYAN)
                
                # Special handling for prompt generator
                elif choice == "d":
                    # Daily prompt - no additional args needed (defaults to daily)
                    pass
                elif choice == "w":
                    args.extend(["--type", "weekly"])
                
                # Special handling for email trade parser
                elif choice == "e":
                    # Email trade parser - no additional args needed, uses add_trade_from_email.py
                    pass
                elif choice == "r":
                    # Rebuild portfolio - pass current fund data directory as positional argument
                    try:
                        from utils.fund_ui import get_current_fund_info
                        fund_info = get_current_fund_info()
                        if fund_info["exists"] and fund_info["data_directory"]:
                            args = [fund_info["data_directory"]]
                        else:
                            args = ["trading_data/funds/Project Chimera"]
                    except ImportError:
                        args = ["trading_data/funds/Project Chimera"]
                
                # Run the script
                return_code = run_with_venv(script_path, args)
                
                print_colored("\n" + "=" * 60, Colors.BLUE)
                if return_code == 0:
                    print_colored(f"{_safe_emoji('✅')} Script completed successfully!", Colors.GREEN)
                else:
                    print_colored(f"{_safe_emoji('❌')} Script exited with code: {return_code}", Colors.RED)
                
                input(f"\n{Colors.YELLOW}Press Enter to return to menu...{Colors.ENDC}")
                continue  # Return to main menu loop
            else:
                print_colored(f"{_safe_emoji('❌')} Invalid option selected", Colors.RED)
                continue  # Return to main menu loop
        else:
            print_colored(f"{_safe_emoji('❌')} Invalid option. Please try again.", Colors.RED)
            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
            continue  # Return to main menu loop

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 Goodbye!", Colors.GREEN)
    except Exception as e:
        print_colored(f"\n{_safe_emoji('❌')} Unexpected error: {e}", Colors.RED)
        sys.exit(1)
