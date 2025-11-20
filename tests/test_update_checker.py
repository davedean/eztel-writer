"""Tests for GitHub update checker"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from src.update_checker import UpdateChecker


class TestCheckForUpdate:
    """Tests for check_for_update method"""

    @patch('requests.get')
    def test_check_for_update_available(self, mock_get):
        """Test update check when newer version is available"""
        # Mock GitHub API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'tag_name': 'v1.1.0',
            'body': '## What\'s New\n- Feature 1\n- Bug fix 2',
            'published_at': '2025-11-20T10:00:00Z',
            'assets': [
                {
                    'name': 'LMU_Telemetry_Logger.exe',
                    'browser_download_url': 'https://github.com/davedean/eztel-writer/releases/download/v1.1.0/LMU_Telemetry_Logger.exe'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result is not None
        assert result['available'] is True
        assert result['current_version'] == '1.0.0'
        assert result['latest_version'] == 'v1.1.0'
        assert 'github.com' in result['download_url']
        assert 'Feature 1' in result['changelog']

    @patch('requests.get')
    def test_check_for_update_not_available(self, mock_get):
        """Test update check when no update is available (same version)"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tag_name': 'v1.0.0',
            'body': 'Release notes',
            'published_at': '2025-11-20T10:00:00Z',
            'assets': [
                {
                    'name': 'LMU_Telemetry_Logger.exe',
                    'browser_download_url': 'https://github.com/davedean/eztel-writer/releases/download/v1.0.0/LMU_Telemetry_Logger.exe'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result is not None
        assert result['available'] is False
        assert result['current_version'] == '1.0.0'
        assert result['latest_version'] == 'v1.0.0'

    @patch('requests.get')
    def test_check_for_update_network_error(self, mock_get):
        """Test update check when network request fails"""
        mock_get.side_effect = requests.RequestException("Network error")

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result is None

    @patch('requests.get')
    def test_check_for_update_invalid_response(self, mock_get):
        """Test update check when GitHub returns invalid JSON"""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result is None

    @patch('requests.get')
    def test_check_for_update_no_exe_asset(self, mock_get):
        """Test update check when release has no .exe file"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tag_name': 'v1.1.0',
            'body': 'Release notes',
            'published_at': '2025-11-20T10:00:00Z',
            'assets': [
                {
                    'name': 'source.zip',
                    'browser_download_url': 'https://github.com/davedean/eztel-writer/archive/v1.1.0.zip'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        # Should return None if no .exe asset found
        assert result is None

    @patch('requests.get')
    def test_github_api_timeout(self, mock_get):
        """Test update check when GitHub API times out"""
        mock_get.side_effect = requests.Timeout("Request timed out")

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result is None

    @patch('requests.get')
    def test_parse_release_metadata(self, mock_get):
        """Test that all release metadata is correctly parsed"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tag_name': 'v2.0.0',
            'body': '## Major Update\n- New feature\n- Breaking changes',
            'published_at': '2025-12-01T15:30:00Z',
            'assets': [
                {
                    'name': 'LMU_Telemetry_Logger.exe',
                    'browser_download_url': 'https://github.com/davedean/eztel-writer/releases/download/v2.0.0/LMU_Telemetry_Logger.exe'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result['available'] is True
        assert result['latest_version'] == 'v2.0.0'
        assert result['changelog'] == '## Major Update\n- New feature\n- Breaking changes'
        assert result['release_date'] == '2025-12-01T15:30:00Z'
        assert 'v2.0.0' in result['download_url']

    @patch('requests.get')
    def test_handle_github_rate_limit(self, mock_get):
        """Test handling of GitHub rate limit (403 response)"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("403 Forbidden")
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        result = checker.check_for_update('1.0.0')

        assert result is None


class TestDownloadUpdate:
    """Tests for download_update method"""

    @patch('requests.get')
    def test_download_update_success(self, mock_get):
        """Test successful update download"""
        # Mock download response
        mock_response = Mock()
        mock_response.iter_content = Mock(return_value=[b'test', b'data'])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        checker = UpdateChecker()
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / 'test.exe'
            result = checker.download_update('https://github.com/test/test.exe', dest_path)

            assert result is True
            assert dest_path.exists()
            assert dest_path.read_bytes() == b'testdata'

    @patch('requests.get')
    def test_download_update_network_error(self, mock_get):
        """Test download failure due to network error"""
        mock_get.side_effect = requests.RequestException("Network error")

        checker = UpdateChecker()
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / 'test.exe'
            result = checker.download_update('https://github.com/test/test.exe', dest_path)

            assert result is False
            assert not dest_path.exists()

    @patch('requests.get')
    def test_download_update_with_progress(self, mock_get):
        """Test download with progress callback"""
        # Mock download response with multiple chunks
        mock_response = Mock()
        chunks = [b'chunk1', b'chunk2', b'chunk3']
        mock_response.iter_content = Mock(return_value=chunks)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Track progress callback invocations
        progress_calls = []

        def progress_callback(bytes_downloaded):
            progress_calls.append(bytes_downloaded)

        checker = UpdateChecker()
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / 'test.exe'
            result = checker.download_update(
                'https://github.com/test/test.exe',
                dest_path,
                progress_callback=progress_callback
            )

            assert result is True
            # Progress callback should have been called for each chunk
            assert len(progress_calls) == len(chunks)
            assert progress_calls[0] == len(chunks[0])
            assert progress_calls[-1] == sum(len(c) for c in chunks)

    @patch('requests.get')
    def test_https_only(self, mock_get):
        """Test that only HTTPS URLs are accepted"""
        checker = UpdateChecker()
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / 'test.exe'

            # HTTP should be rejected
            result = checker.download_update('http://github.com/test.exe', dest_path)
            assert result is False
            assert not dest_path.exists()

            # mock_get should not have been called
            mock_get.assert_not_called()


class TestVerifyChecksum:
    """Tests for verify_checksum method"""

    def test_verify_checksum_valid(self):
        """Test checksum verification with valid SHA256"""
        checker = UpdateChecker()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / 'test.exe'
            content = b'test file content for checksum'
            test_file.write_bytes(content)

            # Calculate expected checksum
            expected_checksum = hashlib.sha256(content).hexdigest()

            result = checker.verify_checksum(test_file, expected_checksum)
            assert result is True

    def test_verify_checksum_invalid(self):
        """Test checksum verification with invalid SHA256"""
        checker = UpdateChecker()

        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / 'test.exe'
            test_file.write_bytes(b'test content')

            # Use wrong checksum
            wrong_checksum = 'a' * 64  # Invalid checksum

            result = checker.verify_checksum(test_file, wrong_checksum)
            assert result is False

    def test_verify_checksum_file_not_found(self):
        """Test checksum verification when file doesn't exist"""
        checker = UpdateChecker()

        non_existent_file = Path('/tmp/does_not_exist.exe')

        with pytest.raises(FileNotFoundError):
            checker.verify_checksum(non_existent_file, 'a' * 64)


class TestUpdateCheckerConfiguration:
    """Tests for UpdateChecker configuration"""

    def test_github_api_url_format(self):
        """Test that GitHub API URL is correctly formatted"""
        checker = UpdateChecker()

        assert 'davedean' in checker.GITHUB_API
        assert 'eztel-writer' in checker.GITHUB_API
        assert 'releases/latest' in checker.GITHUB_API
        assert checker.GITHUB_API.startswith('https://')
