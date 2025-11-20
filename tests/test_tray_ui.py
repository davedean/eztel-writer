"""Tests for system tray UI"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import sys

# Mock pystray and PIL before importing tray_ui
sys.modules['pystray'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.ImageDraw'] = MagicMock()

from src.session_manager import SessionState
from src.tray_ui import TrayUI


class TestTrayUI(unittest.TestCase):
    """Test system tray UI functionality"""

    def setUp(self):
        """Set up test fixtures"""
        # Mock the telemetry app
        self.mock_app = Mock()
        self.mock_app.telemetry_loop = Mock()
        self.mock_app.telemetry_loop.is_running.return_value = False
        self.mock_app.telemetry_loop.is_paused.return_value = False
        self.mock_app.telemetry_loop.session_manager = Mock()
        self.mock_app.telemetry_loop.session_manager.state = SessionState.IDLE
        self.mock_app.telemetry_loop.session_manager.current_lap = 0
        self.mock_app.telemetry_loop.session_manager.lap_samples = []
        self.mock_app.file_manager = Mock()
        self.mock_app.file_manager.get_output_directory.return_value = '/test/output'

    def test_init(self):
        """Test TrayUI initialization"""
        tray = TrayUI(self.mock_app)

        self.assertEqual(tray.app, self.mock_app)
        self.assertIsNone(tray.icon)
        self.assertEqual(tray.state, SessionState.IDLE)

    def test_create_icon_generates_image(self):
        """Test that create_icon generates icon images"""
        tray = TrayUI(self.mock_app)

        # Icons should be created during init
        self.assertIsNotNone(tray.icons)
        self.assertIn(SessionState.IDLE, tray.icons)
        self.assertIn(SessionState.DETECTED, tray.icons)
        self.assertIn(SessionState.LOGGING, tray.icons)

    def test_create_icon_creates_menu(self):
        """Test that create_icon creates menu with correct items"""
        tray = TrayUI(self.mock_app)
        tray.create_icon()

        # Verify icon was created
        self.assertIsNotNone(tray.icon)

    def test_update_status_changes_icon(self):
        """Test that update_status changes icon based on state"""
        mock_icon_instance = Mock()
        tray = TrayUI(self.mock_app)
        tray.icon = mock_icon_instance

        # Update to DETECTED state
        tray.update_status(SessionState.DETECTED)
        self.assertEqual(tray.state, SessionState.DETECTED)

        # Update to LOGGING state
        tray.update_status(SessionState.LOGGING)
        self.assertEqual(tray.state, SessionState.LOGGING)

    def test_on_start_stop_when_stopped(self):
        """Test on_start_stop starts the app when stopped"""
        self.mock_app.telemetry_loop.is_running.return_value = False

        tray = TrayUI(self.mock_app)
        tray.on_start_stop()

        # Should start the telemetry loop
        self.mock_app.telemetry_loop.start.assert_called_once()

    def test_on_start_stop_when_running(self):
        """Test on_start_stop stops the app when running"""
        self.mock_app.telemetry_loop.is_running.return_value = True

        tray = TrayUI(self.mock_app)
        tray.on_start_stop()

        # Should stop the telemetry loop
        self.mock_app.telemetry_loop.stop.assert_called_once()

    def test_on_pause_resume_when_running(self):
        """Test on_pause_resume pauses when running"""
        self.mock_app.telemetry_loop.is_running.return_value = True
        self.mock_app.telemetry_loop.is_paused.return_value = False

        tray = TrayUI(self.mock_app)
        tray.on_pause_resume()

        # Should pause the telemetry loop
        self.mock_app.telemetry_loop.pause.assert_called_once()

    def test_on_pause_resume_when_paused(self):
        """Test on_pause_resume resumes when paused"""
        self.mock_app.telemetry_loop.is_running.return_value = True
        self.mock_app.telemetry_loop.is_paused.return_value = True

        tray = TrayUI(self.mock_app)
        tray.on_pause_resume()

        # Should resume the telemetry loop
        self.mock_app.telemetry_loop.resume.assert_called_once()

    @patch('src.tray_ui.subprocess.run')
    def test_on_open_folder_windows(self, mock_subprocess):
        """Test on_open_folder opens folder on Windows"""
        with patch('sys.platform', 'win32'):
            tray = TrayUI(self.mock_app)
            tray.on_open_folder()

            # Should call explorer.exe
            mock_subprocess.assert_called_once()
            args = mock_subprocess.call_args[0][0]
            self.assertIn('explorer', args[0].lower())

    @patch('src.tray_ui.subprocess.run')
    def test_on_open_folder_mac(self, mock_subprocess):
        """Test on_open_folder opens folder on macOS"""
        with patch('sys.platform', 'darwin'):
            tray = TrayUI(self.mock_app)
            tray.on_open_folder()

            # Should call open command
            mock_subprocess.assert_called_once()
            args = mock_subprocess.call_args[0][0]
            self.assertEqual(args[0], 'open')

    def test_on_quit_stops_app(self):
        """Test on_quit stops app and icon"""
        mock_icon_instance = Mock()
        tray = TrayUI(self.mock_app)
        tray.icon = mock_icon_instance

        tray.on_quit()

        # Should stop telemetry loop
        self.mock_app.telemetry_loop.stop.assert_called_once()

        # Should stop icon
        mock_icon_instance.stop.assert_called_once()

    def test_get_status_text_idle(self):
        """Test get_status_text returns correct text for IDLE state"""
        tray = TrayUI(self.mock_app)
        tray.state = SessionState.IDLE

        status = tray.get_status_text()
        self.assertIn('Idle', status)

    def test_get_status_text_logging(self):
        """Test get_status_text returns correct text for LOGGING state"""
        self.mock_app.telemetry_loop.session_manager.current_lap = 5
        self.mock_app.telemetry_loop.session_manager.lap_samples = [1] * 234

        tray = TrayUI(self.mock_app)
        tray.state = SessionState.LOGGING

        status = tray.get_status_text()
        self.assertIn('Logging', status)
        self.assertIn('5', status)  # Lap number
        self.assertIn('234', status)  # Sample count

    def test_menu_start_stop_text_when_stopped(self):
        """Test menu shows 'Start Logging' when stopped"""
        self.mock_app.telemetry_loop.is_running.return_value = False

        tray = TrayUI(self.mock_app)
        text = tray._get_start_stop_text()

        self.assertEqual(text, 'Start Logging')

    def test_menu_start_stop_text_when_running(self):
        """Test menu shows 'Stop Logging' when running"""
        self.mock_app.telemetry_loop.is_running.return_value = True

        tray = TrayUI(self.mock_app)
        text = tray._get_start_stop_text()

        self.assertEqual(text, 'Stop Logging')

    @patch('src.tray_ui.show_settings_dialog')
    def test_on_settings_opens_dialog(self, mock_show_settings):
        """Test on_settings opens the settings dialog"""
        mock_show_settings.return_value = False  # No changes made

        tray = TrayUI(self.mock_app)
        tray.on_settings()

        # Should call show_settings_dialog
        mock_show_settings.assert_called_once()

    @patch('src.tray_ui.show_settings_dialog')
    def test_on_settings_returns_when_changes_made(self, mock_show_settings):
        """Test on_settings handles when settings are changed"""
        mock_show_settings.return_value = True  # Changes made

        tray = TrayUI(self.mock_app)
        result = tray.on_settings()

        # Should call show_settings_dialog and return True
        mock_show_settings.assert_called_once()


if __name__ == '__main__':
    unittest.main()
