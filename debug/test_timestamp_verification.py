"""Test script for timestamp-based integrity verification.

This script tests the new timestamp-based integrity checking system.
"""

import sys
import tempfile
import time
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.hash_verification import (
    initialize_launch_time,
    get_python_files,
    check_file_modification_times,
    verify_script_integrity,
    require_script_integrity,
    ScriptIntegrityError,
    get_launch_time_string
)


def test_launch_time_initialization():
    """Test launch time initialization."""
    print("Testing launch time initialization...")
    
    # Initialize launch time
    initialize_launch_time()
    
    # Check that launch time is set
    launch_time_str = get_launch_time_string()
    assert launch_time_str != "Not initialized", "Launch time should be initialized"
    print(f"✅ Launch time initialized: {launch_time_str}")


def test_python_file_detection():
    """Test Python file detection."""
    print("\nTesting Python file detection...")
    
    python_files = get_python_files(project_root)
    
    # Should find the main trading script
    trading_script = project_root / "trading_script.py"
    assert trading_script in python_files, "Should find trading_script.py"
    
    # Should find files in subdirectories
    hash_verification = project_root / "utils" / "hash_verification.py"
    assert hash_verification in python_files, "Should find hash_verification.py"
    
    print(f"✅ Found {len(python_files)} Python files")


def test_integrity_verification():
    """Test integrity verification."""
    print("\nTesting integrity verification...")
    
    # Initialize launch time
    initialize_launch_time()
    
    # Should pass initially (no files modified)
    assert verify_script_integrity(project_root), "Should pass initially"
    print("✅ Initial integrity check passes")
    
    # Create a temporary Python file (simulates modification)
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py', dir=project_root) as f:
        f.write("print('test')")
        temp_file = Path(f.name)
    
    try:
        # Should still pass (temp file is not in our tracked files)
        assert verify_script_integrity(project_root), "Should pass with untracked files"
        print("✅ Integrity check passes with untracked files")
        
        # Now modify a tracked file by touching it
        trading_script = project_root / "trading_script.py"
        original_mtime = trading_script.stat().st_mtime
        
        # Touch the file to update its modification time
        trading_script.touch()
        
        # Wait a moment to ensure timestamp difference
        time.sleep(0.1)
        
        try:
            # Should fail now
            assert not verify_script_integrity(project_root), "Should fail after modifying tracked file"
            print("✅ Integrity check fails after modifying tracked file")
        finally:
            # Restore original modification time
            trading_script.touch()
            os.utime(trading_script, (original_mtime, original_mtime))
    
    finally:
        # Cleanup temp file
        temp_file.unlink()


def test_require_integrity():
    """Test the require_script_integrity function."""
    print("\nTesting require_script_integrity...")
    
    # Initialize launch time
    initialize_launch_time()
    
    # Should pass initially
    try:
        require_script_integrity(project_root)
        print("✅ require_script_integrity passes initially")
    except ScriptIntegrityError:
        print("❌ require_script_integrity failed initially")
        return
    
    # Modify a tracked file
    trading_script = project_root / "trading_script.py"
    original_mtime = trading_script.stat().st_mtime
    
    try:
        # Touch the file to update its modification time
        trading_script.touch()
        time.sleep(0.1)
        
        # Should fail now
        try:
            require_script_integrity(project_root)
            print("❌ require_script_integrity should have failed")
        except ScriptIntegrityError:
            print("✅ require_script_integrity correctly fails after modification")
    
    finally:
        # Restore original modification time
        trading_script.touch()
        os.utime(trading_script, (original_mtime, original_mtime))


def main():
    """Run all timestamp verification tests."""
    print("🧪 Testing Timestamp-Based Integrity Verification")
    print("=" * 60)
    
    try:
        test_launch_time_initialization()
        test_python_file_detection()
        test_integrity_verification()
        test_require_integrity()
        
        print("\n" + "=" * 60)
        print("✅ All timestamp verification tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
