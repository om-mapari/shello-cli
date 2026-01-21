"""Tests for the UpdateManager component."""

import threading
from unittest.mock import Mock, patch, MagicMock

import pytest

from shello_cli.update.update_manager import (
    UpdateManager,
    UpdateCheckResult,
    UpdateResult,
)
from shello_cli.update.exceptions import UpdateError, UnsupportedPlatformError


class TestUpdateCheckResult:
    """Test suite for UpdateCheckResult dataclass."""

    def test_update_check_result_creation(self):
        """Test creating UpdateCheckResult."""
        result = UpdateCheckResult(
            update_available=True,
            current_version="1.0.0",
            latest_version="1.1.0",
            error=None
        )
        
        assert result.update_available is True
        assert result.current_version == "1.0.0"
        assert result.latest_version == "1.1.0"
        assert result.error is None

    def test_update_check_result_with_error(self):
        """Test UpdateCheckResult with error."""
        result = UpdateCheckResult(
            update_available=False,
            current_version="1.0.0",
            latest_version=None,
            error="Network error"
        )
        
        assert result.update_available is False
        assert result.error == "Network error"


class TestUpdateResult:
    """Test suite for UpdateResult dataclass."""

    def test_update_result_success(self):
        """Test creating successful UpdateResult."""
        result = UpdateResult(
            success=True,
            message="Update completed",
            new_version="1.1.0",
            error=None
        )
        
        assert result.success is True
        assert result.message == "Update completed"
        assert result.new_version == "1.1.0"
        assert result.error is None

    def test_update_result_failure(self):
        """Test creating failed UpdateResult."""
        result = UpdateResult(
            success=False,
            message="Update failed",
            new_version=None,
            error="Download error"
        )
        
        assert result.success is False
        assert result.error == "Download error"


