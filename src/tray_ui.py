"""System tray UI for telemetry logger"""

import sys
import subprocess
from typing import Any, Optional
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as Item
from src.session_manager import SessionState


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
            pystray.Menu.SEPARATOR,
            Item('Check for Updates...', self.on_check_for_updates),
            pystray.Menu.SEPARATOR,
            Item('Quit', self.on_quit)
        )

        self.icon = pystray.Icon(
            'lmu_telemetry',
            self.icons[self.state],
            'LMU Telemetry Logger',
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
            return 'LMU Telemetry Logger - Idle (Waiting for LMU)'
        elif self.state == SessionState.DETECTED:
            return 'LMU Telemetry Logger - Detected (LMU running)'
        elif self.state == SessionState.LOGGING:
            lap = self.app.telemetry_loop.session_manager.current_lap
            samples = len(self.app.telemetry_loop.session_manager.lap_samples)
            return f'LMU Telemetry Logger - Logging Lap {lap} ({samples} samples)'
        elif self.state == SessionState.PAUSED:
            return 'LMU Telemetry Logger - Paused'
        elif self.state == SessionState.ERROR:
            return 'LMU Telemetry Logger - Error'
        else:
            return 'LMU Telemetry Logger'

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
