"""Tests for update UI components"""

from unittest.mock import Mock, patch, MagicMock
import pytest
import sys

# Mock tkinter if not available (headless environments)
if 'tkinter' not in sys.modules:
    sys.modules['tkinter'] = Mock()
    sys.modules['tkinter.ttk'] = Mock()
    sys.modules['tkinter.scrolledtext'] = Mock()

from src.update_ui import UpdateDialog, UpdateNotification


class TestUpdateDialog:
    """Tests for UpdateDialog class"""

    @patch('tkinter.Tk')
    def test_update_dialog_creation(self, mock_tk):
        """Test that dialog is created with update information"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': '## What\'s New\n- Feature 1\n- Bug fix 2',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        assert dialog.update_info == update_info
        assert dialog.result is None

    @patch('tkinter.Tk')
    @patch('tkinter.messagebox')
    def test_update_dialog_install_clicked(self, mock_messagebox, mock_tk):
        """Test that clicking Install returns 'install'"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Simulate clicking Install button
        dialog.on_install()

        assert dialog.result == 'install'

    @patch('tkinter.Tk')
    def test_update_dialog_skip_clicked(self, mock_tk):
        """Test that clicking Skip returns 'skip'"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Simulate clicking Skip button
        dialog.on_skip()

        assert dialog.result == 'skip'

    @patch('tkinter.Tk')
    def test_update_dialog_later_clicked(self, mock_tk):
        """Test that clicking Remind Later returns 'later'"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Simulate clicking Remind Later button
        dialog.on_later()

        assert dialog.result == 'later'

    @patch('tkinter.Tk')
    def test_update_dialog_displays_version(self, mock_tk):
        """Test that dialog displays version numbers"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Verify version info is stored
        assert '1.0.0' in dialog.update_info['current_version']
        assert 'v1.1.0' in dialog.update_info['latest_version']

    @patch('tkinter.Tk')
    def test_update_dialog_displays_changelog(self, mock_tk):
        """Test that dialog displays release notes/changelog"""
        changelog = '## What\'s New\n- Feature 1\n- Bug fix 2\n- Performance improvements'
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': changelog,
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Verify changelog is stored
        assert changelog in dialog.update_info['changelog']
        assert 'Feature 1' in dialog.update_info['changelog']

    @patch('tkinter.Tk')
    def test_update_dialog_progress_bar(self, mock_tk):
        """Test that progress bar can be updated"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Test progress updates (should not raise errors)
        dialog.set_progress(0.0)
        dialog.set_progress(0.5)
        dialog.set_progress(1.0)

        # Progress should be stored
        assert hasattr(dialog, 'progress')

    @patch('tkinter.Tk')
    def test_update_dialog_window_title(self, mock_tk):
        """Test that dialog has appropriate window title"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        dialog = UpdateDialog(update_info)

        # Should have a title stored
        assert hasattr(dialog, 'title')
        assert 'update' in dialog.title.lower() or 'available' in dialog.title.lower()


class TestUpdateNotification:
    """Tests for UpdateNotification class"""

    def test_show_update_available(self):
        """Test showing update available notification"""
        mock_tray_icon = Mock()

        notification = UpdateNotification(mock_tray_icon)
        notification.show_update_available('v1.1.0')

        # Should have called show_notification or similar
        assert notification.last_version == 'v1.1.0'

    def test_notification_displays_version(self):
        """Test that notification displays version number"""
        mock_tray_icon = Mock()

        notification = UpdateNotification(mock_tray_icon)
        notification.show_update_available('v2.0.0')

        assert notification.last_version == 'v2.0.0'

    def test_notification_without_tray_icon(self):
        """Test that notification handles missing tray icon gracefully"""
        # No tray icon provided
        notification = UpdateNotification(None)

        # Should not raise error
        notification.show_update_available('v1.1.0')

        assert notification.last_version == 'v1.1.0'


class TestUpdateUIIntegration:
    """Integration tests for update UI components"""

    @patch('tkinter.Tk')
    def test_dialog_and_notification_together(self, mock_tk):
        """Test that dialog and notification can work together"""
        update_info = {
            'current_version': '1.0.0',
            'latest_version': 'v1.1.0',
            'changelog': 'Release notes',
            'release_date': '2025-11-20T10:00:00Z'
        }

        # Create dialog
        dialog = UpdateDialog(update_info)

        # Create notification
        mock_tray = Mock()
        notification = UpdateNotification(mock_tray)

        # Show notification
        notification.show_update_available('v1.1.0')

        # Both should work without conflicts
        assert dialog.update_info == update_info
        assert notification.last_version == 'v1.1.0'