class TestUpdateManager:
    """Test suite for UpdateManager class."""

    def test_init_default_repo(self):
        """Test UpdateManager initialization with default repo."""
        manager = UpdateManager()
        
        assert manager.repo_owner == "om-mapari"
        assert manager.repo_name == "shello-cli"
        assert manager.version_checker is not None
        assert manager.platform_detector is not None
        assert manager.executable_updater is not None

    def test_init_custom_repo(self):
        """Test UpdateManager initialization with custom repo."""
        manager = UpdateManager(repo_owner="custom", repo_name="repo")
        
        assert manager.repo_owner == "custom"
        assert manager.repo_name == "repo"

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_update_available(self, mock_checker_class):
        """Test check_for_updates when update is available."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates()
        
        assert result.update_available is True
        assert result.current_version == "1.0.0"
        assert result.latest_version == "1.1.0"
        assert result.error is None

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_no_update(self, mock_checker_class):
        """Test check_for_updates when no update is available."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (False, "1.1.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates()
        
        assert result.update_available is False
        assert result.current_version == "1.1.0"
        assert result.latest_version == "1.1.0"
        assert result.error is None

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_current_version_unknown(self, mock_checker_class):
        """Test check_for_updates when current version cannot be determined."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (False, None, None)
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates()
        
        assert result.update_available is False
        assert result.current_version == "unknown"
        assert result.latest_version is None
        assert result.error == "Could not determine current version"

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_network_error(self, mock_checker_class):
        """Test check_for_updates when network check fails."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (False, "1.0.0", None)
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates()
        
        assert result.update_available is False
        assert result.current_version == "1.0.0"
        assert result.latest_version is None
        assert "internet connection" in result.error

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_exception(self, mock_checker_class):
        """Test check_for_updates when an exception occurs."""
        mock_checker = Mock()
        mock_checker.is_update_available.side_effect = Exception("Unexpected error")
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates()
        
        assert result.update_available is False
        assert result.current_version == "unknown"
        assert "Update check failed" in result.error

    @patch("shello_cli.update.update_manager.VersionChecker")
    @patch("shello_cli.update.update_manager.PlatformDetector")
    @patch("shello_cli.update.update_manager.ExecutableUpdater")
    @patch("shello_cli.update.update_manager.Console")
    @patch("shello_cli.update.update_manager.Progress")
    def test_perform_update_success(self, mock_progress_class, mock_console_class, 
                                    mock_updater_class, mock_detector_class, mock_checker_class):
        """Test successful update process."""
        # Mock version checker
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        # Mock platform detector
        mock_detector = Mock()
        mock_detector.get_platform.return_value = "linux"
        mock_detector.get_asset_name.return_value = "shello"
        mock_detector.get_executable_path.return_value = "/usr/bin/shello"
        mock_detector_class.return_value = mock_detector
        
        # Mock executable updater
        mock_updater = Mock()
        mock_updater.download_binary.return_value = "/tmp/shello"
        mock_updater.verify_binary.return_value = True
        mock_updater.replace_executable.return_value = None
        mock_updater_class.return_value = mock_updater
        
        # Mock console
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        # Mock Progress context manager
        mock_progress = MagicMock()
        mock_progress.__enter__ = Mock(return_value=mock_progress)
        mock_progress.__exit__ = Mock(return_value=False)
        mock_progress.add_task = Mock(return_value=0)
        mock_progress_class.return_value = mock_progress
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is True
        assert result.new_version == "1.1.0"
        assert "successfully" in result.message.lower()
        
        # Verify download was called
        mock_updater.download_binary.assert_called_once()
        mock_updater.verify_binary.assert_called_once()
        mock_updater.replace_executable.assert_called_once()

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_perform_update_already_latest(self, mock_checker_class):
        """Test update when already on latest version."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (False, "1.1.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is True
        assert "already on the latest version" in result.message
        assert result.new_version == "1.1.0"

    @patch("shello_cli.update.update_manager.VersionChecker")
    @patch("shello_cli.update.update_manager.Console")
    @patch("shello_cli.update.update_manager.Progress")
    def test_perform_update_force_flag(self, mock_progress_class, mock_console_class, mock_checker_class):
        """Test force flag behavior."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (False, "1.1.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        # Mock Progress context manager
        mock_progress = MagicMock()
        mock_progress.__enter__ = Mock(return_value=mock_progress)
        mock_progress.__exit__ = Mock(return_value=False)
        mock_progress.add_task = Mock(return_value=0)
        mock_progress_class.return_value = mock_progress
        
        manager = UpdateManager()
        
        # Force should skip the "already latest" check
        # We need to mock the rest of the update process
        with patch.object(manager.platform_detector, 'get_platform', return_value='linux'), \
             patch.object(manager.platform_detector, 'get_asset_name', return_value='shello'), \
             patch.object(manager.platform_detector, 'get_executable_path', return_value='/usr/bin/shello'), \
             patch.object(manager.executable_updater, 'download_binary', return_value='/tmp/shello'), \
             patch.object(manager.executable_updater, 'verify_binary', return_value=True), \
             patch.object(manager.executable_updater, 'replace_executable', return_value=None):
            
            result = manager.perform_update(force=True)
            
            # With force, it should attempt the update
            assert result.success is True

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_perform_update_check_error(self, mock_checker_class):
        """Test update when version check fails."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (False, "1.0.0", None)
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is False
        assert "Update check failed" in result.message

    @patch("shello_cli.update.update_manager.VersionChecker")
    @patch("shello_cli.update.update_manager.PlatformDetector")
    @patch("shello_cli.update.update_manager.Console")
    def test_perform_update_unsupported_platform(self, mock_console_class, 
                                                 mock_detector_class, mock_checker_class):
        """Test update on unsupported platform."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        mock_detector = Mock()
        mock_detector.get_platform.side_effect = UnsupportedPlatformError("Unsupported")
        mock_detector_class.return_value = mock_detector
        
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is False
        assert "Platform not supported" in result.message

    @patch("shello_cli.update.update_manager.VersionChecker")
    @patch("shello_cli.update.update_manager.PlatformDetector")
    @patch("shello_cli.update.update_manager.ExecutableUpdater")
    @patch("shello_cli.update.update_manager.Console")
    def test_perform_update_download_failure(self, mock_console_class, mock_updater_class,
                                            mock_detector_class, mock_checker_class):
        """Test update when download fails."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        mock_detector = Mock()
        mock_detector.get_platform.return_value = "linux"
        mock_detector.get_asset_name.return_value = "shello"
        mock_detector_class.return_value = mock_detector
        
        mock_updater = Mock()
        mock_updater.download_binary.side_effect = Exception("Download failed")
        mock_updater_class.return_value = mock_updater
        
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is False
        assert "Download failed" in result.message

    @patch("shello_cli.update.update_manager.VersionChecker")
    @patch("shello_cli.update.update_manager.PlatformDetector")
    @patch("shello_cli.update.update_manager.ExecutableUpdater")
    @patch("shello_cli.update.update_manager.Console")
    @patch("shello_cli.update.update_manager.Progress")
    def test_perform_update_verification_failure(self, mock_progress_class, mock_console_class, 
                                                 mock_updater_class, mock_detector_class, mock_checker_class):
        """Test update when binary verification fails."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        mock_detector = Mock()
        mock_detector.get_platform.return_value = "linux"
        mock_detector.get_asset_name.return_value = "shello"
        mock_detector_class.return_value = mock_detector
        
        mock_updater = Mock()
        mock_updater.download_binary.return_value = "/tmp/shello"
        mock_updater.verify_binary.return_value = False
        mock_updater_class.return_value = mock_updater
        
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        # Mock Progress context manager
        mock_progress = MagicMock()
        mock_progress.__enter__ = Mock(return_value=mock_progress)
        mock_progress.__exit__ = Mock(return_value=False)
        mock_progress.add_task = Mock(return_value=0)
        mock_progress_class.return_value = mock_progress
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is False
        assert "verification failed" in result.message.lower()

    @patch("shello_cli.update.update_manager.VersionChecker")
    @patch("shello_cli.update.update_manager.PlatformDetector")
    @patch("shello_cli.update.update_manager.ExecutableUpdater")
    @patch("shello_cli.update.update_manager.Console")
    @patch("shello_cli.update.update_manager.Progress")
    def test_perform_update_replacement_failure(self, mock_progress_class, mock_console_class, 
                                               mock_updater_class, mock_detector_class, mock_checker_class):
        """Test update when executable replacement fails."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        mock_detector = Mock()
        mock_detector.get_platform.return_value = "linux"
        mock_detector.get_asset_name.return_value = "shello"
        mock_detector.get_executable_path.return_value = "/usr/bin/shello"
        mock_detector_class.return_value = mock_detector
        
        mock_updater = Mock()
        mock_updater.download_binary.return_value = "/tmp/shello"
        mock_updater.verify_binary.return_value = True
        mock_updater.replace_executable.side_effect = UpdateError("Permission denied")
        mock_updater_class.return_value = mock_updater
        
        mock_console = Mock()
        mock_console_class.return_value = mock_console
        
        # Mock Progress context manager
        mock_progress = MagicMock()
        mock_progress.__enter__ = Mock(return_value=mock_progress)
        mock_progress.__exit__ = Mock(return_value=False)
        mock_progress.add_task = Mock(return_value=0)
        mock_progress_class.return_value = mock_progress
        
        manager = UpdateManager()
        result = manager.perform_update()
        
        assert result.success is False
        assert "Failed to replace executable" in result.message

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_async_success(self, mock_checker_class):
        """Test async update check with successful result."""
        mock_checker = Mock()
        mock_checker.is_update_available.return_value = (True, "1.0.0", "1.1.0")
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates_async(timeout=5.0)
        
        assert result is not None
        assert result.update_available is True
        assert result.current_version == "1.0.0"
        assert result.latest_version == "1.1.0"

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_async_timeout(self, mock_checker_class):
        """Test async update check with timeout."""
        mock_checker = Mock()
        
        # Simulate a slow check that exceeds timeout
        def slow_check():
            import time
            time.sleep(5)
            return (True, "1.0.0", "1.1.0")
        
        mock_checker.is_update_available.side_effect = slow_check
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        result = manager.check_for_updates_async(timeout=0.1)
        
        # Should return None on timeout
        assert result is None

    @patch("shello_cli.update.update_manager.VersionChecker")
    def test_check_for_updates_async_exception(self, mock_checker_class):
        """Test async update check when exception occurs in thread."""
        mock_checker = Mock()
        
        # Make check_for_updates itself raise an exception (not is_update_available)
        def raise_exception():
            raise Exception("Network error")
        
        # We need to patch check_for_updates to raise
        mock_checker_class.return_value = mock_checker
        
        manager = UpdateManager()
        
        # Patch check_for_updates to raise an exception
        with patch.object(manager, 'check_for_updates', side_effect=Exception("Network error")):
            result = manager.check_for_updates_async(timeout=5.0)
            
            # Should return None on exception (silent failure)
            assert result is None
