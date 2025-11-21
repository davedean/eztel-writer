"""System tray UI for telemetry logger"""

import os
import sys
import subprocess
from typing import Any, Optional
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item
from src.session_manager import SessionState
from src.settings_ui import show_settings_dialog


class TrayUI:
    """
    System tray UI for telemetry logger

    Provides:
    - System tray icon with state indicators (gray/yellow/green)
    - Context menu for Start/Stop, Pause/Resume, Open Folder, Quit
    - Status tooltips
    - Integration with TelemetryApp
    """

    def __init__(self, app):
        """
        Initialize system tray UI

        Args:
            app: TelemetryApp instance to control
        """
        self.app = app
        self.icon = None
        self.state = SessionState.IDLE

        # Create icon images for different states
        self.icons = {
            SessionState.IDLE: self._create_icon_image('gray'),
            SessionState.DETECTED: self._create_icon_image('yellow'),
            SessionState.LOGGING: self._create_icon_image('green'),
            SessionState.PAUSED: self._create_icon_image('orange'),
            SessionState.ERROR: self._create_icon_image('red'),
        }

    def _create_icon_image(self, color: str) -> Image.Image:
        """
        Create icon image with specified color

        Args:
            color: Color name (gray, yellow, green, orange, red)

        Returns:
            PIL Image object
        """
        # Color map
        color_map = {
            'gray': (128, 128, 128),
            'yellow': (255, 215, 0),
            'green': (0, 200, 0),
            'orange': (255, 165, 0),
            'red': (255, 0, 0),
        }

        # Create 64x64 image with white background
        img = Image.new('RGB', (64, 64), color='white')
        draw = ImageDraw.Draw(img)

        # Draw colored circle
        rgb_color = color_map.get(color, (128, 128, 128))
        draw.ellipse([8, 8, 56, 56], fill=rgb_color)

        return img

    def create_icon(self):
        """Create system tray icon with menu"""
        menu = pystray.Menu(
            Item(
                self._get_start_stop_text,
                self.on_start_stop
            ),
            Item(
                self._get_pause_resume_text,
                self.on_pause_resume,
                enabled=self._is_pause_resume_enabled
            ),
            Item('Open Output Folder', self.on_open_folder),
            Item('Open Log File', self.on_open_log_file),
            pystray.Menu.SEPARATOR,
            Item('Settings...', self.on_settings),
            Item('Check for Updates...', self.on_check_for_updates),
            pystray.Menu.SEPARATOR,
            Item('Quit', self.on_quit)
        )

        self.icon = pystray.Icon(
            '1lap',
            self.icons[self.state],
            '1Lap',
            menu=menu
        )

    def start(self):
        """Start the tray icon (blocking)"""
        if self.icon is None:
            self.create_icon()

        # Run icon in main thread (required by pystray)
        self.icon.run()

    def update_status(self, state: SessionState, lap: int = 0, samples: int = 0):
        """
        Update tray icon and tooltip based on status

        Args:
            state: Current SessionState
            lap: Current lap number (for LOGGING state)
            samples: Number of samples buffered (for LOGGING state)
        """
        self.state = state

        if self.icon is not None:
            # Update icon image
            self.icon.icon = self.icons[state]

            # Update tooltip
            self.icon.title = self.get_status_text()

    def get_status_text(self) -> str:
        """
        Get status text for tooltip

        Returns:
            Status text string
        """
        if self.state == SessionState.IDLE:
            return '1Lap - Idle (Waiting for LMU)'
        elif self.state == SessionState.DETECTED:
            return '1Lap - Detected (LMU running)'
        elif self.state == SessionState.LOGGING:
            lap = self.app.telemetry_loop.session_manager.current_lap
            samples = len(self.app.telemetry_loop.session_manager.lap_samples)
            return f'1Lap - Logging Lap {lap} ({samples} samples)'
        elif self.state == SessionState.PAUSED:
            return '1Lap - Paused'
        elif self.state == SessionState.ERROR:
            return '1Lap - Error'
        else:
            return '1Lap'

    def on_start_stop(self):
        """Handle Start/Stop menu click"""
        if self.app.telemetry_loop.is_running():
            self.app.telemetry_loop.stop()
        else:
            self.app.telemetry_loop.start()

    def on_pause_resume(self):
        """Handle Pause/Resume menu click"""
        if self.app.telemetry_loop.is_paused():
            self.app.telemetry_loop.resume()
        else:
            self.app.telemetry_loop.pause()

    def on_open_folder(self):
        """Handle Open Output Folder menu click"""
        output_dir = self.app.file_manager.get_output_directory()

        # Open folder using platform-specific command
        if sys.platform == 'win32':
            subprocess.run(['explorer', output_dir])
        elif sys.platform == 'darwin':
            subprocess.run(['open', output_dir])
        else:  # Linux
            subprocess.run(['xdg-open', output_dir])

    def on_open_log_file(self):
        """Handle Open Log File menu click"""
        # Get log file path from tray_app module
        try:
            from tray_app import LOG_FILE_PATH
            log_file = LOG_FILE_PATH
        except ImportError:
            # Fallback: determine log file path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                app_dir = os.path.dirname(sys.executable)
            else:
                # Running as script
                app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            log_file = os.path.join(app_dir, 'telemetry_logger.log')

        # Check if log file exists
        if not os.path.exists(log_file):
            return  # Silently return if log file doesn't exist yet

        # Open log file using platform-specific command
        if sys.platform == 'win32':
            # On Windows, open with default text editor
            os.startfile(log_file)
        elif sys.platform == 'darwin':
            # On macOS, open with default text editor
            subprocess.run(['open', log_file])
        else:  # Linux
            # On Linux, open with default text editor
            subprocess.run(['xdg-open', log_file])

    def on_settings(self):
        """Handle Settings menu click"""
        # Show settings dialog (will block until closed)
        changed = show_settings_dialog()

        # Return True if settings were changed (for potential future use)
        return changed

    def on_check_for_updates(self):
        """Handle Check for Updates menu click"""
        if hasattr(self.app, 'check_for_updates_manual'):
            self.app.check_for_updates_manual()

    def on_quit(self):
        """Handle Quit menu click"""
        # Stop telemetry loop
        self.app.telemetry_loop.stop()

        # Stop tray icon
        if self.icon is not None:
            self.icon.stop()

    def _get_start_stop_text(self, item=None) -> str:
        """
        Get Start/Stop menu item text

        Returns:
            'Start Logging' or 'Stop Logging' depending on state
        """
        if self.app.telemetry_loop.is_running():
            return 'Stop Logging'
        else:
            return 'Start Logging'

    def _get_pause_resume_text(self, item=None) -> str:
        """
        Get Pause/Resume menu item text

        Returns:
            'Pause Logging' or 'Resume Logging' depending on state
        """
        if self.app.telemetry_loop.is_paused():
            return 'Resume Logging'
        else:
            return 'Pause Logging'

    def _is_pause_resume_enabled(self, item=None) -> bool:
        """
        Check if Pause/Resume menu item should be enabled

        Returns:
            True if logging is running, False otherwise
        """
        return self.app.telemetry_loop.is_running()
