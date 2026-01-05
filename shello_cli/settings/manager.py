"""
Settings manager for loading, saving, and accessing configuration.

This module provides the SettingsManager class which handles:
- Loading user settings from ~/.shello_cli/user-settings.yml
- Merging user settings with defaults from defaults.py
- Saving settings with helpful YAML comments
- Environment variable fallback for credentials
- Validation with fallback to safe defaults
"""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import asdict

from shello_cli.patterns import APP_DIR
from shello_cli.defaults import (
    DEFAULT_CHAR_LIMITS,
    DEFAULT_STRATEGIES,
    DEFAULT_FIRST_RATIO,
    DEFAULT_LAST_RATIO,
    DEFAULT_CACHE_MAX_SIZE_MB,
    DEFAULT_ALLOWLIST,
    DEFAULT_DENYLIST,
    DEFAULT_APPROVAL_MODE,
    DEFAULT_PROVIDER_CONFIGS,
)
from shello_cli.settings.models import (
    UserSettings,
    ProviderConfig,
    OutputManagementConfig,
    CommandTrustConfig,
    ProjectSettings,
)
from shello_cli.settings.serializers import generate_yaml_with_comments


class SettingsManager:
    """Manages user and project settings with singleton pattern."""
    
    _instance: Optional['SettingsManager'] = None
    
    def __init__(self):
        """Initialize settings manager."""
        self._user_settings_path = APP_DIR / "user-settings.yml"
        self._project_settings_path = Path.cwd() / ".shello" / "settings.json"
        self._user_settings: Optional[UserSettings] = None
        self._project_settings: Optional['ProjectSettings'] = None
    
    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        """Get singleton instance of SettingsManager.
        
        Returns:
            The singleton SettingsManager instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_user_settings(self) -> UserSettings:
        """Load user settings from file, merge with defaults, and cache in memory.
        
        This method:
        1. Returns cached settings if already loaded
        2. Loads from ~/.shello_cli/user-settings.yml if it exists
        3. Merges user values with defaults from defaults.py
        4. Validates configuration and falls back to defaults on errors
        5. Caches the result in memory
        
        Returns:
            UserSettings object with merged configuration
            
        Requirements: 2.1, 2.2, 2.4, 8.4
        """
        # Return cached settings if available
        if self._user_settings is not None:
            return self._user_settings
        
        # If file doesn't exist, return defaults
        if not self._user_settings_path.exists():
            self._user_settings = self._create_default_settings()
            return self._user_settings
        
        try:
            # Load YAML file with UTF-8 encoding
            with open(self._user_settings_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Handle empty file
            if data is None:
                data = {}
            
            # Parse and merge settings
            self._user_settings = self._parse_user_settings(data)
            return self._user_settings
            
        except (yaml.YAMLError, IOError) as e:
            # If file is corrupted or unreadable, return defaults
            print(f"Warning: Could not load settings file: {e}")
            print("Using default settings.")
            self._user_settings = self._create_default_settings()
            return self._user_settings
    
    def _create_default_settings(self) -> UserSettings:
        """Create UserSettings with all defaults.
        
        Returns:
            UserSettings with default values from defaults.py
        """
        return UserSettings(
            provider="openai",
            openai_config=None,
            bedrock_config=None,
            gemini_config=None,
            vertex_config=None,
            output_management=None,
            command_trust=None,
        )
    
    def _parse_user_settings(self, data: Dict[str, Any]) -> UserSettings:
        """Parse user settings data and merge with defaults.
        
        Args:
            data: Dictionary loaded from YAML file
            
        Returns:
            UserSettings with merged configuration
        """
        # Validate and get provider
        provider = self._validate_provider(data.get('provider', 'openai'))
        
        # Parse provider configs
        openai_config = self._parse_provider_config(data.get('openai_config'), 'openai')
        bedrock_config = self._parse_provider_config(data.get('bedrock_config'), 'bedrock')
        gemini_config = self._parse_provider_config(data.get('gemini_config'), 'gemini')
        vertex_config = self._parse_provider_config(data.get('vertex_config'), 'vertex')
        
        # Parse output management config
        output_management = self._parse_output_management(data.get('output_management'))
        
        # Parse command trust config
        command_trust = self._parse_command_trust(data.get('command_trust'))
        
        return UserSettings(
            provider=provider,
            openai_config=openai_config,
            bedrock_config=bedrock_config,
            gemini_config=gemini_config,
            vertex_config=vertex_config,
            output_management=output_management,
            command_trust=command_trust,
        )
    
    def _validate_provider(self, provider: str) -> str:
        """Validate provider value and fall back to default if invalid.
        
        Args:
            provider: Provider string to validate
            
        Returns:
            Valid provider string
            
        Requirements: 3.1, 3.3, 3.5
        """
        valid_providers = ['openai', 'bedrock', 'gemini', 'vertex']
        if provider not in valid_providers:
            print(f"Warning: Invalid provider '{provider}'. Using default 'openai'.")
            return 'openai'
        return provider
    
    def _parse_provider_config(
        self, 
        config_data: Optional[Dict[str, Any]], 
        provider_type: str
    ) -> Optional[ProviderConfig]:
        """Parse provider configuration from data.
        
        Args:
            config_data: Dictionary with provider config or None
            provider_type: Type of provider (openai, bedrock, etc.)
            
        Returns:
            ProviderConfig object or None if not configured
        """
        if config_data is None:
            return None
        
        return ProviderConfig(
            provider_type=config_data.get('provider_type', provider_type),
            api_key=config_data.get('api_key'),
            base_url=config_data.get('base_url'),
            aws_region=config_data.get('aws_region'),
            aws_profile=config_data.get('aws_profile'),
            aws_access_key=config_data.get('aws_access_key'),
            aws_secret_key=config_data.get('aws_secret_key'),
            default_model=config_data.get('default_model'),
            models=config_data.get('models', []),
        )
    
    def _parse_output_management(
        self, 
        om_data: Optional[Dict[str, Any]]
    ) -> Optional[OutputManagementConfig]:
        """Parse output management configuration and merge with defaults.
        
        Args:
            om_data: Dictionary with output management config or None
            
        Returns:
            OutputManagementConfig with merged defaults or None
            
        Requirements: 2.1, 2.4
        """
        if om_data is None:
            return None
        
        # Merge user limits with defaults
        limits = DEFAULT_CHAR_LIMITS.copy()
        if 'limits' in om_data:
            limits.update(om_data['limits'])
        
        # Merge user strategies with defaults
        strategies = DEFAULT_STRATEGIES.copy()
        if 'strategies' in om_data:
            strategies.update(om_data['strategies'])
        
        # Parse nested configs
        from shello_cli.settings.models import FirstLastRatioConfig, SemanticConfig, CompressionConfig, CacheConfig
        
        first_last_ratio = FirstLastRatioConfig()
        if 'first_last_ratio' in om_data:
            flr = om_data['first_last_ratio']
            first_last_ratio = FirstLastRatioConfig(
                first=flr.get('first', DEFAULT_FIRST_RATIO),
                last=flr.get('last', DEFAULT_LAST_RATIO)
            )
        
        semantic = SemanticConfig()
        if 'semantic' in om_data:
            sem = om_data['semantic']
            semantic = SemanticConfig(
                enabled=sem.get('enabled', True),
                always_show_critical=sem.get('always_show_critical', True)
            )
        
        compression = CompressionConfig()
        if 'compression' in om_data:
            comp = om_data['compression']
            compression = CompressionConfig(
                enabled=comp.get('enabled', True)
            )
        
        cache = CacheConfig()
        if 'cache' in om_data:
            c = om_data['cache']
            cache = CacheConfig(
                enabled=c.get('enabled', True),
                max_size_mb=c.get('max_size_mb', DEFAULT_CACHE_MAX_SIZE_MB)
            )
        
        return OutputManagementConfig(
            enabled=om_data.get('enabled', True),
            show_summary=om_data.get('show_summary', True),
            limits=limits,
            strategies=strategies,
            first_last_ratio=first_last_ratio,
            semantic=semantic,
            compression=compression,
            cache=cache,
        )
    
    def _parse_command_trust(
        self, 
        ct_data: Optional[Dict[str, Any]]
    ) -> Optional[CommandTrustConfig]:
        """Parse command trust configuration and merge with defaults.
        
        Args:
            ct_data: Dictionary with command trust config or None
            
        Returns:
            CommandTrustConfig with merged defaults or None
            
        Requirements: 2.1, 2.4, 7.2, 7.3
        """
        if ct_data is None:
            return None
        
        # Validate approval_mode
        approval_mode = self._validate_approval_mode(
            ct_data.get('approval_mode', DEFAULT_APPROVAL_MODE)
        )
        
        # Allowlist: User can override defaults completely
        allowlist = DEFAULT_ALLOWLIST.copy()
        if 'allowlist' in ct_data:
            allowlist = ct_data['allowlist']
        
        # Denylist: ALWAYS merge user patterns with defaults (additive for safety)
        denylist = DEFAULT_DENYLIST.copy()
        if 'denylist' in ct_data:
            user_denylist = ct_data['denylist']
            for pattern in user_denylist:
                if pattern not in denylist:
                    denylist.append(pattern)
        
        return CommandTrustConfig(
            enabled=ct_data.get('enabled', True),
            yolo_mode=ct_data.get('yolo_mode', False),
            approval_mode=approval_mode,
            allowlist=allowlist,
            denylist=denylist,
        )
    
    def _validate_approval_mode(self, approval_mode: str) -> str:
        """Validate approval_mode value and fall back to default if invalid.
        
        Args:
            approval_mode: Approval mode string to validate
            
        Returns:
            Valid approval mode string
            
        Requirements: 3.1, 3.4, 3.5
        """
        valid_modes = ['user_driven', 'ai_driven']
        if approval_mode not in valid_modes:
            print(f"Warning: Invalid approval_mode '{approval_mode}'. Using default '{DEFAULT_APPROVAL_MODE}'.")
            return DEFAULT_APPROVAL_MODE
        return approval_mode
    
    def save_user_settings(self, settings: UserSettings) -> None:
        """Save user settings to file with YAML comments.
        
        This method:
        1. Creates parent directories if needed
        2. Uses serializers.py to generate commented YAML
        3. Writes to ~/.shello_cli/user-settings.yml
        4. Sets file permissions to 0o600 (user read/write only)
        5. Updates the memory cache
        
        Args:
            settings: UserSettings object to save
            
        Requirements: 5.1, 8.1, 8.3, 9.1
        """
        # Ensure directory exists
        self._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate YAML with comments using serializers.py
        yaml_content = generate_yaml_with_comments(settings)
        
        # Write to file with UTF-8 encoding
        with open(self._user_settings_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        # Set secure file permissions (user read/write only)
        os.chmod(self._user_settings_path, 0o600)
        
        # Update cached settings
        self._user_settings = settings
    
    def get_provider_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific provider with environment variable fallback.
        
        This method:
        1. Checks config first for credentials
        2. Falls back to environment variables if not in config
        3. Supports OPENAI_API_KEY, AWS_REGION, AWS_PROFILE, etc.
        
        Args:
            provider: Provider name (defaults to current active provider)
            
        Returns:
            Dictionary with provider configuration including credentials
            
        Raises:
            ValueError: If provider is not configured
            
        Requirements: 4.6, 5.2
        """
        settings = self.load_user_settings()
        target_provider = provider or settings.provider
        
        if target_provider == 'openai':
            config = settings.openai_config
            
            # Get API key with env var fallback
            api_key = None
            if config and config.api_key:
                api_key = config.api_key
            else:
                api_key = os.environ.get('OPENAI_API_KEY')
            
            # Get base URL
            base_url = 'https://api.openai.com/v1'
            if config and config.base_url:
                base_url = config.base_url
            
            # Get model
            default_model = 'gpt-4o'
            models = ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo']
            if config:
                if config.default_model:
                    default_model = config.default_model
                if config.models:
                    models = config.models
            
            return {
                'api_key': api_key,
                'base_url': base_url,
                'model': default_model,
                'models': models,
            }
        
        elif target_provider == 'bedrock':
            config = settings.bedrock_config
            
            # Get AWS credentials with env var fallback
            aws_region = None
            if config and config.aws_region:
                aws_region = config.aws_region
            else:
                aws_region = os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION')
            
            aws_profile = None
            if config and config.aws_profile:
                aws_profile = config.aws_profile
            else:
                aws_profile = os.environ.get('AWS_PROFILE')
            
            aws_access_key = None
            if config and config.aws_access_key:
                aws_access_key = config.aws_access_key
            else:
                aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
            
            aws_secret_key = None
            if config and config.aws_secret_key:
                aws_secret_key = config.aws_secret_key
            else:
                aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
            
            # Get model
            default_model = 'anthropic.claude-3-5-sonnet-20241022-v2:0'
            models = ['anthropic.claude-3-5-sonnet-20241022-v2:0']
            if config:
                if config.default_model:
                    default_model = config.default_model
                if config.models:
                    models = config.models
            
            return {
                'region': aws_region,
                'profile': aws_profile,
                'access_key': aws_access_key,
                'secret_key': aws_secret_key,
                'model': default_model,
                'models': models,
            }
        
        elif target_provider == 'gemini':
            config = settings.gemini_config
            
            # Get API key with env var fallback
            api_key = None
            if config and config.api_key:
                api_key = config.api_key
            else:
                api_key = os.environ.get('GEMINI_API_KEY')
            
            # Get model
            default_model = 'gemini-pro'
            models = ['gemini-pro', 'gemini-pro-vision']
            if config:
                if config.default_model:
                    default_model = config.default_model
                if config.models:
                    models = config.models
            
            return {
                'api_key': api_key,
                'model': default_model,
                'models': models,
            }
        
        elif target_provider == 'vertex':
            config = settings.vertex_config
            
            # Vertex uses gcloud authentication, no API key needed
            # Get model
            default_model = 'gemini-pro'
            models = ['gemini-pro']
            if config:
                if config.default_model:
                    default_model = config.default_model
                if config.models:
                    models = config.models
            
            return {
                'model': default_model,
                'models': models,
            }
        
        else:
            raise ValueError(f"Unknown provider: {target_provider}")
    
    def reload_settings(self) -> UserSettings:
        """Reload settings from disk, clearing the cache.
        
        This is useful when settings have been modified externally.
        
        Returns:
            Freshly loaded UserSettings
        """
        self._user_settings = None
        return self.load_user_settings()
    
    def get_output_management_config(self) -> OutputManagementConfig:
        """Get output management config with defaults if not configured.
        
        Returns:
            OutputManagementConfig (uses defaults if not in user settings)
        """
        settings = self.load_user_settings()
        if settings.output_management is not None:
            return settings.output_management
        
        # Return default config
        from shello_cli.settings.models import FirstLastRatioConfig, SemanticConfig, CompressionConfig, CacheConfig
        
        return OutputManagementConfig(
            enabled=True,
            show_summary=True,
            limits=DEFAULT_CHAR_LIMITS.copy(),
            strategies=DEFAULT_STRATEGIES.copy(),
            first_last_ratio=FirstLastRatioConfig(),
            semantic=SemanticConfig(),
            compression=CompressionConfig(),
            cache=CacheConfig(),
        )
    
    def get_command_trust_config(self) -> CommandTrustConfig:
        """Get command trust config with defaults if not configured.
        
        Returns:
            CommandTrustConfig (uses defaults if not in user settings)
        """
        settings = self.load_user_settings()
        if settings.command_trust is not None:
            return settings.command_trust
        
        # Return default config
        return CommandTrustConfig(
            enabled=True,
            yolo_mode=False,
            approval_mode=DEFAULT_APPROVAL_MODE,
            allowlist=DEFAULT_ALLOWLIST.copy(),
            denylist=DEFAULT_DENYLIST.copy(),
        )
    
    def get_current_model(self) -> str:
        """Get current model with fallback logic.
        
        Priority: project settings > user settings > default
        
        Returns:
            str: The current model identifier
        """
        # Check project settings first
        project_settings = self.load_project_settings()
        if project_settings.model is not None:
            return project_settings.model
        
        # Check user settings
        user_settings = self.load_user_settings()
        provider = user_settings.provider
        
        if provider == "openai" and user_settings.openai_config:
            if user_settings.openai_config.default_model:
                return user_settings.openai_config.default_model
            return "gpt-4o"  # Default fallback for OpenAI
        elif provider == "bedrock" and user_settings.bedrock_config:
            if user_settings.bedrock_config.default_model:
                return user_settings.bedrock_config.default_model
            return "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Default fallback for Bedrock
        elif provider == "gemini" and user_settings.gemini_config:
            if user_settings.gemini_config.default_model:
                return user_settings.gemini_config.default_model
            return "gemini-pro"  # Default fallback for Gemini
        elif provider == "vertex" and user_settings.vertex_config:
            if user_settings.vertex_config.default_model:
                return user_settings.vertex_config.default_model
            return "gemini-pro"  # Default fallback for Vertex
        
        # No provider configured
        return "gpt-4o"
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from settings or environment (for OpenAI provider).
        
        Priority: environment variable > openai_config
        
        Returns:
            Optional[str]: The API key or None if not found
        """
        # Check environment variable first
        env_key = os.environ.get('OPENAI_API_KEY')
        if env_key:
            return env_key
        
        # Get from openai_config
        user_settings = self.load_user_settings()
        if user_settings.openai_config and user_settings.openai_config.api_key:
            return user_settings.openai_config.api_key
        
        return None
    
    def get_base_url(self) -> str:
        """Get API base URL (for OpenAI provider).
        
        Returns base URL from openai_config or default
        
        Returns:
            str: The base URL
        """
        user_settings = self.load_user_settings()
        
        if user_settings.openai_config and user_settings.openai_config.base_url:
            return user_settings.openai_config.base_url
        
        # Default fallback
        return "https://api.openai.com/v1"
    
    def get_provider(self) -> str:
        """Get the configured provider (openai, bedrock, gemini, or vertex).
        
        Returns:
            str: The active provider name
        """
        user_settings = self.load_user_settings()
        return user_settings.provider
    
    def set_provider(self, provider: str) -> None:
        """Set the active provider and save settings.
        
        Args:
            provider: The provider to set ("openai", "bedrock", "gemini", or "vertex")
            
        Raises:
            ValueError: If provider is not valid
        """
        valid_providers = ["openai", "bedrock", "gemini", "vertex"]
        if provider not in valid_providers:
            raise ValueError(f"Invalid provider: {provider}. Supported providers: {', '.join(valid_providers)}")
        
        user_settings = self.load_user_settings()
        user_settings.provider = provider
        self.save_user_settings(user_settings)
    
    def is_provider_configured(self, provider: str) -> bool:
        """Check if a provider is configured.
        
        Args:
            provider: The provider to check ("openai", "bedrock", "gemini", or "vertex")
            
        Returns:
            bool: True if the provider has configuration, False otherwise
        """
        user_settings = self.load_user_settings()
        
        if provider == "openai":
            # OpenAI is considered configured if openai_config exists or environment variable is set
            if user_settings.openai_config is not None:
                return True
            if os.environ.get('OPENAI_API_KEY'):
                return True
            return False
        
        elif provider == "bedrock":
            return user_settings.bedrock_config is not None
        
        elif provider == "gemini":
            return user_settings.gemini_config is not None
        
        elif provider == "vertex":
            return user_settings.vertex_config is not None
        
        return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of configured providers.
        
        Returns:
            List[str]: List of provider names that are configured
        """
        providers = []
        
        if self.is_provider_configured("openai"):
            providers.append("openai")
        
        if self.is_provider_configured("bedrock"):
            providers.append("bedrock")
        
        if self.is_provider_configured("gemini"):
            providers.append("gemini")
        
        if self.is_provider_configured("vertex"):
            providers.append("vertex")
        
        return providers
    
    def load_project_settings(self) -> 'ProjectSettings':
        """Load project settings from .shello/settings.json.
        
        Returns:
            ProjectSettings: The project settings (defaults if file doesn't exist)
        """
        from shello_cli.settings.models import ProjectSettings
        import json
        
        # Return cached settings if available
        if self._project_settings is not None:
            return self._project_settings
        
        # Create default settings
        default_settings = ProjectSettings()
        
        # If file doesn't exist, return defaults
        if not self._project_settings_path.exists():
            self._project_settings = default_settings
            return self._project_settings
        
        try:
            with open(self._project_settings_path, 'r') as f:
                data = json.load(f)
            
            # Merge loaded data with defaults
            self._project_settings = ProjectSettings(
                model=data.get('model', default_settings.model)
            )
            return self._project_settings
        except (json.JSONDecodeError, IOError) as e:
            # If file is corrupted or unreadable, return defaults
            self._project_settings = default_settings
            return self._project_settings
    
    def save_project_settings(self, settings: 'ProjectSettings') -> None:
        """Save project settings to .shello/settings.json.
        
        Args:
            settings: ProjectSettings object to save
        """
        import json
        
        # Ensure directory exists
        self._project_settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        with open(self._project_settings_path, 'w') as f:
            json.dump(asdict(settings), f, indent=2)
        
        # Update cached settings
        self._project_settings = settings
    
    def enable_yolo_mode_for_session(self) -> None:
        """Enable YOLO mode for the current session (does not persist to file).
        
        This modifies the cached settings but does not save to disk.
        """
        user_settings = self.load_user_settings()
        
        # Get or create command_trust config
        if user_settings.command_trust is None:
            user_settings.command_trust = CommandTrustConfig()
        
        # Enable YOLO mode
        user_settings.command_trust.yolo_mode = True
        
        # Update cached settings (but don't save to file)
        self._user_settings = user_settings
