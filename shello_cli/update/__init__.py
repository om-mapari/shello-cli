"""Self-update functionality for Shello CLI.

This module provides components for checking and performing updates
to standalone executable installations from GitHub releases.
"""

from shello_cli.update.exceptions import (
    UpdateError,
    DownloadError,
    UnsupportedPlatformError,
)
from shello_cli.update.version_checker import VersionChecker
from shello_cli.update.platform_detector import PlatformDetector
from shello_cli.update.executable_updater import ExecutableUpdater
from shello_cli.update.update_manager import (
    UpdateManager,
    UpdateCheckResult,
    UpdateResult,
)

__all__ = [
    "UpdateError",
    "DownloadError",
    "UnsupportedPlatformError",
    "VersionChecker",
    "PlatformDetector",
    "ExecutableUpdater",
    "UpdateManager",
    "UpdateCheckResult",
    "UpdateResult",
]
