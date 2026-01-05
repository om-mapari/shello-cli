"""
Data models for settings management.

This module defines the dataclasses used to represent configuration
at different levels (user, project) and for different components
(providers, output management, command trust).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class FirstLastRatioConfig:
    """Configuration for FIRST_LAST truncation strategy ratio."""
    first: float = 0.6
    last: float = 0.4


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
    max_size_mb: int = 100


@dataclass
class ProviderConfig:
    """Configuration for an AI provider (OpenAI, Bedrock, etc.)."""
    
    provider_type: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    aws_region: Optional[str] = None
    aws_profile: Optional[str] = None
    aws_access_key: Optional[str] = None
    aws_secret_key: Optional[str] = None
    default_model: Optional[str] = None
    models: List[str] = field(default_factory=list)


@dataclass
class OutputManagementConfig:
    """Configuration for output truncation and caching."""
    
    enabled: bool = True
    show_summary: bool = True
    limits: Dict[str, int] = field(default_factory=dict)
    strategies: Dict[str, str] = field(default_factory=dict)
    first_last_ratio: FirstLastRatioConfig = field(default_factory=FirstLastRatioConfig)
    semantic: SemanticConfig = field(default_factory=SemanticConfig)
    compression: CompressionConfig = field(default_factory=CompressionConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    def get_limit(self, output_type: str) -> int:
        """Get character limit for output type, falling back to default."""
        from shello_cli.defaults import DEFAULT_CHAR_LIMITS
        return self.limits.get(output_type, self.limits.get("default", DEFAULT_CHAR_LIMITS["default"]))
    
    def get_strategy(self, output_type: str) -> str:
        """Get truncation strategy for output type, falling back to default."""
        from shello_cli.defaults import DEFAULT_STRATEGIES
        return self.strategies.get(output_type, self.strategies.get("default", DEFAULT_STRATEGIES["default"]))


@dataclass
class CommandTrustConfig:
    """Configuration for command approval and trust policies."""
    
    enabled: bool = True
    yolo_mode: bool = False
    approval_mode: str = "user_driven"
    allowlist: List[str] = field(default_factory=list)
    denylist: List[str] = field(default_factory=list)


@dataclass
class UserSettings:
    """User-level settings stored in ~/.shello_cli/user-settings.yml."""
    
    provider: str = "openai"
    openai_config: Optional[ProviderConfig] = None
    bedrock_config: Optional[ProviderConfig] = None
    gemini_config: Optional[ProviderConfig] = None
    vertex_config: Optional[ProviderConfig] = None
    output_management: Optional[OutputManagementConfig] = None
    command_trust: Optional[CommandTrustConfig] = None


@dataclass
class ProjectSettings:
    """Project-level settings stored in .shello/settings.json."""
    
    model: Optional[str] = None
