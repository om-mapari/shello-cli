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
    
    def get_executable_path(self) -> str:
        """Get path to currently running executable.
        
        Returns:
            Absolute path to current executable
        """
        return sys.executable
