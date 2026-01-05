"""Settings manager for user and project configuration."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path
import json
import os
from shello_cli.constants import (
    APP_DIR,
    DEFAULT_CHAR_LIMITS,
    DEFAULT_STRATEGIES,
    DEFAULT_FIRST_RATIO,
    DEFAULT_LAST_RATIO,
    DEFAULT_CACHE_MAX_SIZE_MB,
    DEFAULT_ALLOWLIST,
    DEFAULT_DENYLIST,
    DEFAULT_APPROVAL_MODE,
)
from rich.console import Console

# Console for displaying warnings
console = Console()


@dataclass
class FirstLastRatioConfig:
    """Configuration for FIRST_LAST truncation strategy ratio."""
    first: float = DEFAULT_FIRST_RATIO
    last: float = DEFAULT_LAST_RATIO


@dataclass
class SemanticConfig:
    """Configuration for semantic truncation."""
    enabled: bool = True
    always_show_critical: bool = True


@dataclass
class CompressionConfig:
    """Configuration for progress bar compression."""
    enabled: bool = True


@dataclass
class CacheConfig:
    """Configuration for output caching."""
    enabled: bool = True
    max_size_mb: int = DEFAULT_CACHE_MAX_SIZE_MB


@dataclass
class CommandTrustConfig:
    """Command trust and safety configuration."""
    enabled: bool = True
    yolo_mode: bool = False
    approval_mode: str = DEFAULT_APPROVAL_MODE
    allowlist: List[str] = field(default_factory=lambda: DEFAULT_ALLOWLIST.copy())
    denylist: List[str] = field(default_factory=lambda: DEFAULT_DENYLIST.copy())


@dataclass
class ProviderConfig:
    """Configuration for a single provider.
    
    Attributes:
        provider_type: The type of provider ("openai" or "bedrock")
        api_key: API key for OpenAI-compatible APIs
        base_url: Base URL for OpenAI-compatible APIs
        aws_region: AWS region for Bedrock
        aws_profile: AWS profile name for Bedrock
        aws_access_key: AWS access key ID for Bedrock (explicit credentials)
        aws_secret_key: AWS secret access key for Bedrock (explicit credentials)
        default_model: Default model to use with this provider
        models: List of available models for this provider
    """
    provider_type: str  # "openai" or "bedrock"
    
    # OpenAI fields
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    
    # Bedrock fields
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    
    # Common fields
    default_model: Optional[str] = None
    models: List[str] = field(default_factory=list)


@dataclass
class OutputManagementConfig:
    """Output management configuration with character-based limits.
    
    Attributes:
        enabled: Whether output management is enabled
        show_summary: Whether to show truncation summary
        limits: Character limits per output type (merged with defaults)
        strategies: Truncation strategies per output type (merged with defaults)
        first_last_ratio: Ratio for FIRST_LAST strategy
        semantic: Semantic truncation configuration
        compression: Progress bar compression configuration
        cache: Output caching configuration
    """
    enabled: bool = True
    show_summary: bool = True
    limits: Dict[str, int] = field(default_factory=lambda: DEFAULT_CHAR_LIMITS.copy())
    strategies: Dict[str, str] = field(default_factory=lambda: DEFAULT_STRATEGIES.copy())
    first_last_ratio: FirstLastRatioConfig = field(default_factory=FirstLastRatioConfig)
    semantic: SemanticConfig = field(default_factory=SemanticConfig)
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    def get_limit(self, output_type: str) -> int:
        """Get character limit for output type, falling back to default."""
        return self.limits.get(output_type, self.limits.get("default", DEFAULT_CHAR_LIMITS["default"]))
    
    def get_strategy(self, output_type: str) -> str:
        """Get truncation strategy for output type, falling back to default."""
        return self.strategies.get(output_type, self.strategies.get("default", DEFAULT_STRATEGIES["default"]))


@dataclass
class UserSettings:
    """User-level settings stored in ~/.shello_cli/user-settings.json"""
    # Current active provider ("openai" or "bedrock")
    provider: str = "openai"
    
    # Provider-specific configurations
    openai_config: Optional[ProviderConfig] = None
    bedrock_config: Optional[ProviderConfig] = None
    
    # Other configurations
    output_management: Optional[OutputManagementConfig] = None
    command_trust: Optional[CommandTrustConfig] = None


@dataclass
class ProjectSettings:
    """Project-level settings stored in .shello/settings.json"""
    model: Optional[str] = None


class SettingsManager:
    """Manages user and project settings"""
    
    _instance: Optional['SettingsManager'] = None
    
    def __init__(self):
        """Initialize settings manager"""
        self._user_settings_path = Path.home() / ".shello_cli" / "user-settings.json"
        self._project_settings_path = Path.cwd() / ".shello" / "settings.json"
        self._user_settings: Optional[UserSettings] = None
        self._project_settings: Optional[ProjectSettings] = None
    
    @classmethod
    def get_instance(cls) -> 'SettingsManager':
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def load_user_settings(self) -> UserSettings:
        """Load user settings from file"""
        if self._user_settings is not None:
            return self._user_settings
        
        # Create default settings
        default_settings = UserSettings()
        
        # If file doesn't exist, return defaults
        if not self._user_settings_path.exists():
            self._user_settings = default_settings
            return self._user_settings
        
        try:
            with open(self._user_settings_path, 'r') as f:
                data = json.load(f)
            
            # Parse openai_config if present
            openai_config = None
            if 'openai_config' in data:
                oc_data = data['openai_config']
                openai_config = ProviderConfig(
                    provider_type=oc_data.get('provider_type', 'openai'),
                    api_key=oc_data.get('api_key'),
                    base_url=oc_data.get('base_url'),
                    default_model=oc_data.get('default_model'),
                    models=oc_data.get('models', [])
                )
            
            # Parse bedrock_config if present
            bedrock_config = None
            if 'bedrock_config' in data:
                bc_data = data['bedrock_config']
                bedrock_config = ProviderConfig(
                    provider_type=bc_data.get('provider_type', 'bedrock'),
                    aws_region=bc_data.get('aws_region'),
                    aws_profile=bc_data.get('aws_profile'),
                    aws_access_key=bc_data.get('aws_access_key'),
                    aws_secret_key=bc_data.get('aws_secret_key'),
                    default_model=bc_data.get('default_model'),
                    models=bc_data.get('models', [])
                )
            
            # Parse output_management if present
            output_management = None
            if 'output_management' in data:
                om_data = data['output_management']
                
                # Parse nested configs
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
                
                # Merge user limits with defaults
                limits = DEFAULT_CHAR_LIMITS.copy()
                if 'limits' in om_data:
                    limits.update(om_data['limits'])
                
                # Merge user strategies with defaults
                strategies = DEFAULT_STRATEGIES.copy()
                if 'strategies' in om_data:
                    strategies.update(om_data['strategies'])
                
                output_management = OutputManagementConfig(
                    enabled=om_data.get('enabled', True),
                    show_summary=om_data.get('show_summary', True),
                    limits=limits,
                    strategies=strategies,
                    first_last_ratio=first_last_ratio,
                    semantic=semantic,
                    compression=compression,
                    cache=cache
                )
            
            # Parse command_trust if present
            command_trust = None
            if 'command_trust' in data:
                ct_data = data['command_trust']
                
                # Allowlist: User can override defaults completely
                allowlist = DEFAULT_ALLOWLIST.copy()
                if 'allowlist' in ct_data:
                    allowlist = ct_data['allowlist']
                
                # Denylist: ALWAYS merge user patterns with defaults (additive for safety)
                denylist = DEFAULT_DENYLIST.copy()
                if 'denylist' in ct_data:
                    # Add user patterns to defaults (no duplicates)
                    user_denylist = ct_data['denylist']
                    for pattern in user_denylist:
                        if pattern not in denylist:
                            denylist.append(pattern)
                
                command_trust = CommandTrustConfig(
                    enabled=ct_data.get('enabled', True),
                    yolo_mode=ct_data.get('yolo_mode', False),
                    approval_mode=ct_data.get('approval_mode', DEFAULT_APPROVAL_MODE),
                    allowlist=allowlist,
                    denylist=denylist  # Always includes defaults + user additions
                )
                
                # Validate configuration
                try:
                    # Import here to avoid circular dependency
                    from shello_cli.trust.trust_manager import validate_config
                    validate_config(command_trust)
                except Exception as e:
                    # Validation failed, fall back to defaults and warn user
                    console.print(
                        f"[yellow]⚠️  Warning: Invalid command_trust configuration: {e}[/yellow]"
                    )
                    console.print(
                        "[yellow]   Falling back to safe default settings.[/yellow]"
                    )
                    command_trust = CommandTrustConfig()  # Use defaults
            
            # Merge loaded data with defaults
            self._user_settings = UserSettings(
                provider=data.get('provider', default_settings.provider),
                openai_config=openai_config,
                bedrock_config=bedrock_config,
                output_management=output_management,
                command_trust=command_trust
            )
            return self._user_settings
        except (json.JSONDecodeError, IOError) as e:
            # If file is corrupted or unreadable, return defaults
            self._user_settings = default_settings
            return self._user_settings
    
    def save_user_settings(self, settings: UserSettings) -> None:
        """Save user settings to file"""
        # Ensure directory exists
        self._user_settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict
        settings_dict = {
            'provider': settings.provider
        }
        
        # Only include openai_config if it's not None
        if settings.openai_config is not None:
            settings_dict['openai_config'] = asdict(settings.openai_config)
        
        # Only include bedrock_config if it's not None
        if settings.bedrock_config is not None:
            settings_dict['bedrock_config'] = asdict(settings.bedrock_config)
        
        # Only include output_management if it's not None
        if settings.output_management is not None:
            settings_dict['output_management'] = asdict(settings.output_management)
        
        # Only include command_trust if it's not None
        if settings.command_trust is not None:
            settings_dict['command_trust'] = asdict(settings.command_trust)
        
        # Save to file
        with open(self._user_settings_path, 'w') as f:
            json.dump(settings_dict, f, indent=2)
        
        # Update cached settings
        self._user_settings = settings
        
        # Set secure file permissions (user read/write only)
        os.chmod(self._user_settings_path, 0o600)
    
    def load_project_settings(self) -> ProjectSettings:
        """Load project settings from file"""
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
    
    def save_project_settings(self, settings: ProjectSettings) -> None:
        """Save project settings to file"""
        # Ensure directory exists
        self._project_settings_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        with open(self._project_settings_path, 'w') as f:
            json.dump(asdict(settings), f, indent=2)
        
        # Update cached settings
        self._project_settings = settings
    
    def get_current_model(self) -> str:
        """Get current model with fallback logic"""
        # Priority: project settings > user settings > default
        project_settings = self.load_project_settings()
        if project_settings.model is not None:
            return project_settings.model
        
        user_settings = self.load_user_settings()
        
        # Check provider-specific config
        provider = user_settings.provider
        if provider == "openai" and user_settings.openai_config:
            if user_settings.openai_config.default_model:
                return user_settings.openai_config.default_model
            return "gpt-4o"  # Default fallback for OpenAI
        elif provider == "bedrock" and user_settings.bedrock_config:
            if user_settings.bedrock_config.default_model:
                return user_settings.bedrock_config.default_model
            return "anthropic.claude-3-5-sonnet-20241022-v2:0"  # Default fallback for Bedrock
        
        # No provider configured
        return "gpt-4o"
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from settings or environment (for OpenAI provider).
        
        Priority: environment variable > openai_config
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
        """
        user_settings = self.load_user_settings()
        
        if user_settings.openai_config and user_settings.openai_config.base_url:
            return user_settings.openai_config.base_url
        
        # Default fallback
        return "https://api.openai.com/v1"
    
    def get_provider(self) -> str:
        """Get the configured provider (openai or bedrock)"""
        user_settings = self.load_user_settings()
        return user_settings.provider
    
    def set_provider(self, provider: str) -> None:
        """Set the active provider and save settings.
        
        Args:
            provider: The provider to set ("openai" or "bedrock")
            
        Raises:
            ValueError: If provider is not valid
        """
        if provider not in ["openai", "bedrock"]:
            raise ValueError(f"Invalid provider: {provider}. Supported providers: openai, bedrock")
        
        user_settings = self.load_user_settings()
        user_settings.provider = provider
        self.save_user_settings(user_settings)
    
    def get_provider_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific provider (or current if None).
        
        Args:
            provider: The provider to get config for (defaults to current provider)
            
        Returns:
            Dictionary with provider-specific configuration
            
        Raises:
            ValueError: If provider is not configured
        """
        user_settings = self.load_user_settings()
        target_provider = provider or user_settings.provider
        
        if target_provider == "openai":
            if not user_settings.openai_config:
                raise ValueError("OpenAI provider not configured. Run 'shello setup'.")
            
            return {
                "api_key": user_settings.openai_config.api_key or os.environ.get('OPENAI_API_KEY'),
                "base_url": user_settings.openai_config.base_url or "https://api.openai.com/v1",
                "model": user_settings.openai_config.default_model or "gpt-4o",
                "models": user_settings.openai_config.models or ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
            }
        
        elif target_provider == "bedrock":
            if not user_settings.bedrock_config:
                raise ValueError("Bedrock provider not configured. Run 'shello setup'.")
            
            return {
                "region": user_settings.bedrock_config.aws_region or os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION'),
                "profile": user_settings.bedrock_config.aws_profile or os.environ.get('AWS_PROFILE'),
                "access_key": user_settings.bedrock_config.aws_access_key or os.environ.get('AWS_ACCESS_KEY_ID'),
                "secret_key": user_settings.bedrock_config.aws_secret_key or os.environ.get('AWS_SECRET_ACCESS_KEY'),
                "model": user_settings.bedrock_config.default_model or "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "models": user_settings.bedrock_config.models or ["anthropic.claude-3-5-sonnet-20241022-v2:0"]
            }
        
        else:
            raise ValueError(f"Unknown provider: {target_provider}. Supported providers: openai, bedrock")
    
    def is_provider_configured(self, provider: str) -> bool:
        """Check if a provider is configured.
        
        Args:
            provider: The provider to check ("openai" or "bedrock")
            
        Returns:
            True if the provider has configuration, False otherwise
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
        
        return False
    
    def get_available_providers(self) -> List[str]:
        """Get list of configured providers.
        
        Returns:
            List of provider names that are configured
        """
        providers = []
        
        if self.is_provider_configured("openai"):
            providers.append("openai")
        
        if self.is_provider_configured("bedrock"):
            providers.append("bedrock")
        
        return providers
    
    def get_output_management_config(self) -> OutputManagementConfig:
        """Get output management config with defaults if not configured"""
        user_settings = self.load_user_settings()
        if user_settings.output_management is not None:
            return user_settings.output_management
        # Return default config if not configured
        return OutputManagementConfig()
    
    def get_command_trust_config(self) -> CommandTrustConfig:
        """Get command trust config with defaults if not configured"""
        user_settings = self.load_user_settings()
        if user_settings.command_trust is not None:
            return user_settings.command_trust
        # Return default config if not configured
        return CommandTrustConfig()
    
    def enable_yolo_mode_for_session(self) -> None:
        """Enable YOLO mode for the current session (does not persist to file)"""
        user_settings = self.load_user_settings()
        
        # Get or create command_trust config
        if user_settings.command_trust is None:
            user_settings.command_trust = CommandTrustConfig()
        
        # Enable YOLO mode
        user_settings.command_trust.yolo_mode = True
        
        # Update cached settings (but don't save to file)
        self._user_settings = user_settings
