#!/usr/bin/env python3
"""
Test runner script for the LLM Micro-Cap Trading Bot.

This script provides an easy way to run all tests and specific test categories.
It also includes common bug prevention patterns we've learned from experience.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        # Use the virtual environment's Python
        if sys.platform == "win32":
            python_cmd = ["venv\\Scripts\\python.exe"]
        else:
            python_cmd = ["venv/bin/python"]
        
        # Replace 'python' with the venv python
        if cmd[0] == "python":
            cmd = python_cmd + cmd[1:]
        
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print("Output:", result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print("Error:", e.stderr)
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Main test runner function."""
    print("🧪 LLM Micro-Cap Trading Bot - Test Runner")
    print("=" * 60)
    
    # Ensure we're in the project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Activate virtual environment
    venv_activate = "venv\\Scripts\\activate" if sys.platform == "win32" else "venv/bin/activate"
    
    # Test categories
    test_categories = {
        "all": ["python", "-m", "pytest", "tests/", "-q", "--tb=line", "--durations=10"],
        "portfolio_display": ["python", "-m", "pytest", "tests/test_portfolio_display_bugs.py", "-q", "--tb=line", "--durations=5"],
        "emoji_unicode": ["python", "-m", "pytest", "tests/test_emoji_unicode_bugs.py", "-q", "--tb=line", "--durations=3"],
        "financial": ["python", "-m", "pytest", "tests/test_financial_calculations.py", "-q", "--tb=line", "--durations=5"],
        "integration": ["python", "-m", "pytest", "tests/test_integration.py", "-q", "--tb=line", "--durations=5"],
        "quick": ["python", "-m", "pytest", "tests/", "-q", "--tb=line", "-x"],
        "verbose": ["python", "-m", "pytest", "tests/", "-v", "--tb=short"]
    }
    
    if len(sys.argv) > 1:
        category = sys.argv[1]
        if category in test_categories:
            cmd = test_categories[category]
            success = run_command(cmd, f"Running {category} tests")
            sys.exit(0 if success else 1)
        else:
            print(f"❌ Unknown test category: {category}")
            print(f"Available categories: {', '.join(test_categories.keys())}")
            sys.exit(1)
    else:
        # Interactive mode
        print("\nAvailable test categories:")
        for i, (name, cmd) in enumerate(test_categories.items(), 1):
            print(f"  {i}. {name}: {' '.join(cmd)}")

        print("\nCommon Bug Prevention Patterns:")
        print("=" * 40)
        print("1. Emoji Syntax: Use _safe_emoji('✅') not '_safe_emoji('✅')'")
        print("2. Unicode Issues: Set pandas options to prevent problematic chars")
        print("3. P&L Calculations: Always handle None values with 'or 0'")
        print("4. Field Names: Ensure consistency between data structures")
        print("5. Console Output: Test both Rich and fallback modes")

        try:
            choice = input(f"\nEnter test category number (1-{len(test_categories)}) or name: ").strip()
            
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(test_categories):
                    category = list(test_categories.keys())[choice_num - 1]
                else:
                    print("❌ Invalid choice")
                    sys.exit(1)
            elif choice in test_categories:
                category = choice
            else:
                print("❌ Invalid choice")
                sys.exit(1)
            
            cmd = test_categories[category]
            success = run_command(cmd, f"Running {category} tests")
            sys.exit(0 if success else 1)
            
        except KeyboardInterrupt:
            print("\n\n👋 Test run cancelled by user")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
