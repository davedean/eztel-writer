"""Settings UI and configuration management for telemetry logger"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


class SettingsConfig:
    """Configuration manager for telemetry logger settings

    Handles loading, saving, and validating configuration settings.
    Separates configuration logic from GUI to enable testing without UI.
    """

    DEFAULT_CONFIG = {
        'output_dir': './telemetry_output',
        'target_process': 'Le Mans Ultimate',
        'poll_interval': 0.01,  # 100Hz
        'track_opponents': True,
        'track_opponent_ai': False,
    }

    def __init__(self, config_file: str = 'config.json'):
        """Initialize settings configuration

        Args:
            config_file: Path to config JSON file
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file, merging with defaults

        Returns:
            Configuration dictionary
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge user config with defaults (user config takes precedence)
                return {**self.DEFAULT_CONFIG, **user_config}
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, use defaults
                return self.DEFAULT_CONFIG.copy()
        else:
            # No config file, use defaults
            return self.DEFAULT_CONFIG.copy()

    def get(self, key: str) -> Any:
        """Get configuration value

        Args:
            key: Configuration key

        Returns:
            Configuration value
        """
        return self.config.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value

        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values

        Returns:
            Copy of configuration dictionary
        """
        return self.config.copy()

    def save(self) -> None:
        """Save configuration to file

        Raises:
            IOError: If file cannot be written
        """
        # Create parent directory if it doesn't exist
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def restore_defaults(self) -> None:
        """Restore all configuration values to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()

    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate current configuration

        Returns:
            Tuple of (is_valid, error_message)
            error_message is None if valid
        """
        # Validate output directory
        output_dir = self.config.get('output_dir')
        if output_dir:
            try:
                # Try to create the directory to validate it's accessible
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            except (OSError, ValueError) as e:
                return False, f"Invalid output_dir: {str(e)}"

        # Validate poll interval
        poll_interval = self.config.get('poll_interval')
        if poll_interval is not None:
            if not isinstance(poll_interval, (int, float)) or poll_interval <= 0:
                return False, "poll_interval must be a positive number"

        # Validate target process (must be non-empty string)
        target_process = self.config.get('target_process')
        if target_process is not None:
            if not isinstance(target_process, str) or len(target_process.strip()) == 0:
                return False, "target_process must be a non-empty string"

        return True, None

    @staticmethod
    def hz_to_interval(hz: float) -> float:
        """Convert frequency (Hz) to poll interval (seconds)

        Args:
            hz: Frequency in Hz

        Returns:
            Poll interval in seconds
        """
        return 1.0 / hz

    @staticmethod
    def interval_to_hz(interval: float) -> float:
        """Convert poll interval (seconds) to frequency (Hz)

        Args:
            interval: Poll interval in seconds

        Returns:
            Frequency in Hz
        """
        return 1.0 / interval


class SettingsDialog:
    """GUI dialog for editing telemetry logger settings

    Uses tkinter for cross-platform GUI support.
    """

    def __init__(self, config_file: str = 'config.json', parent=None):
        """Initialize settings dialog

        Args:
            config_file: Path to config JSON file
            parent: Parent window (optional, for modal dialogs)
        """
        try:
            import tkinter as tk
            from tkinter import ttk, filedialog, messagebox
        except ImportError:
            raise ImportError("tkinter is required for settings UI")

        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox

        self.config = SettingsConfig(config_file)
        self.config_file = config_file
        self.result = False  # True if saved, False if cancelled

        # Create window
        if parent is None:
            self.root = tk.Tk()
        else:
            self.root = tk.Toplevel(parent)

        self.root.title("Telemetry Logger Settings")
        self.root.geometry("600x500")
        self.root.resizable(True, True)

        # Store UI variables
        self.output_dir_var = tk.StringVar(value=self.config.get('output_dir'))
        self.target_process_var = tk.StringVar(value=self.config.get('target_process'))
        self.poll_hz_var = tk.IntVar(value=int(self.config.interval_to_hz(self.config.get('poll_interval'))))
        self.track_opponents_var = tk.BooleanVar(value=self.config.get('track_opponents'))
        self.track_opponent_ai_var = tk.BooleanVar(value=self.config.get('track_opponent_ai'))
        self.check_updates_on_startup_var = tk.BooleanVar(value=self.config.get('check_updates_on_startup', True))

        self._build_ui()

    def _build_ui(self):
        """Build the settings dialog UI"""
        # Main container with padding
        main_frame = self.ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(self.tk.W, self.tk.E, self.tk.N, self.tk.S))

        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0

        # ===== Output Directory Section =====
        self.ttk.Label(main_frame, text="Output Directory:", font=('TkDefaultFont', 10, 'bold')).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, pady=(0, 5))
        row += 1

        self.ttk.Entry(main_frame, textvariable=self.output_dir_var, width=50).grid(
            row=row, column=0, columnspan=2, sticky=(self.tk.W, self.tk.E), padx=(0, 5))
        self.ttk.Button(main_frame, text="Browse...", command=self._on_browse_output_dir).grid(
            row=row, column=2, sticky=self.tk.E)
        row += 1

        # ===== Opponent Tracking Section =====
        self.ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(self.tk.W, self.tk.E), pady=15)
        row += 1

        self.ttk.Label(main_frame, text="Opponent Tracking:", font=('TkDefaultFont', 10, 'bold')).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, pady=(0, 5))
        row += 1

        self.ttk.Checkbutton(main_frame, text="Track opponents (save opponent laps to CSV)",
                            variable=self.track_opponents_var).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, padx=(20, 0))
        row += 1

        self.ttk.Checkbutton(main_frame, text="Track AI opponents (include AI-controlled opponents)",
                            variable=self.track_opponent_ai_var).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, padx=(20, 0))
        row += 1

        # ===== Advanced Settings Section =====
        self.ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(self.tk.W, self.tk.E), pady=15)
        row += 1

        self.ttk.Label(main_frame, text="Advanced Settings:", font=('TkDefaultFont', 10, 'bold')).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, pady=(0, 5))
        row += 1

        # Target Process
        self.ttk.Label(main_frame, text="Target Process:").grid(
            row=row, column=0, sticky=self.tk.W, padx=(20, 5), pady=5)
        self.ttk.Entry(main_frame, textvariable=self.target_process_var, width=30).grid(
            row=row, column=1, sticky=(self.tk.W, self.tk.E), pady=5)
        self.ttk.Label(main_frame, text="(e.g., 'Le Mans Ultimate')").grid(
            row=row, column=2, sticky=self.tk.W, padx=(5, 0))
        row += 1

        # Poll Interval
        self.ttk.Label(main_frame, text="Poll Rate:").grid(
            row=row, column=0, sticky=self.tk.W, padx=(20, 5), pady=5)
        poll_frame = self.ttk.Frame(main_frame)
        poll_frame.grid(row=row, column=1, sticky=(self.tk.W, self.tk.E), pady=5)

        for hz in [50, 100, 200]:
            self.ttk.Radiobutton(poll_frame, text=f"{hz} Hz", variable=self.poll_hz_var,
                               value=hz).pack(side=self.tk.LEFT, padx=5)
        row += 1

        # ===== Auto-Update Settings Section =====
        self.ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(self.tk.W, self.tk.E), pady=15)
        row += 1

        self.ttk.Label(main_frame, text="Auto-Update Settings:", font=('TkDefaultFont', 10, 'bold')).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, pady=(0, 5))
        row += 1

        self.ttk.Checkbutton(main_frame, text="Check for updates on startup",
                            variable=self.check_updates_on_startup_var).grid(
            row=row, column=0, columnspan=3, sticky=self.tk.W, padx=(20, 0))
        row += 1

        # ===== Buttons Section =====
        self.ttk.Separator(main_frame, orient='horizontal').grid(
            row=row, column=0, columnspan=3, sticky=(self.tk.W, self.tk.E), pady=15)
        row += 1

        button_frame = self.ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=3, sticky=(self.tk.E, self.tk.W))

        self.ttk.Button(button_frame, text="Restore Defaults", command=self._on_restore_defaults).pack(
            side=self.tk.LEFT, padx=5)
        self.ttk.Button(button_frame, text="Cancel", command=self._on_cancel).pack(
            side=self.tk.RIGHT, padx=5)
        self.ttk.Button(button_frame, text="Save", command=self._on_save).pack(
            side=self.tk.RIGHT, padx=5)

    def _on_browse_output_dir(self):
        """Handle Browse button click for output directory"""
        dir_path = self.filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_dir_var.get()
        )
        if dir_path:
            self.output_dir_var.set(dir_path)

    def _on_save(self):
        """Handle Save button click"""
        # Update config from UI
        self.config.set('output_dir', self.output_dir_var.get())
        self.config.set('target_process', self.target_process_var.get())
        self.config.set('poll_interval', self.config.hz_to_interval(self.poll_hz_var.get()))
        self.config.set('track_opponents', self.track_opponents_var.get())
        self.config.set('track_opponent_ai', self.track_opponent_ai_var.get())
        self.config.set('check_updates_on_startup', self.check_updates_on_startup_var.get())

        # Validate
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            self.messagebox.showerror("Validation Error", error_msg)
            return

        # Save to file
        try:
            self.config.save()
            self.result = True
            self.root.destroy()
        except IOError as e:
            self.messagebox.showerror("Save Error", f"Failed to save config: {str(e)}")

    def _on_cancel(self):
        """Handle Cancel button click"""
        self.result = False
        self.root.destroy()

    def _on_restore_defaults(self):
        """Handle Restore Defaults button click"""
        # Restore defaults in config
        self.config.restore_defaults()

        # Update UI variables
        self.output_dir_var.set(self.config.get('output_dir'))
        self.target_process_var.set(self.config.get('target_process'))
        self.poll_hz_var.set(int(self.config.interval_to_hz(self.config.get('poll_interval'))))
        self.track_opponents_var.set(self.config.get('track_opponents'))
        self.track_opponent_ai_var.set(self.config.get('track_opponent_ai'))

    def show(self) -> bool:
        """Show the settings dialog (modal)

        Returns:
            True if user clicked Save, False if cancelled
        """
        # Make dialog modal
        self.root.transient()
        self.root.grab_set()

        # Center on screen
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

        # Run event loop
        self.root.mainloop()

        return self.result


def show_settings_dialog(config_file: str = 'config.json') -> bool:
    """Convenience function to show settings dialog

    Args:
        config_file: Path to config JSON file

    Returns:
        True if user saved changes, False if cancelled
    """
    dialog = SettingsDialog(config_file)
    return dialog.show()


if __name__ == '__main__':
    # Demo: show settings dialog
    saved = show_settings_dialog()
    if saved:
        print("Settings saved!")
    else:
        print("Settings cancelled")
