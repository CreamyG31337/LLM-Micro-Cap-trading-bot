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
from typing import Optional, List, Tuple, Dict, Any

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


def run_script_with_subprocess(command: List[str]) -> int:
    """Run a script using a subprocess, handling keyboard interrupts."""
    print_colored(f"{_safe_emoji('🚀')} Running: {' '.join(command)}", Colors.CYAN)
    print_colored("=" * 60, Colors.BLUE)
    
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT)
        return result.returncode
    except KeyboardInterrupt:
        print_colored(f"\n\n{_safe_emoji('⚠️')}  Script interrupted by user", Colors.YELLOW)
        return 130
    except Exception as e:
        print_colored(f"\n{_safe_emoji('❌')} Error running script: {e}", Colors.RED)
        return 1

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
    return run_script_with_subprocess(cmd)

def get_menu_options() -> List[Tuple[str, str, str, List[str]]]:
    """Get available menu options with (key, title, description, args)"""
    # Get active fund data directory - NO FALLBACKS ALLOWED
    try:
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        if fund_info["exists"] and fund_info["data_directory"]:
            data_folder_name = fund_info["data_directory"]
            data_dir_path = Path(data_folder_name)
        else:
            # No active fund - this is an error, not a fallback
            raise ValueError("No active fund found. Please select a fund first.")
    except ImportError:
        # Fund management not available - this is an error, not a fallback
        raise ImportError("Fund management not available. Cannot determine data directory safely.")
    
    return [
        ("1", f"{_safe_emoji('🔄')} Main Trading Script",
         "Run the main portfolio management and trading script - runs trading_script.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("2", f"{_safe_emoji('🤖')} Simple Automation",
         "Run LLM-powered automated trading (requires OpenAI API key) - runs simple_automation.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("3", f"{_safe_emoji('📊')} Generate Performance Graph",
         "Create performance comparison charts from your trading data - runs Generate_Graph.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("4", f"{_safe_emoji('📈')} Graph Benchmarks (365 days)",
         f"Generate benchmark performance graphs for last 365 days (S&P 500, QQQ, Russell 2000, VTI) - runs benchmark graphing",
         ["--data-dir", str(data_dir_path)]),
        
        ("8", f"{_safe_emoji('🐛')} Debug Instructions",
         "Show debug information and instructions - runs debug_instructions.py",
         []),
        
        ("9", f"{_safe_emoji('💡')} Show Prompt",
         "Display the current LLM prompt template - runs show_prompt.py",
         []),
        
        ("d", f"{_safe_emoji('📋')} Generate Daily Trading Prompt",
         "Generate daily trading prompt with current portfolio data - runs prompt_generator.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("w", f"{_safe_emoji('🔬')} Generate Weekly Deep Research Prompt",
         "Generate weekly deep research prompt for comprehensive portfolio analysis - runs prompt_generator.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("u", f"{_safe_emoji('💰')} Update Cash Balances",
         "Manually update your CAD/USD cash balances (deposits, withdrawals, corrections) - runs update_cash.py",
         ["--data-dir", str(data_dir_path)]),

        ("m", f"{_safe_emoji('👥')} Manage Contributors",
         "Edit contributor names and email addresses - runs menu_actions.py",
         ["--data-dir", str(data_dir_path)]),

        ("x", f"{_safe_emoji('📧')} Get Contributor Emails",
         "Output all contributor email addresses (semicolon-separated for mail programs) - runs get_emails.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("e", f"{_safe_emoji('📧')} Add Trade from Email",
         "Parse and add trades from email notifications - runs add_trade_from_email.py",
         ["--data-dir", str(data_dir_path), "--fund-name", fund_info.get("name", "") if fund_info["exists"] else ""]),
        
        ("r", f"{_safe_emoji('🔧')} Rebuild Portfolio",
         "Rebuild portfolio CSV + Supabase from trade log (fixes display issues) - runs rebuild_portfolio_complete.py",
         ["--data-dir", str(data_dir_path)]),
        
        ("l", f"{_safe_emoji('📜')} View Trade Log",
         "Display complete trade history in a formatted table - runs menu_actions.py",
         ["--action", "view_trade_log", "--data-dir", str(data_dir_path)]),
        
        ("c", f"{_safe_emoji('⚙️')} Configure",
         "Configuration options and setup",
         []),

        ("f", f"{_safe_emoji('🏦')} Switch Fund",
         "Quickly switch between available funds",
         []),

        ("k", f"{_safe_emoji('💾')} Manage Cache",
         "View, clear, or update cache data - runs cache management",
         []),

        ("b", f"{_safe_emoji('📦')} Archive Backups",
         "Archive old backups into daily zip files to save space.",
         []),

        ("z", f"{_safe_emoji('🧹')} Clear Test Data",
         "Clear all data for test funds (CSV files and database records) - runs clear_fund_data.py",
         ["--fund", "test", "--data-dir", str(data_dir_path)]),

        ("t", f"{_safe_emoji('🔄')} Restart",
         "Restart the application",
         []),

        ("q", f"{_safe_emoji('🚪')} Quit",
         "Exit the application",
         [])
    ]

