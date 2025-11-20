"""Update UI components for auto-update notifications

This module provides user interface components for the auto-update system:
- UpdateDialog: Tkinter dialog for showing update information and getting user choice
- UpdateNotification: System tray balloon notification for update availability

Both components are designed to be non-intrusive and user-friendly.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import logging
from typing import Optional


logger = logging.getLogger(__name__)


class UpdateDialog:
    """Tkinter dialog for update notifications.

    Displays update information including version numbers, changelog, and
    provides buttons for user action (Install, Skip, Remind Later).

    Attributes:
        update_info: Dictionary containing update metadata
        result: User's choice ('install', 'skip', 'later', or None)
        progress: Current download progress (0.0 to 1.0)
        title: Window title
    """

    def __init__(self, update_info: dict):
        """Initialize update dialog.

        Args:
            update_info: Dictionary with keys:
                - current_version: Current version string
                - latest_version: Latest version string
                - changelog: Release notes/changelog text
                - release_date: ISO 8601 release date
        """
        self.update_info = update_info
        self.result = None
        self.progress = 0.0
        self.title = "Update Available"

        # UI components (created when show() is called)
        self.root = None
        self.progress_var = None
        self.progress_bar = None

    def show(self) -> str:
        """Show the dialog and wait for user response.

        Creates and displays the dialog window, then waits for the user
        to click a button. The dialog is modal.

        Returns:
            str: User's choice - 'install', 'skip', or 'later'

        Example:
            >>> dialog = UpdateDialog(update_info)
            >>> choice = dialog.show()
            >>> if choice == 'install':
            ...     # Download and install update
        """
        # Create root window
        self.root = tk.Tk()
        self.root.title(self.title)
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # Header
        header_frame = ttk.Frame(self.root, padding="10")
        header_frame.pack(fill=tk.X)

        title_label = ttk.Label(
            header_frame,
            text=f"Update Available: {self.update_info['latest_version']}",
            font=("", 12, "bold")
        )
        title_label.pack(anchor=tk.W)

        subtitle_label = ttk.Label(
            header_frame,
            text=f"Current version: {self.update_info['current_version']}"
        )
        subtitle_label.pack(anchor=tk.W)

        # Changelog section
        changelog_frame = ttk.LabelFrame(self.root, text="Release Notes", padding="10")
        changelog_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        changelog_text = scrolledtext.ScrolledText(
            changelog_frame,
            wrap=tk.WORD,
            width=60,
            height=15
        )
        changelog_text.pack(fill=tk.BOTH, expand=True)
        changelog_text.insert('1.0', self.update_info.get('changelog', 'No release notes available.'))
        changelog_text.config(state=tk.DISABLED)

        # Progress bar (initially hidden)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.root,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        # Don't pack yet - will be shown during download

        # Buttons
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(fill=tk.X)

        install_btn = ttk.Button(
            button_frame,
            text="Download & Install",
            command=self.on_install
        )
        install_btn.pack(side=tk.LEFT, padx=5)

        later_btn = ttk.Button(
            button_frame,
            text="Remind Me Later",
            command=self.on_later
        )
        later_btn.pack(side=tk.LEFT, padx=5)

        skip_btn = ttk.Button(
            button_frame,
            text="Skip This Version",
            command=self.on_skip
        )
        skip_btn.pack(side=tk.LEFT, padx=5)

        # Center window on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        # Make dialog modal
        self.root.grab_set()

        # Run dialog
        self.root.mainloop()

        return self.result or 'later'

    def on_install(self):
        """Handle Install button click."""
        self.result = 'install'
        if self.root:
            self.root.quit()
            self.root.destroy()

    def on_skip(self):
        """Handle Skip button click."""
        self.result = 'skip'
        if self.root:
            self.root.quit()
            self.root.destroy()

    def on_later(self):
        """Handle Remind Later button click."""
        self.result = 'later'
        if self.root:
            self.root.quit()
            self.root.destroy()

    def set_progress(self, progress: float):
        """Update download progress bar.

        Shows the progress bar and updates it with the current progress.

        Args:
            progress: Progress value from 0.0 to 1.0

        Example:
            >>> dialog.set_progress(0.5)  # 50% complete
        """
        self.progress = progress

        if self.root and self.progress_bar and self.progress_var:
            # Show progress bar if not already visible
            if not self.progress_bar.winfo_viewable():
                self.progress_bar.pack(fill=tk.X, padx=10, pady=(0, 10))

            # Update progress
            self.progress_var.set(progress * 100)
            self.root.update_idletasks()


class UpdateNotification:
    """System tray balloon notification for updates.

    Displays a balloon notification in the system tray when an update
    is available. This is less intrusive than a dialog.

    Attributes:
        tray_icon: Reference to pystray.Icon instance
        last_version: Last version that was notified about
    """

    def __init__(self, tray_icon: Optional[object]):
        """Initialize update notification.

        Args:
            tray_icon: pystray.Icon instance (or None if tray not available)
        """
        self.tray_icon = tray_icon
        self.last_version = None

    def show_update_available(self, version: str):
        """Show balloon notification for available update.

        Displays a system tray balloon notification informing the user
        that an update is available.

        Args:
            version: Version string of available update (e.g., 'v1.1.0')

        Example:
            >>> notification = UpdateNotification(tray_icon)
            >>> notification.show_update_available('v1.1.0')
        """
        self.last_version = version

        if self.tray_icon:
            try:
                # pystray notification (if supported by platform)
                if hasattr(self.tray_icon, 'notify'):
                    self.tray_icon.notify(
                        title="Update Available",
                        message=f"LMU Telemetry Logger {version} is now available!"
                    )
                else:
                    logger.debug("Tray icon doesn't support notifications")
            except Exception as e:
                logger.debug(f"Failed to show tray notification: {e}")
        else:
            logger.debug("No tray icon available for notification")
