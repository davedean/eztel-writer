"""GitHub update checker for auto-update functionality

This module provides the UpdateChecker class that:
- Checks for new releases on GitHub
- Downloads release assets (.exe files)
- Verifies download integrity with SHA256 checksums

Security features:
- HTTPS-only downloads
- Checksum verification
- Timeout protection
- Error handling for all network operations
"""

import hashlib
import logging
from pathlib import Path
from typing import Optional, Callable

import requests

from src.version import compare_versions


logger = logging.getLogger(__name__)


class UpdateChecker:
    """Check for updates from GitHub releases.

    This class handles all interactions with the GitHub API for checking
    and downloading application updates.

    Attributes:
        REPO_OWNER: GitHub repository owner
        REPO_NAME: GitHub repository name
        GITHUB_API: Full GitHub API URL for latest release
    """

    REPO_OWNER = "davedean"
    REPO_NAME = "eztel-writer"
    GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"

    def check_for_update(self, current_version: str) -> Optional[dict]:
        """Check if an update is available.

        Queries the GitHub releases API for the latest release and compares
        it with the current version.

        Args:
            current_version: Current application version (e.g., '1.0.0')

        Returns:
            dict with update information if successful:
                {
                    'available': bool,           # True if update available
                    'current_version': str,      # Current version
                    'latest_version': str,       # Latest version on GitHub
                    'download_url': str,         # URL to .exe file
                    'changelog': str,            # Release notes
                    'release_date': str,         # ISO 8601 timestamp
                }
            None if check fails (network error, API error, no .exe asset, etc.)

        Example:
            >>> checker = UpdateChecker()
            >>> update_info = checker.check_for_update('1.0.0')
            >>> if update_info and update_info['available']:
            ...     print(f"Update available: {update_info['latest_version']}")
        """
        try:
            # Query GitHub API with timeout
            response = requests.get(self.GITHUB_API, timeout=5)
            response.raise_for_status()
            release = response.json()

            # Extract release metadata
            latest_version = release['tag_name']
            changelog = release.get('body', '')
            release_date = release.get('published_at', '')

            # Find .exe asset in release
            download_url = None
            for asset in release.get('assets', []):
                if asset['name'].endswith('.exe'):
                    download_url = asset['browser_download_url']
                    break

            # No .exe found in release
            if not download_url:
                logger.warning(f"No .exe asset found in release {latest_version}")
                return None

            # Compare versions
            update_available = compare_versions(current_version, latest_version)

            return {
                'available': update_available,
                'current_version': current_version,
                'latest_version': latest_version,
                'download_url': download_url,
                'changelog': changelog,
                'release_date': release_date,
            }

        except requests.RequestException as e:
            # Network error, timeout, or HTTP error
            logger.debug(f"Update check failed: {e}")
            return None

        except (KeyError, ValueError) as e:
            # JSON parsing error or missing required fields
            logger.debug(f"Failed to parse GitHub release data: {e}")
            return None

    def download_update(
        self,
        download_url: str,
        dest_path: Path,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> bool:
        """Download update file from GitHub.

        Downloads the update file with streaming to handle large files
        efficiently. Optionally reports progress via callback.

        Args:
            download_url: URL to download from (must be HTTPS)
            dest_path: Destination path for downloaded file
            progress_callback: Optional callback function called with bytes
                             downloaded after each chunk. Signature: fn(bytes_downloaded: int)

        Returns:
            bool: True if download successful, False otherwise

        Example:
            >>> checker = UpdateChecker()
            >>> url = "https://github.com/owner/repo/releases/download/v1.1.0/app.exe"
            >>> dest = Path("./downloads/app.exe")
            >>> success = checker.download_update(url, dest)
        """
        # Security: Only allow HTTPS downloads
        if not download_url.startswith('https://'):
            logger.error(f"Rejected non-HTTPS download URL: {download_url}")
            return False

        try:
            # Download with streaming for large files
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()

            # Ensure parent directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to file in chunks
            bytes_downloaded = 0
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # Filter out keep-alive chunks
                        f.write(chunk)
                        bytes_downloaded += len(chunk)

                        # Report progress if callback provided
                        if progress_callback:
                            progress_callback(bytes_downloaded)

            logger.info(f"Downloaded {bytes_downloaded} bytes to {dest_path}")
            return True

        except requests.RequestException as e:
            logger.error(f"Download failed: {e}")
            # Clean up partial download
            if dest_path.exists():
                dest_path.unlink()
            return False

    def verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """Verify downloaded file integrity using SHA256 checksum.

        Args:
            file_path: Path to file to verify
            expected_checksum: Expected SHA256 checksum (hex string)

        Returns:
            bool: True if checksum matches, False otherwise

        Raises:
            FileNotFoundError: If file does not exist

        Example:
            >>> checker = UpdateChecker()
            >>> valid = checker.verify_checksum(
            ...     Path("app.exe"),
            ...     "abc123def456..."
            ... )
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # Calculate SHA256 checksum
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        actual_checksum = sha256.hexdigest()

        # Compare checksums (case-insensitive)
        is_valid = actual_checksum.lower() == expected_checksum.lower()

        if not is_valid:
            logger.error(f"Checksum mismatch for {file_path}")
            logger.error(f"  Expected: {expected_checksum}")
            logger.error(f"  Actual:   {actual_checksum}")

        return is_valid
