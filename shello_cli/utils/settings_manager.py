"""Settings manager for user and project configuration."""

from dataclasses import dataclass, field, asdict
from typing import Optional, List
from pathlib import Path
import json
import os


@dataclass
class UserSettings:
    """User-level settings stored in ~/.shello_cli/user-settings.json"""
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    models: List[str] = field(default_factory=lambda: [
        "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"
    ])


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
            
            # Merge loaded data with defaults
            self._user_settings = UserSettings(
                api_key=data.get('api_key', default_settings.api_key),
                base_url=data.get('base_url', default_settings.base_url),
                default_model=data.get('default_model', default_settings.default_model),
                models=data.get('models', default_settings.models)
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
        
        # Convert to dict and save
        with open(self._user_settings_path, 'w') as f:
            json.dump(asdict(settings), f, indent=2)
        
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
