"""Tests for update manager orchestration"""

from unittest.mock import Mock, patch, MagicMock, call
import tempfile
from pathlib import Path
import pytest
import sys

# Mock tkinter if not available (headless environments)
if 'tkinter' not in sys.modules:
    sys.modules['tkinter'] = Mock()
    sys.modules['tkinter.ttk'] = Mock()
    sys.modules['tkinter.scrolledtext'] = Mock()

from src.update_manager import UpdateManager


class TestUpdateManager:
    """Tests for UpdateManager class"""

    def test_initialization(self):
        """Test that UpdateManager initializes with config"""
        config = {
            'check_on_startup': True,
            'auto_download': False,
            'include_prereleases': False
        }

        manager = UpdateManager(config)

        assert manager.config == config
        assert manager.check_on_startup is True

    def test_check_for_updates_async(self):
        """Test async update checking in background thread"""
        config = {'check_on_startup': True}
        manager = UpdateManager(config)

        callback_called = []

        def callback(update_info):
            callback_called.append(update_info)

        # Mock the update checker
        with patch.object(manager, 'checker') as mock_checker:
            mock_checker.check_for_update.return_value = {
                'available': True,
                'latest_version': 'v1.1.0'
            }

            manager.check_for_updates_async(callback)

            # Give thread time to complete
            import time
            time.sleep(0.5)

            # Callback should have been called
            assert len(callback_called) > 0

    @patch('src.update_manager.UpdateDialog')
    @patch('src.update_manager.UpdateChecker')
    def test_handle_update_available(self, mock_checker_class, mock_dialog_class):
        """Test handling when update is available"""
        config = {}
        manager = UpdateManager(config)

        # Mock dialog to return 'install'
        mock_dialog = Mock()
        mock_dialog.show.return_value = 'install'
        mock_dialog_class.return_value = mock_dialog

        update_info = {
            'available': True,
            'latest_version': 'v1.1.0',
            'current_version': '1.0.0',
            'changelog': 'Release notes',
            'download_url': 'https://github.com/test/test.exe'
        }

        # Mock download_and_install
        with patch.object(manager, 'download_and_install') as mock_download:
            mock_download.return_value = True

            manager.handle_update_available(update_info)

            # Dialog should have been shown
            mock_dialog_class.assert_called_once_with(update_info)
            mock_dialog.show.assert_called_once()

            # Download should have been called
            mock_download.assert_called_once_with(update_info)

    @patch('src.update_manager.UpdateDialog')
    @patch('src.update_manager.UpdateChecker')
    def test_handle_no_update_available(self, mock_checker_class, mock_dialog_class):
        """Test handling when no update is available"""
        config = {}
        manager = UpdateManager(config)

        update_info = {
            'available': False,
            'latest_version': 'v1.0.0',
            'current_version': '1.0.0'
        }

        manager.handle_update_available(update_info)

        # Dialog should not be shown
        mock_dialog_class.assert_not_called()

    @patch('src.update_manager.UpdateChecker')
    def test_download_and_install(self, mock_checker_class):
        """Test download and install workflow"""
        config = {}
        manager = UpdateManager(config)

        # Mock checker download
        mock_checker = Mock()
        mock_checker.download_update.return_value = True
        mock_checker.verify_checksum.return_value = True
        manager.checker = mock_checker

        update_info = {
            'download_url': 'https://github.com/test/test.exe',
            'latest_version': 'v1.1.0'
        }

        # Mock subprocess to avoid actually launching updater
        with patch('subprocess.Popen') as mock_popen:
            with patch('sys.exit') as mock_exit:
                result = manager.download_and_install(update_info)

                # Download should have been called
                assert mock_checker.download_update.called

    @patch('src.update_manager.UpdateChecker')
    def test_skip_version(self, mock_checker_class):
        """Test skipping a version"""
        config = {}
        manager = UpdateManager(config)

        manager.skip_version('v1.1.0')

        # Version should be in skipped list
        assert 'v1.1.0' in manager.skipped_versions

    @patch('src.update_manager.UpdateChecker')
    def test_skip_version_not_shown_again(self, mock_checker_class):
        """Test that skipped version is not shown again"""
        config = {}
        manager = UpdateManager(config)

        # Skip version
        manager.skip_version('v1.1.0')

        # Check if should show update
        assert manager.should_show_update('v1.1.0') is False
        assert manager.should_show_update('v1.2.0') is True

    @patch('src.update_manager.UpdateChecker')
    def test_update_check_disabled(self, mock_checker_class):
        """Test that update check respects settings"""
        config = {'check_on_startup': False}
        manager = UpdateManager(config)

        assert manager.should_check_for_updates() is False

        config2 = {'check_on_startup': True}
        manager2 = UpdateManager(config2)

        assert manager2.should_check_for_updates() is True

    @patch('src.update_manager.UpdateChecker')
    def test_update_check_offline(self, mock_checker_class):
        """Test handling when offline (network error)"""
        config = {}
        manager = UpdateManager(config)

        # Mock checker to return None (network error)
        mock_checker = Mock()
        mock_checker.check_for_update.return_value = None
        manager.checker = mock_checker

        # Should not raise error
        callback_called = []

        def callback(update_info):
            callback_called.append(update_info)

        manager.check_for_updates_async(callback)

        # Give thread time
        import time
        time.sleep(0.5)

        # Callback might not be called or called with None
        # Either way, no error should be raised

    @patch('src.update_manager.UpdateDialog')
    @patch('src.update_manager.UpdateChecker')
    def test_download_failure_handling(self, mock_checker_class, mock_dialog_class):
        """Test handling of download failure"""
        config = {}
        manager = UpdateManager(config)

        # Mock checker to fail download
        mock_checker = Mock()
        mock_checker.download_update.return_value = False
        manager.checker = mock_checker

        update_info = {
            'download_url': 'https://github.com/test/test.exe',
            'latest_version': 'v1.1.0'
        }

        result = manager.download_and_install(update_info)

        # Should return False
        assert result is False

    @patch('src.update_manager.UpdateChecker')
    def test_checksum_failure_handling(self, mock_checker_class):
        """Test handling of checksum verification failure"""
        config = {}
        manager = UpdateManager(config)

        # Mock checker: download succeeds but checksum fails
        mock_checker = Mock()
        mock_checker.download_update.return_value = True
        mock_checker.verify_checksum.return_value = False
        manager.checker = mock_checker

        update_info = {
            'download_url': 'https://github.com/test/test.exe',
            'latest_version': 'v1.1.0',
            'checksum': 'abc123'  # Include checksum to trigger verification
        }

        result = manager.download_and_install(update_info)

        # Should return False (failed verification)
        assert result is False

    @patch('src.update_manager.UpdateChecker')
    def test_launch_updater_script(self, mock_checker_class):
        """Test that updater script is launched correctly"""
        config = {}
        manager = UpdateManager(config)

        # Mock download
        mock_checker = Mock()
        mock_checker.download_update.return_value = True
        manager.checker = mock_checker

        update_info = {
            'download_url': 'https://github.com/test/test.exe',
            'latest_version': 'v1.1.0'
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch('subprocess.Popen') as mock_popen:
                with patch('sys.exit'):
                    with patch('sys.executable', '/usr/bin/python'):
                        manager.download_and_install(update_info)

                        # Popen should have been called with updater.py
                        assert mock_popen.called

    @patch('src.update_manager.UpdateChecker')
    def test_update_settings_persistence(self, mock_checker_class):
        """Test that update settings are persisted"""
        config = {'check_on_startup': True}
        manager = UpdateManager(config)

        # Skip a version
        manager.skip_version('v1.1.0')

        # Get updated config
        updated_config = manager.get_config()

        # Should include skipped versions
        assert 'skipped_versions' in updated_config
        assert 'v1.1.0' in updated_config['skipped_versions']


class TestUpdateManagerIntegration:
    """Integration tests for UpdateManager"""

    @patch('src.update_manager.UpdateDialog')
    @patch('src.update_manager.UpdateChecker')
    def test_full_update_workflow_install(self, mock_checker_class, mock_dialog_class):
        """Test complete update workflow when user chooses install"""
        config = {'check_on_startup': True}

        # Mock checker
        mock_checker = Mock()
        mock_checker.check_for_update.return_value = {
            'available': True,
            'latest_version': 'v1.1.0',
            'current_version': '1.0.0',
            'changelog': 'New features',
            'download_url': 'https://github.com/test/test.exe'
        }
        mock_checker.download_update.return_value = True
        mock_checker_class.return_value = mock_checker

        # Mock dialog to choose install
        mock_dialog = Mock()
        mock_dialog.show.return_value = 'install'
        mock_dialog_class.return_value = mock_dialog

        manager = UpdateManager(config)
        manager.checker = mock_checker

        # Mock subprocess and exit
        with patch('subprocess.Popen'):
            with patch('sys.exit'):
                # Simulate update check
                update_info = mock_checker.check_for_update('1.0.0')
                manager.handle_update_available(update_info)

                # Dialog should have been shown
                mock_dialog.show.assert_called_once()

    @patch('src.update_manager.UpdateDialog')
    @patch('src.update_manager.UpdateChecker')
    def test_full_update_workflow_skip(self, mock_checker_class, mock_dialog_class):
        """Test complete update workflow when user skips"""
        config = {'check_on_startup': True}

        # Mock checker
        mock_checker = Mock()
        mock_checker.check_for_update.return_value = {
            'available': True,
            'latest_version': 'v1.1.0',
            'current_version': '1.0.0',
            'changelog': 'New features',
            'download_url': 'https://github.com/test/test.exe'
        }
        mock_checker_class.return_value = mock_checker

        # Mock dialog to choose skip
        mock_dialog = Mock()
        mock_dialog.show.return_value = 'skip'
        mock_dialog_class.return_value = mock_dialog

        manager = UpdateManager(config)

        update_info = mock_checker.check_for_update('1.0.0')
        manager.handle_update_available(update_info)

        # Version should be skipped
        assert 'v1.1.0' in manager.skipped_versions