def get_global_repository_type() -> str:
    """Get the global repository type based on system data source settings.
    
    Returns:
        Repository type string (CSV, Supabase, Hybrid, or Unknown)
    """
    try:
        # Get the actual repository being used by the system
        from data.repositories.repository_factory import get_repository_container
        container = get_repository_container()
        
        # Try to get the repository instance
        try:
            repository = container.get_repository('default')
            if repository:
                # Check the actual repository type
                repo_type = type(repository).__name__
                if 'CSV' in repo_type:
                    return "CSV"
                elif 'Supabase' in repo_type:
                    return "Supabase"
                elif 'Dual' in repo_type:
                    return "Dual-Write (CSV + Supabase)"
                else:
                    return repo_type
        except Exception:
            pass
        
        # Fallback: check if we can determine from settings
        try:
            from config.settings import Settings
            settings = Settings()
            repo_config = settings.get('repository', {})
            repo_type = repo_config.get('type', 'csv')
            
            if repo_type == 'csv':
                return "CSV"
            elif repo_type == 'supabase':
                return "Supabase"
            elif repo_type == 'dual-write':
                return "Dual-Write (CSV + Supabase)"
            else:
                return repo_type.title()
        except Exception:
            pass
        
        return "Unknown"
    except Exception:
        return "Unknown"

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
            fund_name = fund_info['name']
            data_directory = fund_info.get('data_directory', 'Unknown')
            repository_type = get_global_repository_type()
            
            print_colored(f"{_safe_emoji('📊')} Active Fund: {fund_name}", Colors.GREEN + Colors.BOLD)
            print_colored(f"{_safe_emoji('📁')} Data Folder: {data_directory}", Colors.CYAN)
            
            # Color code repository status - red for errors, green for success
            if "ERROR" in repository_type or "DOWN" in repository_type:
                print_colored(f"{_safe_emoji('🗄️')} Repository: {repository_type}", Colors.RED + Colors.BOLD)
            elif "✅" in repository_type:
                print_colored(f"{_safe_emoji('🗄️')} Repository: {repository_type}", Colors.GREEN + Colors.BOLD)
            else:
                print_colored(f"{_safe_emoji('🗄️')} Repository: {repository_type}", Colors.CYAN)
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
        ("1", f"{_safe_emoji('📈')} QQQ (Nasdaq-100)", "Technology-focused benchmark - ideal for growth/tech portfolios", "qqq"),
        ("2", f"{_safe_emoji('📊')} S&P 500", "Broad market benchmark - 500 largest US companies", "sp500"),
        ("3", f"{_safe_emoji('📉')} Russell 2000", "Small-cap benchmark - smaller US companies", "russell2000"),
        ("4", f"{_safe_emoji('📋')} VTI (Total Market)", "Complete US stock market benchmark", "vti"),
        ("5", f"{_safe_emoji('📊')} All Benchmarks", "Show all benchmarks on one chart for comprehensive comparison", "all"),
        ("6", f"{_safe_emoji('🔙')} Back to Main Menu", "Return without generating graph", "back")
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
    print_colored(f"\n{_safe_emoji('⚙️')} CONFIGURATION OPTIONS", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 40, Colors.HEADER)
    
    print_colored("\n[1] Check Virtual Environment Status", Colors.CYAN)
    print_colored("[2] Show Project Structure", Colors.CYAN)
    print_colored("[3] Check Data Directories", Colors.CYAN)
    print_colored(f"[4] {_safe_emoji('🏦')} Fund Management", Colors.CYAN)
    print_colored(f"[5] {_safe_emoji('📊')} App Data Source Configuration", Colors.CYAN)
    print_colored("[6] Return to Main Menu", Colors.CYAN)
    
    choice = input(f"\n{Colors.YELLOW}Select option (1-6): {Colors.ENDC}").strip()
    
    if choice == "1":
        print_colored(f"\n{_safe_emoji('📍')} Virtual Environment Status:", Colors.BLUE + Colors.BOLD)
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
        print_colored(f"\n{_safe_emoji('📁')} Project Structure:", Colors.BLUE + Colors.BOLD)
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
        print_colored(f"\n{_safe_emoji('📂')} Data Directory Status:", Colors.BLUE + Colors.BOLD)
        
        # Check current fund data directory
        try:
            from utils.fund_ui import get_current_fund_info
            fund_info = get_current_fund_info()
            if fund_info["exists"] and fund_info["data_directory"]:
                data_dir = Path(fund_info["data_directory"])
                print_colored(f"{_safe_emoji('📁')} Active Fund: {fund_info['name']} ({data_dir})", Colors.CYAN)
                
                # Check for key files
                portfolio_file = data_dir / "llm_portfolio_update.csv"
                trade_log_file = data_dir / "llm_trade_log.csv"
                cash_file = data_dir / "cash_balances.json"
                
                print_colored(f"  {_safe_emoji('📄')} Portfolio: {_safe_emoji('✅') if portfolio_file.exists() else _safe_emoji('❌')} {portfolio_file.name}", Colors.ENDC)
                print_colored(f"  {_safe_emoji('📄')} Trade Log: {_safe_emoji('✅') if trade_log_file.exists() else _safe_emoji('❌')} {trade_log_file.name}", Colors.ENDC)
                print_colored(f"  {_safe_emoji('📄')} Cash Balances: {_safe_emoji('✅') if cash_file.exists() else _safe_emoji('❌')} {cash_file.name}", Colors.ENDC)
            else:
                print_colored(f"{_safe_emoji('📁')} No Active Fund", Colors.YELLOW)
        except ImportError:
            print_colored(f"{_safe_emoji('📁')} Fund Management Not Available", Colors.YELLOW)
        
        print_colored(f"\n{_safe_emoji('💡')} Tip: Use option 'u' from the main menu to update cash balances!", Colors.YELLOW)
    
    elif choice == "4":
        try:
            from utils.fund_ui import show_fund_management_menu
            show_fund_management_menu()
            # Fund switching happened, return to main menu to refresh options
            return
        except ImportError as e:
            print_colored(f"{_safe_emoji('❌')} Fund management not available: {e}", Colors.RED)
            print_colored("This feature requires the fund management module.", Colors.YELLOW)
        return  # Don't show "Press Enter" after fund management
    
    elif choice == "5":
        handle_data_source_config()
        return  # Don't show "Press Enter" after data source config
    
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

