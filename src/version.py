"""Version management utilities for auto-update functionality

This module provides utilities for:
- Getting the current application version
- Parsing version strings
- Comparing versions to determine if updates are available
- Validating version format

All versions follow semantic versioning: MAJOR.MINOR.PATCH
Version strings may optionally include 'v' prefix (e.g., 'v1.2.3' or '1.2.3')
"""

import re
from typing import Tuple


def get_current_version() -> str:
    """Get the current application version.

    Returns:
        str: Current version string (e.g., '1.0.0')

    Example:
        >>> version = get_current_version()
        >>> print(version)
        '1.0.0'
    """
    from src import __version__
    return __version__


def parse_version(version_str: str) -> Tuple[int, int, int]:
    """Parse a version string into a tuple of integers.

    Supports both 'v1.2.3' and '1.2.3' formats.

    Args:
        version_str: Version string to parse (e.g., 'v1.2.3' or '1.2.3')

    Returns:
        Tuple[int, int, int]: Version as (major, minor, patch)

    Raises:
        ValueError: If version string is not in valid semantic versioning format

    Examples:
        >>> parse_version('v1.2.3')
        (1, 2, 3)
        >>> parse_version('1.2.3')
        (1, 2, 3)
        >>> parse_version('10.20.30')
        (10, 20, 30)
    """
    if not version_str:
        raise ValueError("Version string cannot be empty")

    # Remove 'v' prefix if present
    version = version_str.lstrip('v')

    # Match semantic versioning pattern: MAJOR.MINOR.PATCH
    pattern = r'^(\d+)\.(\d+)\.(\d+)$'
    match = re.match(pattern, version)

    if not match:
        raise ValueError(
            f"Invalid version format: '{version_str}'. "
            f"Expected format: 'MAJOR.MINOR.PATCH' (e.g., '1.2.3' or 'v1.2.3')"
        )

    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch))


def compare_versions(current: str, latest: str) -> bool:
    """Compare two version strings to determine if an update is available.

    Args:
        current: Current version string (e.g., '1.0.0' or 'v1.0.0')
        latest: Latest version string (e.g., '1.1.0' or 'v1.1.0')

    Returns:
        bool: True if latest version is newer than current version, False otherwise

    Examples:
        >>> compare_versions('1.0.0', '1.1.0')
        True
        >>> compare_versions('1.0.0', '1.0.0')
        False
        >>> compare_versions('1.1.0', '1.0.0')
        False
        >>> compare_versions('v1.0.0', 'v1.1.0')
        True
    """
    current_tuple = parse_version(current)
    latest_tuple = parse_version(latest)

    return latest_tuple > current_tuple


def is_valid_version(version_str: str) -> bool:
    """Check if a version string is in valid semantic versioning format.

    Args:
        version_str: Version string to validate

    Returns:
        bool: True if version string is valid, False otherwise

    Examples:
        >>> is_valid_version('1.2.3')
        True
        >>> is_valid_version('v1.2.3')
        True
        >>> is_valid_version('1.2')
        False
        >>> is_valid_version('abc.def.ghi')
        False
    """
    try:
        parse_version(version_str)
        return True
    except ValueError:
        return False
