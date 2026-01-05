"""
DEPRECATED: This module is deprecated and maintained only for backward compatibility.

Please import from shello_cli.settings instead:
    from shello_cli.settings import SettingsManager, UserSettings, ProviderConfig, etc.

This module re-exports all classes and functions from the new settings module.
"""

# Re-export everything from the new settings module for backward compatibility
from shello_cli.settings.manager import SettingsManager
from shello_cli.settings.models import (
    UserSettings,
    ProjectSettings,
    ProviderConfig,
    OutputManagementConfig,
    CommandTrustConfig,
    FirstLastRatioConfig,
    SemanticConfig,
    CompressionConfig,
    CacheConfig,
)

__all__ = [
    "SettingsManager",
    "UserSettings",
    "ProjectSettings",
    "ProviderConfig",
    "OutputManagementConfig",
    "CommandTrustConfig",
    "FirstLastRatioConfig",
    "SemanticConfig",
    "CompressionConfig",
    "CacheConfig",
]
