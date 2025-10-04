"""
Tests for fund management functionality.

Tests cover fund creation, switching, configuration management,
and data directory handling for the new fund-based structure.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import json
import sys

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.fund_manager import FundManager, get_fund_manager, invalidate_fund_manager_cache
from utils.fund_ui import FundUI
from config.settings import get_settings


class TestFundManager(unittest.TestCase):
    """Test the FundManager class functionality."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fund_manager = FundManager(base_data_dir=str(self.test_dir))
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_create_fund(self):
        """Test creating a new fund."""
        fund_name = "Test Fund"
        fund_type = "investment"
        
        result = self.fund_manager.create_fund(fund_name, fund_type)
        
        self.assertTrue(result)
        self.assertIn(fund_name, self.fund_manager.get_available_funds())
        
        # Check that fund directory was created
        fund_dir = self.fund_manager.funds_dir / fund_name
        self.assertTrue(fund_dir.exists())
        
        # Check that fund config was created
        config_file = fund_dir / "fund_config.json"
        self.assertTrue(config_file.exists())
        
        # Check config content
        with open(config_file, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['fund']['name'], fund_name)
        self.assertEqual(config['fund']['fund_type'], fund_type)
    
    def test_create_fund_with_thesis(self):
        """Test creating a fund with thesis file."""
        fund_name = "RRSP Test"
        fund_type = "rrsp"
        
        result = self.fund_manager.create_fund(fund_name, fund_type)
        
        self.assertTrue(result)
        
        # Check that thesis file was created
        fund_dir = self.fund_manager.funds_dir / fund_name
        thesis_file = fund_dir / "thesis.yaml"
        self.assertTrue(thesis_file.exists())
    
    def test_switch_fund(self):
        """Test switching between funds."""
        # Create two funds
        self.fund_manager.create_fund("Fund A", "investment")
        self.fund_manager.create_fund("Fund B", "tfsa")

        # Switch to Fund A
        result = self.fund_manager.set_active_fund("Fund A")
        self.assertTrue(result)
        self.assertEqual(self.fund_manager.get_active_fund(), "Fund A")

        # Switch to Fund B
        result = self.fund_manager.set_active_fund("Fund B")
        self.assertTrue(result)
        self.assertEqual(self.fund_manager.get_active_fund(), "Fund B")

    def test_fund_manager_cache_invalidation(self):
        """Test that fund manager cache invalidation works correctly after switching funds.

        This test prevents regression of the issue where fund switching would update
        the local fund manager instance but not invalidate the global cache, causing
        other parts of the system to still see the old active fund.
        """
        # Use the global fund manager for this test
        global_fund_manager = get_fund_manager()

        # Get the current active fund before making changes
        original_active_fund = global_fund_manager.get_active_fund()

        # Create test funds if they don't exist
        available_funds = global_fund_manager.get_available_funds()
        if "Test Fund A" not in available_funds:
            global_fund_manager.create_fund("Test Fund A", "investment")
        if "Test Fund B" not in available_funds:
            global_fund_manager.create_fund("Test Fund B", "tfsa")

        # Set initial active fund
        global_fund_manager.set_active_fund("Test Fund A")
        self.assertEqual(global_fund_manager.get_active_fund(), "Test Fund A")

        # Switch to the other fund
        global_fund_manager.set_active_fund("Test Fund B")
        self.assertEqual(global_fund_manager.get_active_fund(), "Test Fund B")

        # Test cache invalidation function
        # The cache invalidation should force creation of a new fund manager instance
        # that reads the active fund from the file system
        invalidate_fund_manager_cache()

        # After invalidation, get_fund_manager() should return a new instance
        # that correctly reads the active fund from the file
        new_fund_manager = get_fund_manager()
        self.assertEqual(new_fund_manager.get_active_fund(), "Test Fund B")

        # Clean up - reset to original active fund for other tests
        try:
            if original_active_fund:
                global_fund_manager.set_active_fund(original_active_fund)
            else:
                # If no original fund, try to set to a known fund or clear it
                try:
                    global_fund_manager.set_active_fund("Project Chimera")
                except:
                    pass  # Ignore if fund doesn't exist
        except:
            pass  # Ignore cleanup errors

    def test_fund_manager_methods_exist(self):
        """Test that FundManager has all required methods for fund switching.

        This test prevents regression of missing method errors that could occur
        during fund switching operations.
        """
        # Test that required methods exist
        required_methods = [
            'set_active_fund',
            'get_active_fund',
            'create_fund',
            'get_available_funds',
            'get_fund_config',
            'get_fund_data_directory'
        ]

        for method_name in required_methods:
            self.assertTrue(hasattr(self.fund_manager, method_name),
                          f"FundManager missing required method: {method_name}")
            self.assertTrue(callable(getattr(self.fund_manager, method_name)),
                          f"FundManager method {method_name} is not callable")
    
    def test_get_fund_list(self):
        """Test getting list of available funds."""
        # Initially no funds
        funds = self.fund_manager.get_available_funds()
        self.assertEqual(len(funds), 0)
        
        # Create some funds
        self.fund_manager.create_fund("Fund 1", "investment")
        self.fund_manager.create_fund("Fund 2", "tfsa")
        self.fund_manager.create_fund("Fund 3", "rrsp")
        
        funds = self.fund_manager.get_available_funds()
        self.assertEqual(len(funds), 3)
        self.assertIn("Fund 1", funds)
        self.assertIn("Fund 2", funds)
        self.assertIn("Fund 3", funds)
    
    def test_fund_data_directory(self):
        """Test getting fund data directory."""
        fund_name = "Test Fund"
        self.fund_manager.create_fund(fund_name, "investment")
        
        data_dir = self.fund_manager.get_fund_data_directory()
        expected_dir = self.test_dir / "funds" / fund_name
        self.assertEqual(Path(data_dir), expected_dir)
    
    def test_fund_config_loading(self):
        """Test loading fund configuration."""
        fund_name = "Config Test"
        fund_type = "rrsp"
        
        self.fund_manager.create_fund(fund_name, fund_type)
        self.fund_manager.set_active_fund(fund_name)
        
        config = self.fund_manager.get_fund_config(fund_name)
        self.assertEqual(config['fund']['name'], fund_name)
        self.assertEqual(config['fund']['fund_type'], fund_type)
        self.assertIn('created_date', config['fund'])
        self.assertIn('data_directory', config['repository']['csv'])


