"""Tests for the CLI module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from hermes.cli import main


class TestCLIMain:
    """Test the main CLI function."""
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes'])
    def test_cli_main_default_args(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI with default arguments."""
        mock_run_pipeline.return_value = Path("/fake/path/digest.md")
        
        # Call main function
        main()
        
        mock_setup_logging.assert_called_once()
        mock_run_pipeline.assert_called_once_with("markdown")
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes', '--format', 'html'])
    def test_cli_main_html_format(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI with HTML format argument."""
        mock_run_pipeline.return_value = Path("/fake/path/digest.html")
        
        main()
        
        mock_run_pipeline.assert_called_once_with("html")
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes', '--format', 'json'])
    def test_cli_main_json_format(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI with JSON format argument."""
        mock_run_pipeline.return_value = Path("/fake/path/digest.json")
        
        main()
        
        mock_run_pipeline.assert_called_once_with("json")
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes', '--verbose'])
    def test_cli_main_verbose_mode(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI with verbose flag."""
        mock_run_pipeline.return_value = Path("/fake/path/digest.md")
        
        main()
        
        mock_setup_logging.assert_called_once()
        mock_run_pipeline.assert_called_once_with("markdown")
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes', '--format', 'html', '--verbose'])
    def test_cli_main_combined_args(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI with multiple arguments."""
        mock_run_pipeline.return_value = Path("/fake/path/digest.html")
        
        main()
        
        mock_setup_logging.assert_called_once()
        mock_run_pipeline.assert_called_once_with("html")
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes'])
    def test_cli_main_pipeline_failure(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI when pipeline returns None (failure)."""
        mock_run_pipeline.return_value = None
        
        # Should not raise an exception
        main()
        
        mock_run_pipeline.assert_called_once()
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes'])
    def test_cli_main_pipeline_exception(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI when pipeline raises an exception."""
        mock_run_pipeline.side_effect = Exception("Pipeline failed")
        
        # Should handle the exception gracefully
        with pytest.raises(Exception, match="Pipeline failed"):
            main()


class TestCLIArgumentParsing:
    """Test CLI argument parsing scenarios."""
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    def test_cli_invalid_format(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI with invalid format argument."""
        with patch('sys.argv', ['hermes', '--format', 'invalid']):
            # This should be handled by argparse or the pipeline
            try:
                main()
            except SystemExit:
                # argparse exits on invalid choice
                pass
            except Exception as e:
                # Or pipeline raises exception for invalid format
                assert "format" in str(e).lower() or "invalid" in str(e).lower()
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes', '--help'])
    def test_cli_help_flag(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI help flag."""
        with pytest.raises(SystemExit) as exc_info:
            main()
        
        # Help should exit with code 0
        assert exc_info.value.code == 0
        # Pipeline should not be called when showing help
        mock_run_pipeline.assert_not_called()


class TestCLIOutput:
    """Test CLI output and user feedback."""
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('builtins.print')
    @patch('sys.argv', ['hermes'])
    def test_cli_success_output(self, mock_print, mock_setup_logging, mock_run_pipeline):
        """Test CLI output on successful execution."""
        digest_path = Path("/fake/path/digest.md")
        mock_run_pipeline.return_value = digest_path
        
        main()
        
        # Should print success message
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("digest.md" in call for call in print_calls)
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('builtins.print')
    @patch('sys.argv', ['hermes'])
    def test_cli_failure_output(self, mock_print, mock_setup_logging, mock_run_pipeline):
        """Test CLI output on pipeline failure."""
        mock_run_pipeline.return_value = None
        
        main()
        
        # Should print failure message
        mock_print.assert_called()
        print_calls = [str(call) for call in mock_print.call_args_list]
        assert any("failed" in call.lower() or "error" in call.lower() for call in print_calls)


class TestCLILogging:
    """Test CLI logging configuration."""
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.logging.basicConfig')
    @patch('sys.argv', ['hermes', '--verbose'])
    def test_cli_verbose_logging(self, mock_basic_config, mock_run_pipeline):
        """Test that verbose flag configures logging appropriately."""
        mock_run_pipeline.return_value = Path("/fake/digest.md")
        
        main()
        
        # Check that logging was configured (setup_logging should be called)
        mock_basic_config.assert_called()
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('sys.argv', ['hermes'])
    def test_cli_normal_logging(self, mock_setup_logging, mock_run_pipeline):
        """Test normal logging configuration."""
        mock_run_pipeline.return_value = Path("/fake/digest.md")
        
        main()
        
        mock_setup_logging.assert_called_once()


class TestCLIIntegration:
    """Integration tests for CLI functionality."""
    
    @patch('hermes.main.write_digest')
    @patch('hermes.main.fetch_articles')
    def test_cli_end_to_end_simulation(self, mock_fetch, mock_write, temp_output_dir):
        """Test CLI in an end-to-end simulation."""
        from hermes.fetcher import NewsArticle
        
        # Mock the pipeline components
        sample_articles = [
            NewsArticle(
                title="Test CLI Article",
                summary="CLI test summary", 
                link="https://example.com/cli-test",
                content="CLI test content about technology"
            )
        ]
        
        mock_fetch.return_value = sample_articles
        mock_write.return_value = temp_output_dir / "cli-test-digest.md"
        
        with patch('sys.argv', ['hermes', '--format', 'markdown']):
            with patch('builtins.print') as mock_print:
                main()
                
                # Verify success output
                mock_print.assert_called()
                print_calls = [str(call) for call in mock_print.call_args_list]
                assert any("cli-test-digest.md" in call for call in print_calls)
    
    def test_cli_module_imports(self):
        """Test that CLI module imports work correctly."""
        # These imports should work without errors
        from hermes.cli import main
        from hermes.main import run_pipeline, setup_logging
        
        assert callable(main)
        assert callable(run_pipeline)
        assert callable(setup_logging)


class TestCLIErrorHandling:
    """Test CLI error handling scenarios."""
    
    @patch('hermes.cli.setup_logging')
    def test_cli_handles_import_errors(self, mock_setup_logging):
        """Test CLI handles import errors gracefully."""
        with patch('hermes.cli.run_pipeline', side_effect=ImportError("Missing dependency")):
            with patch('sys.argv', ['hermes']):
                with pytest.raises(ImportError):
                    main()
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    def test_cli_handles_keyboard_interrupt(self, mock_setup_logging, mock_run_pipeline):
        """Test CLI handles KeyboardInterrupt (Ctrl+C) gracefully."""
        mock_run_pipeline.side_effect = KeyboardInterrupt()
        
        with patch('sys.argv', ['hermes']):
            with pytest.raises(KeyboardInterrupt):
                main()
    
    @patch('hermes.cli.run_pipeline')
    @patch('hermes.cli.setup_logging')
    @patch('builtins.print')
    def test_cli_handles_general_exceptions(self, mock_print, mock_setup_logging, mock_run_pipeline):
        """Test CLI handles general exceptions."""
        mock_run_pipeline.side_effect = Exception("Unexpected error")
        
        with patch('sys.argv', ['hermes']):
            with pytest.raises(Exception, match="Unexpected error"):
                main()
