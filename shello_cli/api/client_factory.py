"""Factory for creating AI provider clients based on configuration.

This module provides a factory function that creates the appropriate client
(ShelloClient or ShelloBedrockClient) based on the provider configuration
in the settings manager.
"""

from typing import Union, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from shello_cli.settings import SettingsManager
    from shello_cli.api.openai_client import ShelloClient
    from shello_cli.api.bedrock_client import ShelloBedrockClient


def create_client(
    settings_manager: 'SettingsManager',
    provider: Optional[str] = None
) -> Union['ShelloClient', 'ShelloBedrockClient']:
    """Create an AI client based on provider configuration.
    
    This factory function reads the provider configuration from the settings
    manager and creates the appropriate client instance. It supports both
    OpenAI-compatible APIs and AWS Bedrock.
    
    Args:
        settings_manager: The settings manager instance containing provider configuration
        provider: Optional provider override (defaults to current provider in settings).
                 Valid values: "openai", "bedrock"
    
    Returns:
        ShelloClient for OpenAI-compatible APIs or ShelloBedrockClient for AWS Bedrock
    
    Raises:
        ValueError: If provider is invalid, configuration is incomplete, or
                   required dependencies are not installed
    
    Examples:
        >>> from shello_cli.settings import SettingsManager
        >>> settings = SettingsManager.get_instance()
        >>> client = create_client(settings)  # Uses current provider
        >>> client = create_client(settings, provider="bedrock")  # Force Bedrock
    """
    # Determine which provider to use
    target_provider = provider or settings_manager.get_provider()
    
    if target_provider == "openai":
        return _create_openai_client(settings_manager)
    
    elif target_provider == "bedrock":
        return _create_bedrock_client(settings_manager)
    
    else:
        raise ValueError(
            f"Unknown provider: '{target_provider}'. "
            f"Supported providers: openai, bedrock. "
            f"Run 'shello setup' to configure a valid provider."
        )


def _create_openai_client(settings_manager: 'SettingsManager') -> 'ShelloClient':
    """Create an OpenAI-compatible client.
    
    Args:
        settings_manager: The settings manager instance
        
    Returns:
        Configured ShelloClient instance
        
    Raises:
        ValueError: If API key is not configured
    """
    from shello_cli.api.openai_client import ShelloClient
    
    # Get OpenAI configuration
    try:
        config = settings_manager.get_provider_config("openai")
    except ValueError as e:
        raise ValueError(
            "OpenAI provider not configured. "
            "Set OPENAI_API_KEY environment variable or run 'shello setup'."
        ) from e
    
    # Validate API key
    api_key = config.get("api_key")
    if not api_key:
        raise ValueError(
            "OpenAI API key not configured. "
            "Set OPENAI_API_KEY environment variable or run 'shello setup'."
        )
    
    # Get optional configuration
    base_url = config.get("base_url")
    model = config.get("model", "gpt-4o")
    
    # Create and return the client
    return ShelloClient(
        api_key=api_key,
        model=model,
        base_url=base_url if base_url else None
    )


def _create_bedrock_client(settings_manager: 'SettingsManager') -> 'ShelloBedrockClient':
    """Create an AWS Bedrock client.
    
    Args:
        settings_manager: The settings manager instance
        
    Returns:
        Configured ShelloBedrockClient instance
        
    Raises:
        ValueError: If boto3 is not installed or Bedrock is not configured
    """
    # Check if boto3 is available
    try:
        from shello_cli.api.bedrock_client import ShelloBedrockClient
    except ImportError as e:
        # Check if it's specifically boto3 that's missing
        if "boto3" in str(e) or "botocore" in str(e):
            raise ValueError(
                "AWS Bedrock support requires boto3. "
                "Install it with: uv pip install boto3 (or pip install boto3)"
            ) from e
        raise
    
    # Get Bedrock configuration
    try:
        config = settings_manager.get_provider_config("bedrock")
    except ValueError as e:
        raise ValueError(
            "Bedrock provider not configured. "
            "Run 'shello setup' to configure AWS Bedrock credentials."
        ) from e
    
    # Extract configuration values
    region = config.get("region") or "us-east-1"
    profile = config.get("profile")
    access_key = config.get("access_key")
    secret_key = config.get("secret_key")
    model = config.get("model", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    
    # Create and return the client
    return ShelloBedrockClient(
        model=model,
        region=region,
        aws_access_key=access_key,
        aws_secret_key=secret_key,
        aws_profile=profile
    )
