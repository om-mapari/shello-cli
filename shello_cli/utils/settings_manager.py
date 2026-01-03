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
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_CACHE_MAX_SIZE_MB,
)


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
    ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    max_size_mb: int = DEFAULT_CACHE_MAX_SIZE_MB


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
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    models: List[str] = field(default_factory=lambda: [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"
    ])
    output_management: Optional[OutputManagementConfig] = None


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
                        ttl_seconds=c.get('ttl_seconds', DEFAULT_CACHE_TTL_SECONDS),
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
            
            # Merge loaded data with defaults
            self._user_settings = UserSettings(
                api_key=data.get('api_key', default_settings.api_key),
                base_url=data.get('base_url', default_settings.base_url),
                default_model=data.get('default_model', default_settings.default_model),
                models=data.get('models', default_settings.models),
                output_management=output_management
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
            'api_key': settings.api_key,
            'base_url': settings.base_url,
            'default_model': settings.default_model,
            'models': settings.models
        }
        
        # Only include output_management if it's not None
        if settings.output_management is not None:
            settings_dict['output_management'] = asdict(settings.output_management)
        
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
        return user_settings.default_model
    
    def get_api_key(self) -> Optional[str]:
        """Get API key from settings or environment"""
        # Check environment variable first
        env_key = os.environ.get('OPENAI_API_KEY')
        if env_key:
            return env_key
        
        # Fall back to user settings
        user_settings = self.load_user_settings()
        return user_settings.api_key
    
    def get_base_url(self) -> str:
        """Get API base URL"""
        user_settings = self.load_user_settings()
        return user_settings.base_url
    
    def get_output_management_config(self) -> OutputManagementConfig:
        """Get output management config with defaults if not configured"""
        user_settings = self.load_user_settings()
        if user_settings.output_management is not None:
            return user_settings.output_management
        # Return default config if not configured
        return OutputManagementConfig()
