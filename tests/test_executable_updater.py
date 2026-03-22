"""Tests for the ExecutableUpdater component."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pytest
import requests

from shello_cli.update.executable_updater import ExecutableUpdater
from shello_cli.update.exceptions import DownloadError, UpdateError


class TestExecutableUpdater:
    """Test suite for ExecutableUpdater class."""

    def test_init(self):
        """Test ExecutableUpdater initialization."""
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        assert updater.repo_owner == "test-owner"
        assert updater.repo_name == "test-repo"
        assert updater.base_url == "https://github.com/test-owner/test-repo/releases/download"

    def test_init_with_real_repo(self):
        """Test initialization with real repository details."""
        updater = ExecutableUpdater("om-mapari", "shello-cli")
        
        assert updater.repo_owner == "om-mapari"
        assert updater.repo_name == "shello-cli"
        assert "om-mapari" in updater.base_url
        assert "shello-cli" in updater.base_url

    @patch("requests.get")
    def test_download_binary_success(self, mock_get):
        """Test successful binary download."""
        # Setup mock response
        mock_response = Mock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content = Mock(return_value=[b'test' * 256])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        # Download binary
        result_path = updater.download_binary("v0.4.4", "shello.exe")
        
        # Verify
        assert os.path.exists(result_path)
        assert "shello_update_shello.exe" in result_path
        
        # Verify URL construction
        expected_url = "https://github.com/test-owner/test-repo/releases/download/v0.4.4/shello.exe"
        mock_get.assert_called_once()
        assert mock_get.call_args[0][0] == expected_url
        
        # Cleanup
        if os.path.exists(result_path):
            os.remove(result_path)

    @patch("requests.get")
    def test_download_binary_adds_v_prefix(self, mock_get):
        """Test that download adds 'v' prefix to version if missing."""
        mock_response = Mock()
        mock_response.headers = {'content-length': '1024'}
        mock_response.iter_content = Mock(return_value=[b'test'])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        updater = ExecutableUpdater("test-owner", "test-repo")
        result_path = updater.download_binary("0.4.4", "shello.exe")
        
        # Verify URL has 'v' prefix
        expected_url = "https://github.com/test-owner/test-repo/releases/download/v0.4.4/shello.exe"
        assert mock_get.call_args[0][0] == expected_url
        
        # Cleanup
        if os.path.exists(result_path):
            os.remove(result_path)

    @patch("requests.get")
    def test_download_binary_with_progress_callback(self, mock_get):
        """Test download with progress callback."""
        mock_response = Mock()
        mock_response.headers = {'content-length': '2048'}
        mock_response.iter_content = Mock(return_value=[b'a' * 1024, b'b' * 1024])
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        # Track progress calls
        progress_calls = []
        def progress_callback(downloaded, total):
            progress_calls.append((downloaded, total))
        
        result_path = updater.download_binary("v0.4.4", "shello", progress_callback)
        
        # Verify progress was tracked
        assert len(progress_calls) == 2
        assert progress_calls[0] == (1024, 2048)
        assert progress_calls[1] == (2048, 2048)
        
        # Cleanup
        if os.path.exists(result_path):
            os.remove(result_path)

    @patch("requests.get")
    def test_download_binary_network_error(self, mock_get):
        """Test download failure due to network error."""
        mock_get.side_effect = requests.RequestException("Network error")
        
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        with pytest.raises(DownloadError) as exc_info:
            updater.download_binary("v0.4.4", "shello.exe")
        
        assert "Failed to download binary" in str(exc_info.value)
        assert "Network error" in str(exc_info.value)

    @patch("requests.get")
    def test_download_binary_http_error(self, mock_get):
        """Test download failure due to HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        with pytest.raises(DownloadError) as exc_info:
            updater.download_binary("v0.4.4", "shello.exe")
        
        assert "Failed to download binary" in str(exc_info.value)

    def test_verify_binary_valid_file(self):
        """Test binary verification with valid file."""
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        # Create temporary file with content
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test binary content")
            temp_path = f.name
        
        try:
            result = updater.verify_binary(temp_path)
            assert result is True
        finally:
            os.remove(temp_path)

    def test_verify_binary_empty_file(self):
        """Test binary verification with empty file."""
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        # Create empty temporary file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            temp_path = f.name
        
        try:
            result = updater.verify_binary(temp_path)
            assert result is False
        finally:
            os.remove(temp_path)

    def test_verify_binary_nonexistent_file(self):
        """Test binary verification with nonexistent file."""
        updater = ExecutableUpdater("test-owner", "test-repo")
        
        result = updater.verify_binary("/nonexistent/path/to/file")
        assert result is False

    def test_replace_executable_success(self):
        """Test successful executable replacement."""
        updater = ExecutableUpdater("test-owner", "test-repo")

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as old_file:
            old_file.write("old executable")
            old_path = old_file.name

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as new_file:
            new_file.write("new executable")
            new_path = new_file.name

        old_bak = f"{old_path}.old"

        try:
            updater.replace_executable(new_path, old_path)

            with open(old_path, 'r') as f:
                content = f.read()
            assert content == "new executable"

            # .old file cleaned up on success
            assert not os.path.exists(old_bak)
            # new binary was moved, not copied
            assert not os.path.exists(new_path)

        finally:
            for p in [old_path, new_path, old_bak]:
                if os.path.exists(p):
                    os.remove(p)

    def test_replace_executable_uses_rename_on_windows(self):
        """On Windows the old exe is renamed before placing the new one (avoids lock)."""
        updater = ExecutableUpdater("test-owner", "test-repo")

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as old_file:
            old_file.write("old executable")
            old_path = old_file.name

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as new_file:
            new_file.write("new executable")
            new_path = new_file.name

        old_bak = f"{old_path}.old"
        rename_calls = []
        original_rename = os.rename

        def tracking_rename(src, dst):
            rename_calls.append((src, dst))
            return original_rename(src, dst)

        try:
            with patch('os.name', 'nt'), patch('os.rename', side_effect=tracking_rename):
                updater.replace_executable(new_path, old_path)

            # rename should have been called to move old exe out of the way
            assert any(dst == old_bak for _, dst in rename_calls), \
                "Expected old exe to be renamed to .old before replacement"

            with open(old_path, 'r') as f:
                assert f.read() == "new executable"

        finally:
            for p in [old_path, new_path, old_bak]:
                if os.path.exists(p):
                    os.remove(p)

    def test_replace_executable_restores_on_failure(self):
        """Test that old exe is restored when replacement fails."""
        updater = ExecutableUpdater("test-owner", "test-repo")

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as old_file:
            old_file.write("original content")
            old_path = old_file.name

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as new_file:
            new_file.write("new content")
            new_path = new_file.name

        old_bak = f"{old_path}.old"

        try:
            with patch('os.name', 'nt'), patch('shutil.move', side_effect=OSError("Simulated disk full")):
                with pytest.raises(UpdateError) as exc_info:
                    updater.replace_executable(new_path, old_path)

                assert "Failed to replace executable" in str(exc_info.value)

            # Original file should be restored
            assert os.path.exists(old_path)
            with open(old_path, 'r') as f:
                assert f.read() == "original content"

            assert not os.path.exists(old_bak)

        finally:
            for p in [old_path, new_path, old_bak]:
                if os.path.exists(p):
                    os.remove(p)

    @patch('os.name', 'posix')
    @patch('os.chmod')
    def test_replace_executable_sets_permissions_unix(self, mock_chmod):
        """Test that executable permissions are set on Unix systems."""
        updater = ExecutableUpdater("test-owner", "test-repo")

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as old_file:
            old_file.write("old")
            old_path = old_file.name

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as new_file:
            new_file.write("new")
            new_path = new_file.name

        try:
            updater.replace_executable(new_path, old_path)
            assert mock_chmod.called

        finally:
            for p in [old_path, new_path, f"{old_path}.old"]:
                if os.path.exists(p):
                    os.remove(p)

    def test_replace_executable_cleans_up_on_failure(self):
        """Test that temporary files are cleaned up when replacement fails."""
        updater = ExecutableUpdater("test-owner", "test-repo")

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as old_file:
            old_file.write("old")
            old_path = old_file.name

        with tempfile.NamedTemporaryFile(delete=False, mode='w') as new_file:
            new_file.write("new")
            new_path = new_file.name

        old_bak = f"{old_path}.old"

        try:
            with patch('os.name', 'nt'), patch('shutil.move', side_effect=OSError("Disk full")):
                with pytest.raises(UpdateError):
                    updater.replace_executable(new_path, old_path)

            assert not os.path.exists(old_bak)
            assert os.path.exists(old_path)

        finally:
            for p in [old_path, new_path, old_bak]:
                if os.path.exists(p):
                    os.remove(p)
