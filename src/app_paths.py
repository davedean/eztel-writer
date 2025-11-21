"""Application path utilities for cross-platform file storage

Provides utilities for determining appropriate directories for:
- Application data (config files)
- Log files
- Cache/temporary files

Follows platform conventions:
- Windows: %LOCALAPPDATA%\LMU Telemetry Logger\
- macOS: ~/Library/Application Support/LMU Telemetry Logger/
- Linux: ~/.local/share/lmu-telemetry-logger/
"""

import os
import sys
from pathlib import Path
from typing import Optional


def get_app_data_dir() -> Path:
    """Get the platform-appropriate application data directory

    Returns:
        Path to application data directory (created if doesn't exist)

    Examples:
        - Windows: C:\\Users\\username\\AppData\\Local\\LMU Telemetry Logger\\
        - macOS: ~/Library/Application Support/LMU Telemetry Logger/
        - Linux: ~/.local/share/lmu-telemetry-logger/
    """
    app_name = "LMU Telemetry Logger"

    if sys.platform == 'win32':
        # Windows: Use LOCALAPPDATA
        base = os.environ.get('LOCALAPPDATA')
        if not base:
            # Fallback if LOCALAPPDATA not set
            base = os.path.expanduser('~\\AppData\\Local')
        app_dir = Path(base) / app_name

    elif sys.platform == 'darwin':
        # macOS: Use ~/Library/Application Support/
        app_dir = Path.home() / 'Library' / 'Application Support' / app_name

    else:
        # Linux/Unix: Use XDG_DATA_HOME or ~/.local/share
        xdg_data = os.environ.get('XDG_DATA_HOME')
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / '.local' / 'share'
        # Use lowercase with hyphens for Linux (convention)
        app_dir = base / 'lmu-telemetry-logger'

    # Create directory if it doesn't exist
    app_dir.mkdir(parents=True, exist_ok=True)

    return app_dir


def get_config_file_path(filename: str = 'config.json') -> Path:
    """Get path to configuration file in app data directory

    Args:
        filename: Name of config file (default: config.json)

    Returns:
        Path to config file
    """
    return get_app_data_dir() / filename


def get_log_file_path(filename: str = 'telemetry_logger.log') -> Path:
    """Get path to log file in app data directory

    Args:
        filename: Name of log file (default: telemetry_logger.log)

    Returns:
        Path to log file
    """
    return get_app_data_dir() / filename


def get_legacy_config_path() -> Optional[Path]:
    """Get legacy config file path (for migration)

    Returns path to old config.json location (script directory) if it exists,
    otherwise None.

    Returns:
        Path to legacy config file, or None if not found
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable - check exe directory
        legacy_dir = os.path.dirname(sys.executable)
    else:
        # Running as script - check script directory
        legacy_dir = os.path.dirname(os.path.abspath(__file__))

    legacy_config = Path(legacy_dir) / 'config.json'

    if legacy_config.exists():
        return legacy_config

    return None


def migrate_config_if_needed(config_filename: str = 'config.json') -> None:
    """Migrate config from legacy location to app data directory if needed

    If a config.json exists in the script/exe directory and not in the app data
    directory, copy it to the new location.

    Args:
        config_filename: Name of config file (default: config.json)
    """
    import shutil

    new_config = get_config_file_path(config_filename)
    legacy_config = get_legacy_config_path()

    # Only migrate if legacy exists and new doesn't
    if legacy_config and not new_config.exists():
        try:
            shutil.copy2(legacy_config, new_config)
            print(f"Migrated config from {legacy_config} to {new_config}")
        except Exception as e:
            print(f"Warning: Could not migrate config: {e}")
