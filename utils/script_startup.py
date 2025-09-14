"""Script Startup Utility.

This module provides a simple, lightweight way to handle common script
initialization tasks like dependency checking. It's designed to have minimal
dependencies so it can be safely imported even when the full environment
isn't available.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional


def ensure_dependencies(required_packages: List[str], script_name: str) -> None:
    """Ensure required dependencies are available, exit with helpful message if not.
    
    This is a lightweight, self-contained dependency checker that doesn't depend
    on external modules. It provides helpful guidance to users when dependencies
    are missing.
    
    Args:
        required_packages: List of required package names
        script_name: Name of the current script for error messages
    """
    missing_packages = []
    
    # Check each required package
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    # If any packages are missing, show helpful error and exit
    if missing_packages:
        _show_dependency_error(missing_packages, script_name)
        sys.exit(1)


def _show_dependency_error(missing_packages: List[str], script_name: str) -> None:
    """Show a helpful error message when dependencies are missing."""
    print(f"\n❌ Missing Dependencies ({script_name})")
    print("=" * 60)
    
    print(f"\nThe following required packages are not available:")
    for pkg in missing_packages:
        print(f"  • {pkg}")
    
    # Check if virtual environment exists
    venv_exists = _check_venv_exists()
    venv_active = _is_venv_active()
    
    if not venv_active and venv_exists:
        print(f"\n🔧 SOLUTION:")
        print(f"It looks like you have a virtual environment but it's not activated.")
        print(f"Please activate it first:")
        if os.name == 'nt':  # Windows
            print(f"  venv\\Scripts\\activate")
        else:  # Mac/Linux
            print(f"  source venv/bin/activate")
        print(f"  python {script_name}")
        
    elif not venv_exists:
        print(f"\n🔧 SOLUTION:")
        print(f"Virtual environment not found. Please create and set it up:")
        print(f"  python -m venv venv")
        if os.name == 'nt':  # Windows
            print(f"  venv\\Scripts\\activate")
        else:  # Mac/Linux
            print(f"  source venv/bin/activate")
        print(f"  pip install -r requirements.txt")
        print(f"  python {script_name}")
        
    else:
        print(f"\n🔧 SOLUTION:")
        print(f"Install the missing packages:")
        print(f"  pip install {' '.join(missing_packages)}")
    
    print(f"\n💡 TIP:")
    print(f"Use the master control script to avoid these issues:")
    print(f"  python run.py")
    print("=" * 60)


def _check_venv_exists() -> bool:
    """Check if virtual environment exists."""
    project_root = Path(__file__).parent.parent.absolute()
    venv_dir = project_root / "venv"
    
    if os.name == 'nt':  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:  # Mac/Linux
        python_exe = venv_dir / "bin" / "python"
    
    return venv_dir.exists() and python_exe.exists()


def _is_venv_active() -> bool:
    """Check if we're currently running in a virtual environment."""
    return (hasattr(sys, 'real_prefix') or 
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))


def setup_project_path() -> None:
    """Add project root to Python path for imports."""
    project_root = Path(__file__).parent.parent.absolute()
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


# Common package groups for convenience
TRADING_PACKAGES = ['pandas']
DATA_PACKAGES = ['pandas', 'numpy']
WEB_PACKAGES = ['requests']


def ensure_trading_deps(script_name: str) -> None:
    """Convenience function to check trading dependencies."""
    ensure_dependencies(TRADING_PACKAGES, script_name)


def ensure_data_deps(script_name: str) -> None:
    """Convenience function to check data processing dependencies."""
    ensure_dependencies(DATA_PACKAGES, script_name)


def ensure_web_deps(script_name: str) -> None:
    """Convenience function to check web/API dependencies."""
    ensure_dependencies(WEB_PACKAGES, script_name)


def startup_check(script_name: Optional[str] = None, packages: Optional[List[str]] = None) -> None:
    """Complete startup check for a script.
    
    This function handles both path setup and dependency checking in one call.
    
    Args:
        script_name: Name of the script (auto-detected if None)
        packages: Required packages (defaults to trading packages)
    """
    # Auto-detect script name if not provided
    if script_name is None:
        script_name = Path(sys.argv[0]).name if sys.argv else "script"
    
    # Default to trading packages if not specified
    if packages is None:
        packages = TRADING_PACKAGES
    
    # Setup project path
    setup_project_path()
    
    # Check dependencies
    ensure_dependencies(packages, script_name)


if __name__ == "__main__":
    # Test the startup utility
    print("🔍 Testing Script Startup Utility")
    print(f"Virtual environment exists: {_check_venv_exists()}")
    print(f"Virtual environment active: {_is_venv_active()}")
    
    # Test dependency checking
    ensure_trading_deps("script_startup.py")