def handle_fund_switch() -> None:
    """Handle quick fund switching"""
    print_colored(f"\n{_safe_emoji('🏦')} QUICK FUND SWITCH", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 40, Colors.HEADER)
    
    try:
        from utils.fund_ui import FundUI
        fund_ui = FundUI()
        
        # Get available funds
        funds = fund_ui.fund_manager.get_available_funds()
        if not funds:
            print_colored(f"{_safe_emoji('❌')} No funds available", Colors.RED)
            return
        
        # Display available funds
        print_colored(f"\n{_safe_emoji('📋')} Available funds:", Colors.CYAN)
        for i, fund in enumerate(funds, 1):
            print_colored(f"  [{i}] {fund}", Colors.CYAN)
        
        # Get user selection
        while True:
            choice = input(f"\n{Colors.YELLOW}Select fund (1-{len(funds)}) or Enter to cancel: {Colors.ENDC}").strip()
            
            if choice == "" or choice == "enter":
                print_colored("Fund switching cancelled.", Colors.YELLOW)
                return
            
            try:
                fund_index = int(choice) - 1
                if 0 <= fund_index < len(funds):
                    selected_fund = funds[fund_index]
                    if fund_ui.fund_manager.set_active_fund(selected_fund):
                        print_colored(f"{_safe_emoji('✅')} Successfully switched to fund: {selected_fund}", Colors.GREEN)
                    else:
                        print_colored(f"{_safe_emoji('❌')} Failed to switch fund.", Colors.RED)
                    return
                else:
                    print_colored(f"Invalid choice. Please select 1-{len(funds)}.", Colors.RED)
            except ValueError:
                print_colored("Please enter a valid number.", Colors.RED)
                
    except ImportError as e:
        print_colored(f"{_safe_emoji('❌')} Fund management not available: {e}", Colors.RED)
        print_colored("This feature requires the fund management module.", Colors.YELLOW)