class TestFundUI(unittest.TestCase):
    """Test the FundUI class functionality."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        # Create a test fund manager
        self.fund_manager = FundManager(base_data_dir=str(self.test_dir))
        # Mock the global fund manager to return our test instance
        import utils.fund_manager
        self.original_fund_manager = utils.fund_manager._fund_manager
        utils.fund_manager._fund_manager = self.fund_manager
        # Also mock the get_fund_manager function to return our test instance
        self.original_get_fund_manager = utils.fund_manager.get_fund_manager
        utils.fund_manager.get_fund_manager = lambda: self.fund_manager
        self.fund_ui = FundUI()
        
    def tearDown(self):
        """Clean up test environment."""
        # Restore original fund manager
        import utils.fund_manager
        utils.fund_manager._fund_manager = self.original_fund_manager
        utils.fund_manager.get_fund_manager = self.original_get_fund_manager
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_get_fund_list(self):
        """Test getting fund list through UI."""
        # Create some funds
        self.fund_ui.fund_manager.create_fund("UI Fund 1", "investment")
        self.fund_ui.fund_manager.create_fund("UI Fund 2", "tfsa")
        
        funds = self.fund_ui.fund_manager.get_available_funds()
        self.assertEqual(len(funds), 2)
        self.assertIn("UI Fund 1", funds)
        self.assertIn("UI Fund 2", funds)
    
    def test_get_current_fund_info(self):
        """Test getting current fund information."""
        # Create and set active fund
        self.fund_ui.fund_manager.create_fund("Current Fund", "investment")
        self.fund_ui.fund_manager.set_active_fund("Current Fund")
        
        # Debug: Check what the active fund actually is
        active_fund = self.fund_ui.fund_manager.get_active_fund()
        print(f"Debug: Active fund is: {active_fund}")
        
        # Import and patch the function to use our test fund manager
        from utils import fund_ui
        original_get_fund_manager = fund_ui.get_fund_manager
        fund_ui.get_fund_manager = lambda: self.fund_manager
        
        try:
            info = fund_ui.get_current_fund_info()
            
            print(f"Debug: get_current_fund_info returned: {info}")
            
            self.assertTrue(info['exists'])
            self.assertEqual(info['name'], "Current Fund")
            self.assertIn('data_directory', info)
            self.assertIn('config', info)
        finally:
            # Restore original function
            fund_ui.get_fund_manager = original_get_fund_manager


class TestFundIntegration(unittest.TestCase):
    """Test fund management integration with settings."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_settings_fund_integration(self):
        """Test that settings properly integrate with fund management."""
        # This test would require mocking the settings to use our test directory
        # For now, we'll just test that the fund manager can be imported
        from utils.fund_manager import get_fund_manager
        
        fund_manager = get_fund_manager()
        self.assertIsNotNone(fund_manager)
        self.assertTrue(hasattr(fund_manager, 'create_fund'))
        self.assertTrue(hasattr(fund_manager, 'get_active_fund'))
        self.assertTrue(hasattr(fund_manager, 'set_active_fund'))


