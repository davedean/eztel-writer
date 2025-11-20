"""Tests for version management utilities"""

import pytest
from src.version import (
    get_current_version,
    parse_version,
    compare_versions,
    is_valid_version,
)


class TestGetCurrentVersion:
    """Tests for get_current_version function"""

    def test_get_current_version(self):
        """Test that current version is returned from __init__.py"""
        version = get_current_version()
        assert isinstance(version, str)
        assert len(version) > 0
        # Should match semantic versioning pattern
        assert is_valid_version(version)


class TestParseVersion:
    """Tests for parse_version function"""

    def test_parse_version_with_v_prefix(self):
        """Test parsing version string with 'v' prefix"""
        assert parse_version("v1.2.3") == (1, 2, 3)
        assert parse_version("v10.20.30") == (10, 20, 30)
        assert parse_version("v0.0.1") == (0, 0, 1)

    def test_parse_version_without_v_prefix(self):
        """Test parsing version string without 'v' prefix"""
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("10.20.30") == (10, 20, 30)
        assert parse_version("0.0.1") == (0, 0, 1)

    def test_parse_version_invalid_format(self):
        """Test that invalid version format raises ValueError"""
        with pytest.raises(ValueError):
            parse_version("1.2")  # Missing patch version

        with pytest.raises(ValueError):
            parse_version("1.2.3.4")  # Too many parts

        with pytest.raises(ValueError):
            parse_version("abc.def.ghi")  # Non-numeric

        with pytest.raises(ValueError):
            parse_version("")  # Empty string

        with pytest.raises(ValueError):
            parse_version("v1.2.x")  # Invalid number


class TestCompareVersions:
    """Tests for compare_versions function"""

    def test_compare_versions_update_available(self):
        """Test that newer version is detected"""
        # Minor version update
        assert compare_versions("1.0.0", "1.1.0") is True
        # Patch version update
        assert compare_versions("1.0.0", "1.0.1") is True
        # Major version update
        assert compare_versions("1.0.0", "2.0.0") is True
        # Multiple version jumps
        assert compare_versions("1.0.0", "1.2.5") is True

    def test_compare_versions_no_update_available(self):
        """Test that same version returns False"""
        assert compare_versions("1.0.0", "1.0.0") is False
        assert compare_versions("1.2.3", "1.2.3") is False
        assert compare_versions("10.20.30", "10.20.30") is False

    def test_compare_versions_downgrade(self):
        """Test that older version returns False"""
        assert compare_versions("1.1.0", "1.0.0") is False
        assert compare_versions("2.0.0", "1.9.9") is False
        assert compare_versions("1.0.1", "1.0.0") is False

    def test_compare_versions_with_v_prefix(self):
        """Test comparison works with 'v' prefix"""
        assert compare_versions("v1.0.0", "v1.1.0") is True
        assert compare_versions("v1.0.0", "v1.0.0") is False
        assert compare_versions("v1.1.0", "v1.0.0") is False

    def test_compare_versions_mixed_format(self):
        """Test comparison works with mixed formats"""
        assert compare_versions("1.0.0", "v1.1.0") is True
        assert compare_versions("v1.0.0", "1.1.0") is True


class TestIsValidVersion:
    """Tests for is_valid_version function"""

    def test_valid_version_formats(self):
        """Test that valid version formats are recognized"""
        assert is_valid_version("1.2.3") is True
        assert is_valid_version("v1.2.3") is True
        assert is_valid_version("0.0.1") is True
        assert is_valid_version("10.20.30") is True
        assert is_valid_version("v100.200.300") is True

    def test_invalid_version_formats(self):
        """Test that invalid version formats are rejected"""
        assert is_valid_version("1.2") is False  # Missing patch
        assert is_valid_version("1.2.3.4") is False  # Too many parts
        assert is_valid_version("abc.def.ghi") is False  # Non-numeric
        assert is_valid_version("") is False  # Empty
        assert is_valid_version("1.2.x") is False  # Invalid number
        assert is_valid_version("v1.2") is False  # Missing patch with v prefix