def get_script_path(option: str) -> Optional[Path]:
    """Get the script path for a given menu option"""
    script_map = {
        "1": PROJECT_ROOT / "trading_script.py",
        "2": PROJECT_ROOT / "simple_automation.py",
        "3": SCRIPTS_DIR / "Generate_Graph.py",
        "4": "benchmark",  # Special handler for benchmark graphing
        "8": PROJECT_ROOT / "debug_instructions.py",
        "9": PROJECT_ROOT / "show_prompt.py",
        "d": PROJECT_ROOT / "prompt_generator.py",
        "w": PROJECT_ROOT / "prompt_generator.py",
        "u": PROJECT_ROOT / "update_cash.py",
        "m": PROJECT_ROOT / "menu_actions.py",
        "x": PROJECT_ROOT / "get_emails.py",
        "e": PROJECT_ROOT / "add_trade_from_email.py",
        "r": PROJECT_ROOT / "debug" / "rebuild_portfolio_complete.py",
        "l": PROJECT_ROOT / "menu_actions.py"
    }
    
    return script_map.get(option)

def handle_benchmark_graphing(data_dir: str) -> None:
    """Handle benchmark graphing for last 365 days."""
    print_colored("\n" + "=" * 80, Colors.HEADER)
    print_colored(f"{_safe_emoji('📈')} BENCHMARK PERFORMANCE GRAPHING", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 80, Colors.HEADER)
    print_colored(
        "Generating benchmark performance graphs for the last 365 days...",
        Colors.YELLOW
    )
    print_colored("This will download data for S&P 500, QQQ, Russell 2000, and VTI.", Colors.CYAN)
    
    try:
        # Import the benchmark graphing function from trading_script
        from trading_script import generate_benchmark_graph
        from config.settings import configure_system
        
        # Configure system settings
        settings = configure_system()
        settings.set('repository.csv.data_directory', data_dir)
        
        print_colored(f"Using data directory: {data_dir}", Colors.CYAN)
        print_colored("Downloading benchmark data and generating graph...", Colors.YELLOW)
        
        # Generate the benchmark graph
        generate_benchmark_graph(settings)
        
        print_colored(f"\n{_safe_emoji('✅')} Benchmark graph generated successfully!", Colors.GREEN)
        print_colored("Check the 'graphs' folder for the generated image.", Colors.CYAN)
        
    except ImportError as e:
        print_colored(f"{_safe_emoji('❌')} Error importing benchmark graphing function: {e}", Colors.RED)
        print_colored("This feature requires the trading_script module.", Colors.YELLOW)
    except Exception as e:
        print_colored(f"{_safe_emoji('❌')} Error generating benchmark graph: {e}", Colors.RED)
        print_colored("Please check your data directory and try again.", Colors.YELLOW)

    input(f"\n{Colors.YELLOW}Press Enter to return to the main menu...{Colors.ENDC}")

def handle_backup_archiving() -> None:
    """Handle backup archiving submenu."""
    print_colored("\n" + "=" * 80, Colors.HEADER)
    print_colored(f"{_safe_emoji('📦')} BACKUP ARCHIVING", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 80, Colors.HEADER)
    print_colored(
        "This utility will archive old backups into daily zip files.",
        Colors.YELLOW
    )
    
    try:
        days_old_str = input(f"Enter number of days old to archive (default: 1): ")
        days_old = int(days_old_str) if days_old_str else 1
        
        dry_run_choice = input("Perform a dry run first? (y/n, default: y): ").lower()
        dry_run = dry_run_choice != 'n'

        command = [
            sys.executable, 
            "utils/backup_cleanup.py",
            "--archive",
            "--days", str(days_old)
        ]
        if dry_run:
            command.append("--dry-run")

        run_script_with_subprocess(command)

    except ValueError:
        print_colored("Invalid number of days. Please enter an integer.", Colors.RED)
    except Exception as e:
        print_colored(f"An error occurred: {e}", Colors.RED)

    input("\nPress Enter to return to the main menu...")


