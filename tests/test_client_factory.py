"""
Unit tests for client_factory module.

Feature: bedrock-provider-integration
Tests client factory functionality for creating OpenAI and Bedrock clients.
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

from shello_cli.api.client_factory import create_client, _create_openai_client, _create_bedrock_client
from shello_cli.utils.settings_manager import SettingsManager, UserSettings, ProviderConfig


class TestCreateClientOpenAI:
    """Unit tests for creating OpenAI clients."""
    
    def test_create_openai_client_with_api_key(self):
        """Test creating ShelloClient for provider='openai' with API key configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with OpenAI config
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="test-api-key-12345",
                base_url="https://api.openai.com/v1",
                default_model="gpt-4o"
            )
            
            settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client
            client = create_client(manager)
            
            # Verify it's a ShelloClient
            from shello_cli.api.openai_client import ShelloClient
            assert isinstance(client, ShelloClient)
            assert client.get_current_model() == "gpt-4o"
    
    def test_create_openai_client_with_legacy_api_key(self):
        """Test creating ShelloClient using legacy api_key field."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with legacy api_key (no openai_config)
            settings = UserSettings(
                provider="openai",
                api_key="legacy-api-key-12345",
                base_url="https://api.openai.com/v1",
                default_model="gpt-4o"
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client
            client = create_client(manager)
            
            # Verify it's a ShelloClient
            from shello_cli.api.openai_client import ShelloClient
            assert isinstance(client, ShelloClient)
    
    def test_create_openai_client_with_env_api_key(self):
        """Test creating ShelloClient with API key from environment variable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings without API key
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key=None,  # No API key in config
                default_model="gpt-4o"
            )
            
            settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Set environment variable
            os.environ['OPENAI_API_KEY'] = "env-api-key-12345"
            
            try:
                # Create client
                client = create_client(manager)
                
                # Verify it's a ShelloClient
                from shello_cli.api.openai_client import ShelloClient
                assert isinstance(client, ShelloClient)
            finally:
                del os.environ['OPENAI_API_KEY']
    
    def test_create_openai_client_missing_api_key_raises_error(self):
        """Test error when OpenAI API key is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Ensure no environment variable
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
            
            # Create settings without API key
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key=None,
                default_model="gpt-4o"
            )
            
            settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                create_client(manager)
            
            assert "OpenAI API key not configured" in str(exc_info.value)
            assert "OPENAI_API_KEY" in str(exc_info.value)
            assert "shello setup" in str(exc_info.value)


class TestCreateClientBedrock:
    """Unit tests for creating Bedrock clients."""
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_create_bedrock_client_with_profile(self, mock_boto3):
        """Test creating ShelloBedrockClient for provider='bedrock' with AWS profile."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_session.client.return_value = mock_client
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with Bedrock config
            bedrock_config = ProviderConfig(
                provider_type="bedrock",
                aws_region="us-east-1",
                aws_profile="my-profile",
                default_model="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )
            
            settings = UserSettings(
                provider="bedrock",
                bedrock_config=bedrock_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client
            client = create_client(manager)
            
            # Verify it's a ShelloBedrockClient
            from shello_cli.api.bedrock_client import ShelloBedrockClient
            assert isinstance(client, ShelloBedrockClient)
            assert client.get_current_model() == "anthropic.claude-3-5-sonnet-20241022-v2:0"
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_create_bedrock_client_with_explicit_credentials(self, mock_boto3):
        """Test creating ShelloBedrockClient with explicit AWS credentials."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with explicit credentials
            bedrock_config = ProviderConfig(
                provider_type="bedrock",
                aws_region="us-west-2",
                aws_access_key="AKIAIOSFODNN7EXAMPLE",
                aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                default_model="anthropic.claude-3-sonnet-20240229-v1:0"
            )
            
            settings = UserSettings(
                provider="bedrock",
                bedrock_config=bedrock_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client
            client = create_client(manager)
            
            # Verify it's a ShelloBedrockClient
            from shello_cli.api.bedrock_client import ShelloBedrockClient
            assert isinstance(client, ShelloBedrockClient)
    
    def test_create_bedrock_client_missing_config_raises_error(self):
        """Test error when Bedrock config is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings without bedrock_config
            settings = UserSettings(
                provider="bedrock",
                bedrock_config=None
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                create_client(manager)
            
            assert "Bedrock provider not configured" in str(exc_info.value)
            assert "shello setup" in str(exc_info.value)


class TestCreateClientBoto3Import:
    """Unit tests for boto3 import error handling."""
    
    def test_create_bedrock_client_boto3_not_installed(self):
        """Test error when boto3 is not installed and Bedrock is selected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with Bedrock config
            bedrock_config = ProviderConfig(
                provider_type="bedrock",
                aws_region="us-east-1",
                default_model="anthropic.claude-3-5-sonnet-20241022-v2:0"
            )
            
            settings = UserSettings(
                provider="bedrock",
                bedrock_config=bedrock_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Mock the import to raise ImportError
            with patch.dict(sys.modules, {'shello_cli.api.bedrock_client': None}):
                with patch('shello_cli.api.client_factory._create_bedrock_client') as mock_create:
                    mock_create.side_effect = ValueError(
                        "AWS Bedrock support requires boto3. "
                        "Install it with: pip install boto3"
                    )
                    
                    with pytest.raises(ValueError) as exc_info:
                        create_client(manager)
                    
                    assert "boto3" in str(exc_info.value)
                    assert "pip install boto3" in str(exc_info.value)


class TestCreateClientInvalidProvider:
    """Unit tests for invalid provider handling."""
    
    def test_create_client_invalid_provider_raises_error(self):
        """Test error when provider is invalid."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with invalid provider
            settings = UserSettings(provider="invalid_provider")
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Should raise ValueError
            with pytest.raises(ValueError) as exc_info:
                create_client(manager)
            
            assert "Unknown provider" in str(exc_info.value)
            assert "invalid_provider" in str(exc_info.value)
            assert "openai, bedrock" in str(exc_info.value)
            assert "shello setup" in str(exc_info.value)
    
    def test_create_client_with_provider_override(self):
        """Test creating client with explicit provider override."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings with both providers configured
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="test-api-key-12345",
                default_model="gpt-4o"
            )
            
            settings = UserSettings(
                provider="bedrock",  # Default is bedrock
                openai_config=openai_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client with explicit openai override
            client = create_client(manager, provider="openai")
            
            # Verify it's a ShelloClient (not Bedrock)
            from shello_cli.api.openai_client import ShelloClient
            assert isinstance(client, ShelloClient)


class TestCreateClientDefaultModel:
    """Unit tests for default model handling."""
    
    def test_create_openai_client_uses_default_model(self):
        """Test that OpenAI client uses default model when not specified."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings without default_model
            openai_config = ProviderConfig(
                provider_type="openai",
                api_key="test-api-key-12345",
                default_model=None  # No model specified
            )
            
            settings = UserSettings(
                provider="openai",
                openai_config=openai_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client
            client = create_client(manager)
            
            # Should use default model "gpt-4o"
            assert client.get_current_model() == "gpt-4o"
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_create_bedrock_client_uses_default_model(self, mock_boto3):
        """Test that Bedrock client uses default model when not specified."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = SettingsManager()
            manager._user_settings_path = Path(temp_dir) / "user-settings.json"
            manager._user_settings = None
            
            # Create settings without default_model
            bedrock_config = ProviderConfig(
                provider_type="bedrock",
                aws_region="us-east-1",
                default_model=None  # No model specified
            )
            
            settings = UserSettings(
                provider="bedrock",
                bedrock_config=bedrock_config
            )
            manager.save_user_settings(settings)
            manager._user_settings = None
            
            # Create client
            client = create_client(manager)
            
            # Should use default Bedrock model
            assert client.get_current_model() == "anthropic.claude-3-5-sonnet-20241022-v2:0"
