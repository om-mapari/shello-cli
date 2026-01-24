"""Tests for the VersionChecker component."""

import re
from unittest.mock import Mock, patch

import pytest
import requests
from packaging.version import InvalidVersion

from shello_cli.update.version_checker import VersionChecker


class TestVersionChecker:
    """Test suite for VersionChecker class."""

    def test_init(self):
        """Test VersionChecker initialization."""
        checker = VersionChecker("owner", "repo", timeout=10)
        assert checker.repo_owner == "owner"
        assert checker.repo_name == "repo"
        assert checker.timeout == 10
        assert checker.api_url == "https://api.github.com/repos/owner/repo/releases/latest"

    def test_get_current_version_success(self):
        """Test getting current version from shello_cli module."""
        checker = VersionChecker("owner", "repo")
        version = checker.get_current_version()
        
        # Should import from actual shello_cli.__version__
        assert isinstance(version, str)
        assert re.match(r'\d+\.\d+\.\d+', version)

    def test_get_current_version_import_error(self):
        """Test error when shello_cli module cannot be imported."""
        checker = VersionChecker("owner", "repo")
        
        # Patch the import statement inside get_current_version
        with patch.dict('sys.modules', {'shello_cli': None}):
            with pytest.raises(ValueError, match="Could not determine current version"):
                checker.get_current_version()

    def test_get_current_version_missing_attribute(self):
        """Test error when __version__ attribute is missing."""
        checker = VersionChecker("owner", "repo")
        
        # Create a mock module without __version__
        mock_module = Mock(spec=[])
        del mock_module.__version__  # Ensure __version__ doesn't exist
        
        with patch.dict('sys.modules', {'shello_cli': mock_module}):
            with pytest.raises(ValueError, match="Could not determine current version"):
                checker.get_current_version()

    def test_get_current_version_empty_version(self):
        """Test error when __version__ is empty."""
        checker = VersionChecker("owner", "repo")
        
        # Create a mock module with empty __version__
        mock_module = Mock()
        mock_module.__version__ = ""
        
        with patch.dict('sys.modules', {'shello_cli': mock_module}):
            with pytest.raises(ValueError, match="__version__ is empty"):
                checker.get_current_version()

    @patch("requests.get")
    def test_get_latest_version_success(self, mock_get):
        """Test successful GitHub API query."""
        mock_response = Mock()
        mock_response.json.return_value = {"tag_name": "v1.2.3"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        checker = VersionChecker("owner", "repo")
        version = checker.get_latest_version()
        
        assert version == "1.2.3"
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/releases/latest",
            timeout=5
        )

    @patch("requests.get")
    def test_get_latest_version_without_v_prefix(self, mock_get):
        """Test version without 'v' prefix."""
        mock_response = Mock()
        mock_response.json.return_value = {"tag_name": "1.2.3"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        checker = VersionChecker("owner", "repo")
        version = checker.get_latest_version()
        
        assert version == "1.2.3"

    @patch("requests.get")
    def test_get_latest_version_network_error(self, mock_get):
        """Test graceful handling of network errors."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        checker = VersionChecker("owner", "repo")
        version = checker.get_latest_version()
        
        assert version is None

    @patch("requests.get")
    def test_get_latest_version_malformed_json(self, mock_get):
        """Test handling of malformed JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        checker = VersionChecker("owner", "repo")
        version = checker.get_latest_version()
        
        assert version is None

    @patch("requests.get")
    def test_get_latest_version_missing_tag_name(self, mock_get):
        """Test handling when tag_name is missing."""
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        checker = VersionChecker("owner", "repo")
        version = checker.get_latest_version()
        
        assert version is None

    def test_compare_versions_latest_is_newer(self):
        """Test version comparison when latest is newer."""
        checker = VersionChecker("owner", "repo")
        
        assert checker.compare_versions("1.0.0", "1.0.1") is True
        assert checker.compare_versions("1.0.0", "1.1.0") is True
        assert checker.compare_versions("1.0.0", "2.0.0") is True

    def test_compare_versions_current_is_newer(self):
        """Test version comparison when current is newer."""
        checker = VersionChecker("owner", "repo")
        
        assert checker.compare_versions("1.0.1", "1.0.0") is False
        assert checker.compare_versions("1.1.0", "1.0.0") is False
        assert checker.compare_versions("2.0.0", "1.0.0") is False

    def test_compare_versions_equal(self):
        """Test version comparison when versions are equal."""
        checker = VersionChecker("owner", "repo")
        
        assert checker.compare_versions("1.0.0", "1.0.0") is False

    def test_compare_versions_invalid_format(self):
        """Test error handling for invalid version formats."""
        checker = VersionChecker("owner", "repo")
        
        with pytest.raises(InvalidVersion):
            checker.compare_versions("invalid", "1.0.0")
        
        with pytest.raises(InvalidVersion):
            checker.compare_versions("1.0.0", "invalid")

    @patch.object(VersionChecker, "get_current_version")
    @patch.object(VersionChecker, "get_latest_version")
    def test_is_update_available_update_exists(self, mock_latest, mock_current):
        """Test when an update is available."""
        mock_current.return_value = "1.0.0"
        mock_latest.return_value = "1.1.0"
        
        checker = VersionChecker("owner", "repo")
        update_available, current, latest = checker.is_update_available()
        
        assert update_available is True
        assert current == "1.0.0"
        assert latest == "1.1.0"

    @patch.object(VersionChecker, "get_current_version")
    @patch.object(VersionChecker, "get_latest_version")
    def test_is_update_available_no_update(self, mock_latest, mock_current):
        """Test when no update is available."""
        mock_current.return_value = "1.1.0"
        mock_latest.return_value = "1.1.0"
        
        checker = VersionChecker("owner", "repo")
        update_available, current, latest = checker.is_update_available()
        
        assert update_available is False
        assert current == "1.1.0"
        assert latest == "1.1.0"

    @patch.object(VersionChecker, "get_current_version")
    @patch.object(VersionChecker, "get_latest_version")
    def test_is_update_available_network_error(self, mock_latest, mock_current):
        """Test when network check fails."""
        mock_current.return_value = "1.0.0"
        mock_latest.return_value = None
        
        checker = VersionChecker("owner", "repo")
        update_available, current, latest = checker.is_update_available()
        
        assert update_available is False
        assert current == "1.0.0"
        assert latest is None

    @patch.object(VersionChecker, "get_current_version")
    def test_is_update_available_current_version_error(self, mock_current):
        """Test when current version cannot be determined."""
        mock_current.side_effect = ValueError("Cannot read version")
        
        checker = VersionChecker("owner", "repo")
        update_available, current, latest = checker.is_update_available()
        
        assert update_available is False
        assert current is None
        assert latest is None

    @patch.object(VersionChecker, "get_current_version")
    @patch.object(VersionChecker, "get_latest_version")
    @patch.object(VersionChecker, "compare_versions")
    def test_is_update_available_invalid_version_format(self, mock_compare, mock_latest, mock_current):
        """Test when version format is invalid."""
        mock_current.return_value = "1.0.0"
        mock_latest.return_value = "invalid"
        mock_compare.side_effect = InvalidVersion("Invalid version")
        
        checker = VersionChecker("owner", "repo")
        update_available, current, latest = checker.is_update_available()
        
        assert update_available is False
        assert current == "1.0.0"
        assert latest == "invalid"