def handle_clear_test_data() -> None:
    """Handle clear test data submenu."""
    print_colored("\n" + "=" * 80, Colors.HEADER)
    print_colored(f"{_safe_emoji('🧹')} CLEAR TEST DATA", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 80, Colors.HEADER)
    print_colored(
        "This utility will clear all data for test funds (CSV files and database records).",
        Colors.YELLOW
    )
    print_colored("⚠️  WARNING: This action cannot be undone!", Colors.RED + Colors.BOLD)
    
    try:
        # Get current fund info
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        
        if not fund_info["exists"]:
            print_colored("❌ No active fund found. Please select a fund first.", Colors.RED)
            input("\nPress Enter to return to the main menu...")
            return
        
        data_dir = fund_info["data_directory"]
        fund_name = fund_info["name"]
        
        print_colored(f"\nCurrent Fund: {fund_name}", Colors.CYAN)
        print_colored(f"Data Directory: {data_dir}", Colors.CYAN)
        
        # Ask for confirmation
        print_colored("\nThis will delete:", Colors.YELLOW)
        print_colored("  • All CSV files in the fund directory", Colors.YELLOW)
        print_colored("  • All database records for this fund", Colors.YELLOW)
        print_colored("  • All backup files", Colors.YELLOW)
        
        confirm = input("\nType 'CLEAR' to confirm deletion: ").strip()
        if confirm != "CLEAR":
            print_colored("❌ Operation cancelled.", Colors.YELLOW)
            input("\nPress Enter to return to the main menu...")
            return
        
        # Run the clear command
        command = [
            sys.executable,
            "utils/clear_fund_data.py",
            "--fund", fund_name.lower().replace(" ", "_"),
            "--data-dir", data_dir,
            "--confirm"
        ]
        
        print_colored(f"\n{_safe_emoji('🚀')} Running clear command...", Colors.CYAN)
        run_script_with_subprocess(command)
        
    except Exception as e:
        print_colored(f"An error occurred: {e}", Colors.RED)
    
    input("\nPress Enter to return to the main menu...")


