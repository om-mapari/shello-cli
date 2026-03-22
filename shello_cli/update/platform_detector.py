"""Platform detection for determining correct binary asset names."""

import platform
import sys
from typing import Dict

from shello_cli.update.exceptions import UnsupportedPlatformError


class PlatformDetector:
    """Detects platform and determines correct binary name for updates."""
    
    # Mapping from platform.system() output to normalized platform names
    PLATFORM_MAP: Dict[str, str] = {
        "Windows": "windows",
        "Linux": "linux",
        "Darwin": "macos",
    }
    
    # Mapping from normalized platform names to GitHub release asset names
    ASSET_MAP: Dict[str, str] = {
        "windows": "shello.exe",
        "linux": "shello",
        "macos": "shello-macos",
    }
    
    def get_platform(self) -> str:
        """Detect current platform.
        
        Returns:
            Platform string: "windows", "linux", or "macos"
            
        Raises:
            UnsupportedPlatformError: If platform is not supported
        """
        system = platform.system()
        
        if system not in self.PLATFORM_MAP:
            raise UnsupportedPlatformError(
                f"Unsupported platform: {system}. "
                f"Supported platforms: {', '.join(self.PLATFORM_MAP.keys())}"
            )
        
        return self.PLATFORM_MAP[system]
    
    def get_asset_name(self, platform: str) -> str:
        """Get GitHub release asset name for platform.
        
        Args:
            platform: Platform string from get_platform()
            
        Returns:
            Asset filename (e.g., "shello.exe", "shello", "shello-macos")
            
        Raises:
            UnsupportedPlatformError: If platform is not in asset map
        """
        if platform not in self.ASSET_MAP:
            raise UnsupportedPlatformError(
                f"No asset mapping for platform: {platform}"
            )
        
        return self.ASSET_MAP[platform]
    
    # Preferred install directory for user-managed updates on Windows
    WINDOWS_INSTALL_DIR = "~/.shello_cli"
    WINDOWS_EXE_NAME = "shello.exe"

    def get_executable_path(self) -> str:
        """Get path to write the updated executable.

        On Windows, sys.executable may point to a read-only WindowsApps stub.
        In that case (or when sys.argv[0] also points there), we redirect the
        install to ~/.shello_cli/shello.exe which is always user-writable.
        Subsequent runs from that path will update in-place normally.

        Returns:
            Absolute path where the executable should be written
        """
        import os

        candidate = sys.executable

        # Try sys.argv[0] first — PyInstaller sets this to the real exe path.
        # Only do this when actually frozen (PyInstaller sets sys.frozen),
        # otherwise sys.argv[0] points to the script/test runner, not the exe.
        if getattr(sys, "frozen", False) and sys.argv:
            argv0 = os.path.abspath(sys.argv[0])
            if os.path.isfile(argv0) and (sys.platform != "win32" or "WindowsApps" not in argv0):
                return argv0

        # On Windows, if we're still pointing at a WindowsApps stub, redirect
        # to a user-writable location instead of failing.
        if sys.platform == "win32" and "WindowsApps" in candidate:
            install_dir = os.path.expanduser(self.WINDOWS_INSTALL_DIR)
            os.makedirs(install_dir, exist_ok=True)
            return os.path.join(install_dir, self.WINDOWS_EXE_NAME)

        return candidate

    def is_windows_apps_install(self) -> bool:
        """Return True if currently running from a protected WindowsApps stub."""
        import os
        candidate = sys.executable
        argv0 = os.path.abspath(sys.argv[0]) if sys.argv else candidate
        return sys.platform == "win32" and (
            "WindowsApps" in candidate and "WindowsApps" in argv0
        )