class TestFundDataStructure(unittest.TestCase):
    """Test fund data structure and file organization."""
    
    def setUp(self):
        """Set up test environment with temporary directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fund_manager = FundManager(base_data_dir=str(self.test_dir))
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    def test_fund_directory_structure(self):
        """Test that fund directory has correct structure."""
        fund_name = "Structure Test"
        self.fund_manager.create_fund(fund_name, "investment")
        
        fund_dir = self.fund_manager.funds_dir / fund_name
        
        # Check required files exist
        required_files = [
            "fund_config.json",
            "thesis.yaml"
        ]
        
        for file_name in required_files:
            file_path = fund_dir / file_name
            self.assertTrue(file_path.exists(), f"Required file {file_name} not found")
    
    def test_fund_config_content(self):
        """Test fund configuration file content."""
        fund_name = "Config Content Test"
        fund_type = "tfsa"
        
        self.fund_manager.create_fund(fund_name, fund_type)
        
        config_file = self.fund_manager.funds_dir / fund_name / "fund_config.json"
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Check required fields
        required_sections = ['fund', 'repository', 'market_data', 'backup']
        required_fund_fields = ['name', 'fund_type', 'created_date', 'description']
        
        for section in required_sections:
            self.assertIn(section, config, f"Required section {section} missing from config")
        
        for field in required_fund_fields:
            self.assertIn(field, config['fund'], f"Required field {field} missing from fund config")
        
        # Check values
        self.assertEqual(config['fund']['name'], fund_name)
        self.assertEqual(config['fund']['fund_type'], fund_type)
        self.assertEqual(config['repository']['type'], 'csv')
    
    def test_thesis_file_content(self):
        """Test thesis file content for different fund types."""
        test_cases = [
            ("RRSP Test", "rrsp"),
            ("TFSA Test", "tfsa"),
            ("Investment Test", "investment")
        ]
        
        for fund_name, fund_type in test_cases:
            with self.subTest(fund_type=fund_type):
                self.fund_manager.create_fund(fund_name, fund_type)
                
                thesis_file = self.fund_manager.funds_dir / fund_name / "thesis.yaml"
                self.assertTrue(thesis_file.exists())
                
                # Check that thesis file has content
                content = thesis_file.read_text()
                self.assertGreater(len(content), 0)
                self.assertIn('guiding_thesis', content)


if __name__ == '__main__':
    unittest.main()
