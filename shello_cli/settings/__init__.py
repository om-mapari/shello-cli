"""
Settings management module for Shello CLI.

This module provides a clean public API for accessing and managing
configuration settings across user and project scopes.

Public API:
    - SettingsManager: Main settings management class
    - get_settings(): Get the current settings instance
    - get_api_key(): Get API key for the active provider
    - get_current_model(): Get the current model for the active provider
    
Data Models:
    - UserSettings: User-level configuration
    - ProjectSettings: Project-level configuration
    - ProviderConfig: Provider-specific configuration
    - OutputManagementConfig: Output truncation settings
    - CommandTrustConfig: Command approval settings
"""

from .models import (
    ProviderConfig,
    OutputManagementConfig,
    CommandTrustConfig,
    UserSettings,
    ProjectSettings,
)
from .manager import SettingsManager

__all__ = [
    # Main class
    "SettingsManager",
    # Data models
    "ProviderConfig",
    "OutputManagementConfig",
    "CommandTrustConfig",
    "UserSettings",
    "ProjectSettings",
    # Helper functions
    "get_settings",
    "get_api_key",
    "get_current_model",
]


def get_settings() -> UserSettings:
    """
    Get the current settings instance.
    
    This is a convenience function that returns the singleton SettingsManager
    instance's current settings.
    
    Returns:
        UserSettings: The current user settings
    """
    return SettingsManager.get_instance().load_user_settings()


def get_api_key(provider: str = None) -> str:
    """
    Get the API key for the specified provider (or active provider).
    
    This function checks the configuration first, then falls back to
    environment variables if the key is not in the config.
    
    Args:
        provider: Provider name (openai, bedrock, etc.). If None, uses active provider.
        
    Returns:
        str: The API key or None if not found
    """
    config = SettingsManager.get_instance().get_provider_config(provider)
    return config.get('api_key')


def get_current_model(provider: str = None) -> str:
    """
    Get the current model for the specified provider (or active provider).
    
    Args:
        provider: Provider name (openai, bedrock, etc.). If None, uses active provider.
        
    Returns:
        str: The model identifier
    """
    config = SettingsManager.get_instance().get_provider_config(provider)
    return config.get('model')