def handle_data_source_config() -> None:
    """Handle data source configuration for the Python application"""
    print_colored(f"\n{_safe_emoji('📊')} PYTHON APP DATA SOURCE CONFIGURATION", Colors.HEADER + Colors.BOLD)
    print_colored("=" * 50, Colors.HEADER)
    
    # Show current configuration
    current_info = get_data_source_info()
    print_colored(f"\nCurrent Python App: {current_info}", Colors.CYAN + Colors.BOLD)
    print_colored(f"Web Dashboard: Always uses Supabase (hosted on Vercel)", Colors.YELLOW)
    
    print_colored(f"\n{_safe_emoji('📋')} Python App Data Source Options:", Colors.BLUE + Colors.BOLD)
    print_colored("[1] CSV Mode - Read from CSV files, write to CSV only", Colors.CYAN)
    print_colored("[2] Supabase Mode - Read from Supabase, write to both Supabase + CSV", Colors.CYAN)
    print_colored("[3] CSV Dual-Write - Read from CSV, write to both CSV + Supabase", Colors.CYAN)
    print_colored("[4] Cancel - Return to configuration menu", Colors.CYAN)
    
    choice = input(f"\n{Colors.YELLOW}Select data source (1-4): {Colors.ENDC}").strip()
    
    data_source_map = {
        "1": "csv",
        "2": "supabase", 
        "3": "csv-dual-write"
    }
    
    if choice == "4":
        print_colored("Configuration cancelled.", Colors.YELLOW)
        return
    
    if choice not in data_source_map:
        print_colored("Invalid choice. Configuration cancelled.", Colors.RED)
        return
    
    new_data_source = data_source_map[choice]
    
    # Validate and switch fund based on data source
    print_colored("\n🔍 Validating fund availability for selected data source...", Colors.CYAN)
    
    # Get current fund info
    current_fund = None
    try:
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        if fund_info["exists"]:
            current_fund = fund_info["name"]
    except ImportError:
        current_fund = "Unknown"
    
    # Check fund availability based on data source
    available_funds = []
    recommended_fund = None
    
    if new_data_source == "supabase":
        # Query Supabase for available funds
        try:
            import os
            # Load .env from web_dashboard directory
            from dotenv import load_dotenv
            load_dotenv(Path("web_dashboard/.env"))
            
            from web_dashboard.supabase_client import SupabaseClient
            
            if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
                client = SupabaseClient()
                if client.test_connection():
                    available_funds = client.get_available_funds()
                    print_colored(f"  {_safe_emoji('✅')} Supabase connection successful", Colors.GREEN)
                    print_colored(f"  {_safe_emoji('📊')} Available funds in Supabase: {', '.join(available_funds)}", Colors.CYAN)
                    
                    if available_funds:
                        # Recommend first available fund if current fund not in Supabase
                        if current_fund in available_funds:
                            recommended_fund = current_fund
                            print_colored(f"  {_safe_emoji('✅')} Current fund '{current_fund}' is available in Supabase", Colors.GREEN)
                        else:
                            recommended_fund = available_funds[0]
                            print_colored(f"  ⚠️  Current fund '{current_fund}' not found in Supabase", Colors.YELLOW)
                            print_colored(f"  {_safe_emoji('📁')} Will switch to: {recommended_fund}", Colors.CYAN)
                    else:
                        print_colored(f"  ❌ No funds found in Supabase database", Colors.RED)
                        print_colored(f"  {_safe_emoji('📊')} You need to migrate fund data first", Colors.YELLOW)
                        return
                else:
                    print_colored(f"  ❌ Supabase connection failed", Colors.RED)
                    print_colored(f"  {_safe_emoji('📊')} Cannot switch to Supabase mode", Colors.YELLOW)
                    return
            else:
                print_colored(f"  ❌ Supabase environment variables not configured", Colors.RED)
                print_colored(f"  {_safe_emoji('📊')} Check web_dashboard/.env file", Colors.YELLOW)
                return
        except Exception as e:
            print_colored(f"  ❌ Error checking Supabase: {e}", Colors.RED)
            return
    
    elif new_data_source == "csv":
        # Use CSV funds list
        available_funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
        recommended_fund = current_fund if current_fund in available_funds else available_funds[0]
        print_colored(f"  {_safe_emoji('📊')} CSV mode - all funds available: {', '.join(available_funds)}", Colors.CYAN)
    
    elif new_data_source == "csv-dual-write":
        # CSV dual-write mode - reads CSV, writes to both
        available_funds = ["Project Chimera", "RRSP Lance Webull", "TFSA", "TEST"]
        recommended_fund = current_fund if current_fund in available_funds else available_funds[0]
        print_colored(f"  {_safe_emoji('📊')} CSV Dual-Write mode - reads CSV, writes to both CSV + Supabase", Colors.CYAN)
        print_colored(f"  {_safe_emoji('📁')} Available funds: {', '.join(available_funds)}", Colors.CYAN)
    
    # Update configuration
    try:
        import json
        config_file = Path("repository_config.json")
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
        else:
            config = {"repository": {"type": "csv"}}
        
        # Update repository.type (Python app configuration)
        if "repository" not in config:
            config["repository"] = {}
        
        # Map data source to repository type
        if new_data_source == "csv-dual-write":
            repo_type = "dual-write"
        elif new_data_source == "supabase":
            repo_type = "supabase-dual-write"  # Use Supabase dual-write for Supabase mode
        else:
            repo_type = new_data_source
        config["repository"]["type"] = repo_type
        
        # Web dashboard always uses Supabase (hosted on Vercel, no access to CSV files)
        if "web_dashboard" not in config:
            config["web_dashboard"] = {}
        config["web_dashboard"]["data_source"] = "supabase"
        config["web_dashboard"]["_comment"] = "Web dashboard always uses Supabase (hosted on Vercel)"
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        data_source_names = {
            "csv": "CSV Mode", 
            "supabase": "Supabase Mode", 
            "csv-dual-write": "CSV Dual-Write Mode"
        }
        print_colored(f"\n{_safe_emoji('✅')} Data source updated to: {data_source_names[new_data_source]}", Colors.GREEN)
        
        # Switch fund if needed
        if recommended_fund and recommended_fund != current_fund and new_data_source in ["supabase", "csv", "csv-dual-write"]:
            try:
                from utils.fund_ui import FundUI
                fund_ui = FundUI()
                if fund_ui.fund_manager.set_active_fund(recommended_fund):
                    print_colored(f"{_safe_emoji('✅')} Switched to fund: {recommended_fund}", Colors.GREEN)
                else:
                    print_colored(f"❌ Failed to switch to fund: {recommended_fund}", Colors.RED)
            except Exception as e:
                print_colored(f"⚠️  Could not switch fund automatically: {e}", Colors.YELLOW)
                print_colored(f"  You may need to manually switch to a compatible fund", Colors.YELLOW)
        
        # Automatically restart to apply changes
        print_colored(f"\n{_safe_emoji('🔄')} Restarting application to apply changes...", Colors.YELLOW)
        import time
        time.sleep(1)
        sys.exit(42)  # Exit code 42 signals restart
        
        if new_data_source == "supabase":
            print_colored(f"\n{_safe_emoji('📊')} Supabase Mode Active:", Colors.GREEN + Colors.BOLD)
            print_colored(f"  - Available funds: {', '.join(available_funds)}", Colors.GREEN)
            print_colored(f"  - Active fund: {recommended_fund or 'None'}", Colors.GREEN)
        
    except Exception as e:
        print_colored(f"❌ Error updating configuration: {e}", Colors.RED)
    
    input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")

