"""Tests for the PlatformDetector component."""

import sys
from unittest.mock import patch

import pytest

from shello_cli.update.platform_detector import PlatformDetector
from shello_cli.update.exceptions import UnsupportedPlatformError


class TestPlatformDetector:
    """Test suite for PlatformDetector class."""

    def test_init(self):
        """Test PlatformDetector initialization."""
        detector = PlatformDetector()
        assert detector is not None
        assert hasattr(detector, 'PLATFORM_MAP')
        assert hasattr(detector, 'ASSET_MAP')

    @patch("platform.system")
    def test_get_platform_windows(self, mock_system):
        """Test platform detection for Windows."""
        mock_system.return_value = "Windows"
        
        detector = PlatformDetector()
        platform = detector.get_platform()
        
        assert platform == "windows"

    @patch("platform.system")
    def test_get_platform_linux(self, mock_system):
        """Test platform detection for Linux."""
        mock_system.return_value = "Linux"
        
        detector = PlatformDetector()
        platform = detector.get_platform()
        
        assert platform == "linux"

    @patch("platform.system")
    def test_get_platform_macos(self, mock_system):
        """Test platform detection for macOS."""
        mock_system.return_value = "Darwin"
        
        detector = PlatformDetector()
        platform = detector.get_platform()
        
        assert platform == "macos"

    @patch("platform.system")
    def test_get_platform_unsupported(self, mock_system):
        """Test error handling for unsupported platforms."""
        mock_system.return_value = "FreeBSD"
        
        detector = PlatformDetector()
        
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            detector.get_platform()
        
        assert "Unsupported platform: FreeBSD" in str(exc_info.value)
        assert "Supported platforms:" in str(exc_info.value)

    def test_get_asset_name_windows(self):
        """Test asset name for Windows platform."""
        detector = PlatformDetector()
        asset = detector.get_asset_name("windows")
        
        assert asset == "shello.exe"

    def test_get_asset_name_linux(self):
        """Test asset name for Linux platform."""
        detector = PlatformDetector()
        asset = detector.get_asset_name("linux")
        
        assert asset == "shello"

    def test_get_asset_name_macos(self):
        """Test asset name for macOS platform."""
        detector = PlatformDetector()
        asset = detector.get_asset_name("macos")
        
        assert asset == "shello-macos"

    def test_get_asset_name_invalid_platform(self):
        """Test error handling for invalid platform in asset mapping."""
        detector = PlatformDetector()
        
        with pytest.raises(UnsupportedPlatformError) as exc_info:
            detector.get_asset_name("invalid_platform")
        
        assert "No asset mapping for platform: invalid_platform" in str(exc_info.value)

    def test_get_executable_path(self):
        """Test getting current executable path."""
        detector = PlatformDetector()
        path = detector.get_executable_path()
        
        # Should return sys.executable
        assert path == sys.executable
        assert isinstance(path, str)
        assert len(path) > 0

    @patch("platform.system")
    def test_platform_to_asset_mapping_windows(self, mock_system):
        """Test complete flow from platform detection to asset name for Windows."""
        mock_system.return_value = "Windows"
        
        detector = PlatformDetector()
        platform = detector.get_platform()
        asset = detector.get_asset_name(platform)
        
        assert platform == "windows"
        assert asset == "shello.exe"

    @patch("platform.system")
    def test_platform_to_asset_mapping_linux(self, mock_system):
        """Test complete flow from platform detection to asset name for Linux."""
        mock_system.return_value = "Linux"
        
        detector = PlatformDetector()
        platform = detector.get_platform()
        asset = detector.get_asset_name(platform)
        
        assert platform == "linux"
        assert asset == "shello"

    @patch("platform.system")
    def test_platform_to_asset_mapping_macos(self, mock_system):
        """Test complete flow from platform detection to asset name for macOS."""
        mock_system.return_value = "Darwin"
        
        detector = PlatformDetector()
        platform = detector.get_platform()
        asset = detector.get_asset_name(platform)
        
        assert platform == "macos"
        assert asset == "shello-macos"

    def test_platform_map_completeness(self):
        """Test that all platforms in PLATFORM_MAP have corresponding assets."""
        detector = PlatformDetector()
        
        for system_name, normalized_name in detector.PLATFORM_MAP.items():
            assert normalized_name in detector.ASSET_MAP, \
                f"Platform '{normalized_name}' from PLATFORM_MAP not found in ASSET_MAP"

    def test_asset_map_values_are_strings(self):
        """Test that all asset names are non-empty strings."""
        detector = PlatformDetector()
        
        for platform, asset_name in detector.ASSET_MAP.items():
            assert isinstance(asset_name, str), \
                f"Asset name for '{platform}' is not a string"
            assert len(asset_name) > 0, \
                f"Asset name for '{platform}' is empty"
