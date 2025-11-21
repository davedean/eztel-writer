"""Update manager orchestration for auto-update system

This module provides the UpdateManager class that coordinates all update
components and manages the complete update workflow:
- Check for updates (background)
- Show user notifications
- Handle user responses
- Download and install updates
- Track skipped versions

The UpdateManager is the main entry point for the auto-update system.
"""

import sys
import logging
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, List

from src.update_checker import UpdateChecker
from src.update_ui import UpdateDialog, UpdateNotification
from src.version import get_current_version


logger = logging.getLogger(__name__)


class UpdateManager:
    """Manage the complete auto-update workflow.

    This class orchestrates all update components:
    - UpdateChecker: Check GitHub for updates
    - UpdateDialog: Show update UI to user
    - UpdateNotification: System tray notifications
    - Updater script: Replace .exe and restart

    Attributes:
        config: Configuration dictionary
        checker: UpdateChecker instance
        skipped_versions: List of versions user has skipped
        check_on_startup: Whether to check for updates on startup
    """

    def __init__(self, config: Optional[Dict] = None):
        """Initialize update manager.

        Args:
            config: Configuration dictionary with keys:
                - check_on_startup: bool (default: True)
                - auto_download: bool (default: False)
                - include_prereleases: bool (default: False)
                - skipped_versions: list (default: [])
        """
        self.config = config or {}
        self.checker = UpdateChecker()
        self.skipped_versions = self.config.get('skipped_versions', [])
        self.check_on_startup = self.config.get('check_on_startup', True)

    def should_check_for_updates(self) -> bool:
        """Check if update checking is enabled in settings.

        Returns:
            bool: True if update checking should be performed
        """
        return self.check_on_startup

    def should_show_update(self, version: str) -> bool:
        """Check if update notification should be shown for this version.

        Args:
            version: Version string to check

        Returns:
            bool: True if update should be shown, False if skipped
        """
        return version not in self.skipped_versions

    def check_for_updates_async(self, callback: Callable[[Optional[Dict]], None]):
        """Check for updates in background thread.

        Launches a background thread to check for updates without blocking
        the main application.

        Args:
            callback: Function to call with update info (or None if check fails)
                     Signature: callback(update_info: Optional[Dict])

        Example:
            >>> def on_update_checked(update_info):
            ...     if update_info and update_info['available']:
            ...         print(f"Update available: {update_info['latest_version']}")
            ...
            >>> manager.check_for_updates_async(on_update_checked)
        """
        def check_thread():
            try:
                current_version = get_current_version()
                update_info = self.checker.check_for_update(current_version)

                # Call callback with result (may be None if check failed)
                if callback:
                    callback(update_info)

            except Exception as e:
                logger.error(f"Error checking for updates: {e}")
                if callback:
                    callback(None)

        thread = threading.Thread(target=check_thread, daemon=True)
        thread.start()

    def handle_update_available(self, update_info: Dict) -> Optional[str]:
        """Handle when an update is available.

        Shows dialog to user and handles their response.

        Args:
            update_info: Dictionary with update information

        Returns:
            str: User's choice ('install', 'skip', 'later'), or None if no update

        Example:
            >>> manager.handle_update_available(update_info)
            'install'
        """
        # Only show if update is actually available
        if not update_info.get('available'):
            logger.debug("No update available")
            return None

        # Check if version was already skipped
        version = update_info['latest_version']
        if not self.should_show_update(version):
            logger.debug(f"Version {version} was skipped by user")
            return None

        # Show dialog to user
        dialog = UpdateDialog(update_info)
        choice = dialog.show()

        logger.info(f"User chose: {choice}")

        # Handle user's choice
        if choice == 'install':
            success = self.download_and_install(update_info)
            if not success:
                logger.error("Update installation failed")
        elif choice == 'skip':
            self.skip_version(version)
        elif choice == 'later':
            # Do nothing, will ask again next time
            pass

        return choice

    def download_and_install(self, update_info: Dict) -> bool:
        """Download update and launch installer.

        Downloads the new .exe, optionally verifies checksum, then launches
        the external updater script to replace the running .exe.

        Args:
            update_info: Dictionary with update information including download_url

        Returns:
            bool: True if download successful and updater launched, False otherwise

        Example:
            >>> success = manager.download_and_install(update_info)
            >>> if success:
            ...     # App will exit and updater will replace .exe
        """
        try:
            download_url = update_info['download_url']
            version = update_info['latest_version']

            # Download to temp directory
            temp_dir = Path(tempfile.gettempdir())
            new_exe = temp_dir / f"LMU_Telemetry_Logger_{version}.exe"

            logger.info(f"Downloading update from {download_url}")
            success = self.checker.download_update(download_url, new_exe)

            if not success:
                logger.error("Download failed")
                return False

            # Verify checksum if provided
            if 'checksum' in update_info:
                logger.info("Verifying checksum...")
                if not self.checker.verify_checksum(new_exe, update_info['checksum']):
                    logger.error("Checksum verification failed")
                    new_exe.unlink()  # Delete corrupted file
                    return False

            # Get path to current .exe
            if getattr(sys, 'frozen', False):
                # Running as .exe
                current_exe = Path(sys.executable)

                # When frozen, updater should be bundled as updater.exe
                # PyInstaller puts it in the same directory as the main .exe
                app_dir = current_exe.parent
                updater_exe = app_dir / "updater.exe"

                if not updater_exe.exists():
                    logger.error(f"Updater executable not found at: {updater_exe}")
                    return False

                logger.info("Launching updater executable...")
                # Launch updater.exe directly (no Python interpreter needed)
                subprocess.Popen([
                    str(updater_exe),
                    str(current_exe),
                    str(new_exe)
                ], creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            else:
                # Running as script (for testing)
                current_exe = Path(__file__).parent.parent / "dist" / "LMU_Telemetry_Logger.exe"
                updater_script = Path(__file__).parent.parent / "updater.py"

                logger.info("Launching updater script with Python...")
                # Use Python interpreter to run updater.py
                subprocess.Popen([
                    sys.executable,
                    str(updater_script),
                    str(current_exe),
                    str(new_exe)
                ])

            # Exit application (updater will replace and restart)
            logger.info("Exiting for update...")
            sys.exit(0)

        except Exception as e:
            logger.error(f"Failed to download and install update: {e}")
            return False

    def skip_version(self, version: str):
        """Mark a version as skipped.

        The skipped version will not be shown to the user again.

        Args:
            version: Version string to skip (e.g., 'v1.1.0')

        Example:
            >>> manager.skip_version('v1.1.0')
        """
        if version not in self.skipped_versions:
            self.skipped_versions.append(version)
            logger.info(f"Skipped version: {version}")

    def get_config(self) -> Dict:
        """Get current configuration including skipped versions.

        Returns:
            dict: Updated configuration dictionary

        Example:
            >>> config = manager.get_config()
            >>> config['skipped_versions']
            ['v1.0.5', 'v1.0.6']
        """
        return {
            'check_on_startup': self.check_on_startup,
            'skipped_versions': self.skipped_versions,
            **self.config
        }

    def show_notification(self, tray_icon: Optional[object], version: str):
        """Show system tray notification for available update.

        Args:
            tray_icon: pystray.Icon instance (or None)
            version: Version string of available update

        Example:
            >>> manager.show_notification(tray_icon, 'v1.1.0')
        """
        notification = UpdateNotification(tray_icon)
        notification.show_update_available(version)
