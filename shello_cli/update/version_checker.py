"""Version checking functionality for Shello CLI updates."""

from typing import Optional

import requests
from packaging.version import Version, InvalidVersion


class VersionChecker:
    """Checks for available updates from GitHub releases."""

    def __init__(self, repo_owner: str, repo_name: str, timeout: int = 5):
        """Initialize version checker.

        Args:
            repo_owner: GitHub repository owner (e.g., "om-mapari")
            repo_name: GitHub repository name (e.g., "shello-cli")
            timeout: HTTP request timeout in seconds
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.timeout = timeout
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"

    def get_current_version(self) -> str:
        """Get current version from shello_cli.__init__.

        Returns:
            Current version string (e.g., "0.4.3")

        Raises:
            ValueError: If version cannot be determined
        """
        try:
            # Import version directly from the module
            # This works in both regular Python and PyInstaller frozen executables
            import shello_cli
            version = shello_cli.__version__
            
            if not version:
                raise ValueError("__version__ is empty")
            
            return version
        except (ImportError, AttributeError) as e:
            raise ValueError(f"Could not determine current version: {e}")

    def get_latest_version(self) -> Optional[str]:
        """Query GitHub API for latest release version.

        Returns:
            Latest version string or None if check fails

        Raises:
            requests.RequestException: On network errors
        """
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            tag_name = data.get("tag_name", "")

            # Remove 'v' prefix if present (e.g., "v1.2.3" -> "1.2.3")
            if tag_name.startswith("v"):
                tag_name = tag_name[1:]

            return tag_name if tag_name else None

        except requests.RequestException:
            # Network errors should be handled gracefully
            return None
        except (KeyError, ValueError):
            # Malformed JSON response
            return None

    def compare_versions(self, current: str, latest: str) -> bool:
        """Compare two semantic version strings.

        Args:
            current: Current version string
            latest: Latest version string

        Returns:
            True if latest > current, False otherwise

        Raises:
            InvalidVersion: If either version string is invalid
        """
        try:
            current_ver = Version(current)
            latest_ver = Version(latest)
            return latest_ver > current_ver
        except InvalidVersion as e:
            raise InvalidVersion(f"Invalid version format: {e}")

    def is_update_available(self) -> tuple[bool, Optional[str], Optional[str]]:
        """Check if an update is available.

        Returns:
            Tuple of (update_available, current_version, latest_version)
            - update_available: True if latest > current
            - current_version: Current version string
            - latest_version: Latest version string or None if check failed
        """
        try:
            current_version = self.get_current_version()
        except ValueError:
            # Can't determine current version
            return (False, None, None)

        latest_version = self.get_latest_version()

        if latest_version is None:
            # Network error or API failure
            return (False, current_version, None)

        try:
            update_available = self.compare_versions(current_version, latest_version)
            return (update_available, current_version, latest_version)
        except InvalidVersion:
            # Invalid version format
            return (False, current_version, latest_version)
