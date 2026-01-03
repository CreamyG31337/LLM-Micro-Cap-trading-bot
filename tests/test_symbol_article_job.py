"""
Integration tests for symbol article scraper job.

Tests full job execution with mocked dependencies.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / 'web_dashboard'))


class TestSymbolArticleJob(unittest.TestCase):
    """Test the symbol article scraper job."""
    
    @patch('scheduler.jobs_symbol_articles.SupabaseClient')
    @patch('scheduler.jobs_symbol_articles.scrape_symbol_articles')
    @patch('scheduler.jobs_symbol_articles.extract_article_content')
    @patch('scheduler.jobs_symbol_articles.ResearchRepository')
    @patch('scheduler.jobs_symbol_articles.get_ollama_client')
    def test_job_execution_with_mock_data(self, mock_ollama, mock_repo, mock_extract, mock_scrape, mock_supabase):
        """Test job execution with mocked data."""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_supabase.return_value = mock_client_instance
        
        # Mock fund data
        mock_client_instance.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {'name': 'Test Fund'}
        ]
        
        # Mock position data
        mock_positions = MagicMock()
        mock_positions.data = [
            {'ticker': 'STLD', 'company': 'Steel Dynamics Inc', 'fund': 'Test Fund'}
        ]
        mock_client_instance.supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_positions
        
        # Mock article URLs
        mock_scrape.return_value = [
            'https://seekingalpha.com/article/1234567-test-article',
            'https://seekingalpha.com/article/1234568-another-article',
        ]
        
        # Mock article extraction
        mock_extract.return_value = {
            'title': 'Test Article Title',
            'content': 'This is test article content that is long enough to pass validation.',
            'published_at': None,
            'source': 'seekingalpha.com',
            'success': True,
            'error': None
        }
        
        # Mock repository
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_repo_instance.article_exists.return_value = False
        mock_repo_instance.save_article.return_value = 1
        
        # Mock Ollama (optional)
        mock_ollama.return_value = None
        
        # Import and run job
        try:
            from scheduler.jobs_symbol_articles import seeking_alpha_symbol_job
            seeking_alpha_symbol_job()
            
            # Verify article extraction was called
            self.assertGreater(mock_extract.call_count, 0)
            
            # Verify repository save was called
            self.assertGreater(mock_repo_instance.save_article.call_count, 0)
        except ImportError as e:
            self.skipTest(f"Job module not available: {e}")
    
    @patch('scheduler.jobs_symbol_articles.SupabaseClient')
    def test_job_handles_no_funds(self, mock_supabase):
        """Test job handles case when no production funds exist."""
        mock_client_instance = MagicMock()
        mock_supabase.return_value = mock_client_instance
        
        # Mock empty fund data
        mock_client_instance.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        try:
            from scheduler.jobs_symbol_articles import seeking_alpha_symbol_job
            # Should complete without error
            seeking_alpha_symbol_job()
        except ImportError as e:
            self.skipTest(f"Job module not available: {e}")
    
    @patch('scheduler.jobs_symbol_articles.SupabaseClient')
    @patch('scheduler.jobs_symbol_articles.scrape_symbol_articles')
    def test_job_handles_no_articles(self, mock_scrape, mock_supabase):
        """Test job handles case when no articles found for ticker."""
        mock_client_instance = MagicMock()
        mock_supabase.return_value = mock_client_instance
        
        # Mock fund and position data
        mock_client_instance.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {'name': 'Test Fund'}
        ]
        mock_positions = MagicMock()
        mock_positions.data = [
            {'ticker': 'STLD', 'company': 'Steel Dynamics Inc', 'fund': 'Test Fund'}
        ]
        mock_client_instance.supabase.table.return_value.select.return_value.in_.return_value.execute.return_value = mock_positions
        
        # Mock no articles found
        mock_scrape.return_value = []
        
        try:
            from scheduler.jobs_symbol_articles import seeking_alpha_symbol_job
            # Should complete without error
            seeking_alpha_symbol_job()
        except ImportError as e:
            self.skipTest(f"Job module not available: {e}")
    
    def test_paywall_detection(self):
        """Test paywall content detection."""
        try:
            from symbol_article_scraper import is_paywalled_content
            
            # Test paywalled content
            paywalled = "Create a free account to read the full article"
            self.assertTrue(is_paywalled_content(paywalled))
            
            # Test normal content
            normal = "This is a normal article with substantial content that discusses various topics in detail."
            self.assertFalse(is_paywalled_content(normal))
            
            # Test short content with paywall phrase
            short_paywall = "Sign up for free to continue reading"
            self.assertTrue(is_paywalled_content(short_paywall))
        except ImportError:
            self.skipTest("symbol_article_scraper module not available")


if __name__ == '__main__':
    unittest.main()