def get_data_source_info() -> str:
    """Get information about the current data source configuration"""
    try:
        import json
        config_file = Path("repository_config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Check repository configuration
            repo_config = config.get("repository", {})
            repo_type = repo_config.get("type", "csv")
            
            # Check if Supabase is actually available
            supabase_available = False
            try:
                from web_dashboard.supabase_client import SupabaseClient
                import os
                if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"):
                    client = SupabaseClient()
                    supabase_available = client.test_connection()
            except Exception:
                pass
            
            if repo_type == "csv":
                return f"{_safe_emoji('📊')} Data Source: CSV Mode (CSV only)"
            elif repo_type == "supabase":
                if supabase_available:
                    return f"{_safe_emoji('📊')} Data Source: Supabase Mode (Supabase + CSV backup) {_safe_emoji('✅')}"
                else:
                    return f"{_safe_emoji('📊')} Data Source: Supabase Mode (Supabase unavailable) ⚠️"
            elif repo_type == "dual-write":
                if supabase_available:
                    return f"{_safe_emoji('📊')} Data Source: CSV Dual-Write (CSV + Supabase backup) {_safe_emoji('✅')}"
                else:
                    return f"{_safe_emoji('📊')} Data Source: CSV Dual-Write (CSV only - Supabase unavailable) ⚠️"
            elif repo_type == "supabase-dual-write":
                if supabase_available:
                    return f"{_safe_emoji('📊')} Data Source: Supabase Dual-Write (Supabase + CSV backup) {_safe_emoji('✅')}"
                else:
                    return f"{_safe_emoji('📊')} Data Source: Supabase Dual-Write (Supabase unavailable) ⚠️"
            else:
                return f"{_safe_emoji('📊')} Data Source: {repo_type} (Unknown mode)"
        
    except Exception as e:
        return f"{_safe_emoji('📊')} Data Source: Unknown (Error: {e})"
    
    return f"{_safe_emoji('📊')} Data Source: CSV Mode (Default)"

def main() -> None:
    """Main application loop"""
    # Load environment variables first (for Supabase credentials)
    try:
        from dotenv import load_dotenv
        load_dotenv()  # Load from root .env
        load_dotenv(Path("web_dashboard/.env"))  # Also try web_dashboard/.env
    except ImportError:
        pass  # dotenv not available, will use system env vars
    
    print_colored(f"{_safe_emoji('🚀')} Initializing LLM Micro-Cap Trading Bot...", Colors.GREEN)
    
    # Show current fund information
    try:
        from utils.fund_ui import get_current_fund_info
        fund_info = get_current_fund_info()
        if fund_info["exists"]:
            print_colored(f"{_safe_emoji('📁')} Using fund data folder: {fund_info['data_directory']}", Colors.CYAN)
        else:
            print_colored(f"{_safe_emoji('📁')} No active fund configured - please set up a fund first", Colors.YELLOW)
    except ImportError:
        print_colored(f"{_safe_emoji('📁')} Fund management not available - using legacy mode", Colors.YELLOW)
    
    # Configure repository based on settings
    try:
        from config.settings import Settings
        from data.repositories.repository_factory import configure_repositories, get_repository_container
        
        settings = Settings()
        repo_config = settings.get_repository_config()
        
        # Configure the repository container with the current settings
        configure_repositories({'default': repo_config})
        
        # Clear any existing repositories to ensure fresh configuration
        container = get_repository_container()
        container.clear()
        configure_repositories({'default': repo_config})
        
    except Exception as e:
        print_colored(f"{_safe_emoji('⚠️')} Repository configuration warning: {e}", Colors.YELLOW)
    
    # Show data source information
    data_source_info = get_data_source_info()
    print_colored(data_source_info, Colors.CYAN)
    
    # Ensure legacy directories exist for backward compatibility
    LEGACY_MY_TRADING_DIR.mkdir(exist_ok=True)
    LEGACY_TEST_DATA_DIR.mkdir(exist_ok=True)
    
    # Check venv status
    if not check_venv():
        print_colored(f"{_safe_emoji('⚠️')} Virtual environment not detected", Colors.YELLOW)
    else:
        print_colored(f"{_safe_emoji('✅')} Virtual environment ready", Colors.GREEN)
    
    try:
        options = get_menu_options()
    except (ValueError, ImportError) as e:
        print_colored(f"{_safe_emoji('❌')} Error: {e}", Colors.RED)
        print_colored("Please select a fund first using option 'f' (Switch Fund)", Colors.YELLOW)
        print_colored("Or restart the application", Colors.YELLOW)
        return
    
    while True:
        show_menu()
        
        choice = input(f"\n{Colors.YELLOW}Select an option: {Colors.ENDC}").strip().lower()
        
        if choice == "q":
            print_colored("\n👋 Thanks for using LLM Micro-Cap Trading Bot!", Colors.GREEN)
            break
        
        elif choice == "t":
            print_colored(f"\n{_safe_emoji('🔄')} Restarting the application...", Colors.YELLOW)
            print_colored("Please wait while the application restarts...", Colors.CYAN)
            # Exit with code 42 to signal restart
            sys.exit(42)
        
        elif choice == "c":
            handle_configuration()
            # Refresh options after configuration changes (fund switching, etc.)
            try:
                options = get_menu_options()
            except (ValueError, ImportError) as e:
                print_colored(f"{_safe_emoji('❌')} Error refreshing menu: {e}", Colors.RED)
                print_colored("Please restart the application", Colors.YELLOW)
                return
            continue

        elif choice == "f":
            handle_fund_switch()
            # Refresh options after fund switching
            try:
                options = get_menu_options()
            except (ValueError, ImportError) as e:
                print_colored(f"{_safe_emoji('❌')} Error refreshing menu: {e}", Colors.RED)
                print_colored("Please restart the application", Colors.YELLOW)
                return
            continue

        elif choice == "b":
            handle_backup_archiving()
            continue

        elif choice == "z":
            handle_clear_test_data()
            continue

        elif choice == "k":
            try:
                from utils.cache_ui import show_cache_management_menu
                show_cache_management_menu()
            except ImportError as e:
                print_colored(f"{_safe_emoji('❌')} Cache management not available: {e}", Colors.RED)
                print_colored("This feature requires the cache management module.", Colors.YELLOW)
            continue
        
        # Handle special cases first
        if choice == "4":
            # Benchmark graphing - special handler
            selected_option = next((opt for opt in options if opt[0] == choice), None)
            if selected_option:
                _, title, _, args = selected_option
                print_colored(f"\n🎯 Selected: {title}", Colors.GREEN + Colors.BOLD)
                
                # Get data directory from args
                data_dir = args[1] if len(args) > 1 else "trading_data/funds/Project Chimera"
                handle_benchmark_graphing(data_dir)
                continue
        
        # Handle script execution options
        script_path = get_script_path(choice)
        if script_path:
            # Find the matching option for args
            selected_option = next((opt for opt in options if opt[0] == choice), None)
            if selected_option:
                _, title, _, args = selected_option
                # Make a copy of args to avoid modifying the original tuple
                args = args.copy()
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
                    
                    # Get the current fund name and pass it to the graph script
                    try:
                        from utils.fund_ui import get_current_fund_info
                        fund_info = get_current_fund_info()
                        if fund_info["exists"] and fund_info["name"]:
                            args.extend(["--fund", fund_info["name"]])
                            print_colored(f"\n{_safe_emoji('📊')} Generating graph for fund: {fund_info['name']} with {benchmark.upper()} benchmark...", Colors.CYAN)
                        else:
                            print_colored(f"\n{_safe_emoji('📊')} Generating graph with {benchmark.upper()} benchmark...", Colors.CYAN)
                    except ImportError:
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
                            print_colored("❌ No active fund found - cannot rebuild portfolio", Colors.RED)
                            input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                            continue
                    except ImportError:
                        print_colored("❌ Fund management not available - cannot rebuild portfolio", Colors.RED)
                        input(f"\n{Colors.YELLOW}Press Enter to continue...{Colors.ENDC}")
                        continue
                
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
