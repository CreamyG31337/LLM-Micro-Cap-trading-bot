#!/usr/bin/env python3
"""
Backup WebAPI Package
=====================

Creates a local backup of the installed gemini-webapi package
in case it gets removed from public repositories.
"""

import sys
import os
import zipfile
import shutil
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
vendor_dir = project_root / "vendor"
vendor_dir.mkdir(exist_ok=True)

def backup_installed_package():
    """Backup the currently installed package."""
    try:
        import gemini_webapi
        package_path = Path(gemini_webapi.__file__).parent
        print(f"Found installed package at: {package_path}")
        
        # Get package root (parent of gemini_webapi module)
        package_root = package_path.parent
        
        # Look for setup.py or pyproject.toml to find the actual source
        if (package_root / "setup.py").exists() or (package_root / "pyproject.toml").exists():
            source_dir = package_root
        else:
            # Package is in site-packages, use the module directory
            source_dir = package_path
        
        backup_path = vendor_dir / "gemini-webapi-backup.zip"
        
        print(f"Creating backup: {backup_path}")
        
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add all Python files and important files
            for file_path in source_dir.rglob('*'):
                if file_path.is_file():
                    # Skip cache and compiled files
                    if '__pycache__' in str(file_path) or file_path.suffix in ['.pyc', '.pyo']:
                        continue
                    
                    # Get relative path for archive
                    try:
                        arcname = file_path.relative_to(source_dir.parent)
                        zf.write(file_path, arcname)
                    except ValueError:
                        # If relative path fails, use filename
                        zf.write(file_path, file_path.name)
        
        size_mb = backup_path.stat().st_size / 1024 / 1024
        print(f"✓ Backup created: {backup_path} ({size_mb:.2f} MB)")
        
        # Also try to get version info
        try:
            version = gemini_webapi.__version__ if hasattr(gemini_webapi, '__version__') else "unknown"
            print(f"  Package version: {version}")
        except:
            pass
        
        return backup_path
        
    except ImportError:
        print("✗ Package not installed. Install with: pip install gemini-webapi")
        return None
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("=" * 60)
    print("Backing up gemini-webapi package")
    print("=" * 60)
    
    backup = backup_installed_package()
    
    if backup:
        print("\n" + "=" * 60)
        print("✓ Backup complete!")
        print(f"  Location: {backup}")
        print(f"  This file is gitignored for security")
        print("\n  To restore if package is removed:")
        print("  1. Extract the zip file")
        print("  2. Install: pip install -e <extracted_directory>")
        print("  3. Or add to Python path in your code")
        print("=" * 60)
        return 0
    else:
        print("\n✗ Failed to create backup")
        return 1

if __name__ == "__main__":
    sys.exit(main())
