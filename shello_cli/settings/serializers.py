"""
YAML serialization with documentation comments.

This module provides functions to generate well-documented YAML configuration
files with inline comments, examples, and section headers.
"""

from typing import Any, Dict, Optional
from .models import UserSettings, ProviderConfig, OutputManagementConfig, CommandTrustConfig


def generate_yaml_with_comments(settings: UserSettings) -> str:
    """
    Generate a user-settings.yml file with documentation comments.
    
    Args:
        settings: The UserSettings object to serialize
        
    Returns:
        A YAML string with inline comments and documentation
    """
    lines = []
    
    # Header
    lines.extend([
        "# =============================================================================",
        "# SHELLO CLI USER SETTINGS",
        "# =============================================================================",
        "# Edit this file to customize your settings.",
        "# Only specify values you want to override - defaults are used for the rest.",
        "# See: https://github.com/om-mapari/shello-cli for documentation",
        "",
    ])
    
    # Provider Configuration Section
    lines.extend([
        "# =============================================================================",
        "# PROVIDER CONFIGURATION",
        "# =============================================================================",
        "# Active provider: openai, bedrock, gemini, vertex",
        f"provider: {settings.provider}",
        "",
    ])
    
    # OpenAI Configuration
    lines.extend([
        "# -----------------------------------------------------------------------------",
        "# OpenAI-compatible API",
        "# -----------------------------------------------------------------------------",
    ])
    
    if settings.openai_config:
        lines.extend(_serialize_provider_config("openai_config", settings.openai_config))
    else:
        lines.extend([
            "# openai_config:",
            "#   provider_type: openai",
            "#   api_key: your-api-key-here  # Or use OPENAI_API_KEY env var",
            "#   base_url: https://api.openai.com/v1",
            "#   default_model: gpt-4o",
            "#   models:",
            "#     - gpt-4o",
            "#     - gpt-4o-mini",
            "#     - gpt-4-turbo",
        ])
    lines.append("")
    
    # Bedrock Configuration
    lines.extend([
        "# -----------------------------------------------------------------------------",
        "# AWS Bedrock (uncomment to configure)",
        "# -----------------------------------------------------------------------------",
    ])
    
    if settings.bedrock_config:
        lines.extend(_serialize_provider_config("bedrock_config", settings.bedrock_config))
    else:
        lines.extend([
            "# bedrock_config:",
            "#   provider_type: bedrock",
            "#   aws_region: us-east-1      # Or use AWS_REGION env var",
            "#   aws_profile: default       # Or use AWS_PROFILE env var",
            "#   # aws_access_key: xxx      # Or use AWS_ACCESS_KEY_ID env var",
            "#   # aws_secret_key: xxx      # Or use AWS_SECRET_ACCESS_KEY env var",
            "#   default_model: anthropic.claude-3-5-sonnet-20241022-v2:0",
            "#   models:",
            "#     - anthropic.claude-3-5-sonnet-20241022-v2:0",
            "#     - anthropic.claude-3-sonnet-20240229-v1:0",
        ])
    lines.append("")
    
    # Gemini Configuration
    lines.extend([
        "# -----------------------------------------------------------------------------",
        "# Google Gemini (uncomment to configure)",
        "# -----------------------------------------------------------------------------",
        "# gemini_config:",
        "#   provider_type: gemini",
        "#   api_key: your-api-key-here  # Or use GEMINI_API_KEY env var",
        "#   default_model: gemini-pro",
        "#   models:",
        "#     - gemini-pro",
        "#     - gemini-pro-vision",
        "",
    ])
    
    # Vertex AI Configuration
    lines.extend([
        "# -----------------------------------------------------------------------------",
        "# Google Vertex AI (uncomment to configure)",
        "# -----------------------------------------------------------------------------",
        "# vertex_config:",
        "#   provider_type: vertex",
        "#   # Requires gcloud authentication",
        "#   default_model: gemini-pro",
        "#   models:",
        "#     - gemini-pro",
        "",
    ])
    
    # Output Management Section
    lines.extend([
        "# =============================================================================",
        "# OUTPUT MANAGEMENT (optional - uses defaults if not specified)",
        "# =============================================================================",
        "# Controls how command output is truncated and displayed.",
        "# Uncomment and modify to customize:",
        "#",
    ])
    
    if settings.output_management:
        lines.extend(_serialize_output_management(settings.output_management))
    else:
        lines.extend([
            "# output_management:",
            "#   enabled: true",
            "#   show_summary: true",
            "#   limits:                    # Character limits per output type",
            "#     list: 5000               # ~1.2K tokens",
            "#     search: 10000            # ~2.5K tokens",
            "#     log: 15000               # ~3.7K tokens",
            "#     json: 20000              # ~5K tokens",
            "#     default: 8000            # ~2K tokens",
            "#   strategies:                # Truncation strategies",
            "#     list: first_only",
            "#     search: first_only",
            "#     log: last_only",
            "#     default: first_last",
            "#   first_ratio: 0.6           # For first_last strategy",
            "#   last_ratio: 0.4",
            "#   cache_max_size_mb: 100",
        ])
    lines.append("")
    
    # Command Trust Section
    lines.extend([
        "# =============================================================================",
        "# COMMAND TRUST (optional - uses defaults if not specified)",
        "# =============================================================================",
        "# Controls which commands require approval before execution.",
        "# Uncomment and modify to customize:",
        "#",
    ])
    
    if settings.command_trust:
        lines.extend(_serialize_command_trust(settings.command_trust))
    else:
        lines.extend([
            "# command_trust:",
            "#   enabled: true",
            "#   yolo_mode: false           # Set true to skip approvals (dangerous!)",
            "#   approval_mode: user_driven # Options: user_driven, ai_driven",
            "#   allowlist:                 # Commands that run without approval",
            "#     - ls",
            "#     - pwd",
            "#     - git status",
            "#   # Note: denylist always includes safety defaults (rm -rf /, etc.)",
            "#   # Your additions are merged with defaults:",
            "#   # denylist:",
            "#   #   - my-dangerous-command",
        ])
    
    return "\n".join(lines)


def _serialize_provider_config(key: str, config: ProviderConfig) -> list:
    """Serialize a ProviderConfig to YAML lines."""
    lines = [f"{key}:"]
    lines.append(f"  provider_type: {config.provider_type}")
    
    if config.api_key:
        # Quote the API key to prevent YAML from interpreting it as a number
        lines.append(f"  api_key: '{config.api_key}'")
    
    if config.base_url:
        lines.append(f"  base_url: {config.base_url}")
    
    if config.aws_region:
        lines.append(f"  aws_region: {config.aws_region}")
    
    if config.aws_profile:
        lines.append(f"  aws_profile: {config.aws_profile}")
    
    if config.aws_access_key:
        # Quote to prevent YAML from interpreting as a number
        lines.append(f"  aws_access_key: '{config.aws_access_key}'")
    
    if config.aws_secret_key:
        # Quote to prevent YAML from interpreting as a number
        lines.append(f"  aws_secret_key: '{config.aws_secret_key}'")
    
    if config.default_model:
        lines.append(f"  default_model: {config.default_model}")
    
    if config.models:
        lines.append("  models:")
        for model in config.models:
            lines.append(f"    - {model}")
    
    return lines


def _serialize_output_management(config: OutputManagementConfig) -> list:
    """Serialize OutputManagementConfig to YAML lines."""
    lines = ["output_management:"]
    lines.append(f"  enabled: {str(config.enabled).lower()}")
    lines.append(f"  show_summary: {str(config.show_summary).lower()}")
    
    if config.limits:
        lines.append("  limits:")
        for key, value in config.limits.items():
            lines.append(f"    {key}: {value}")
    
    if config.strategies:
        lines.append("  strategies:")
        for key, value in config.strategies.items():
            lines.append(f"    {key}: {value}")
    
    # Serialize nested configs
    if config.first_last_ratio:
        lines.append("  first_last_ratio:")
        lines.append(f"    first: {config.first_last_ratio.first}")
        lines.append(f"    last: {config.first_last_ratio.last}")
    
    if config.semantic:
        lines.append("  semantic:")
        lines.append(f"    enabled: {str(config.semantic.enabled).lower()}")
        lines.append(f"    always_show_critical: {str(config.semantic.always_show_critical).lower()}")
    
    if config.compression:
        lines.append("  compression:")
        lines.append(f"    enabled: {str(config.compression.enabled).lower()}")
    
    if config.cache:
        lines.append("  cache:")
        lines.append(f"    enabled: {str(config.cache.enabled).lower()}")
        lines.append(f"    max_size_mb: {config.cache.max_size_mb}")
    
    return lines


def _serialize_command_trust(config: CommandTrustConfig) -> list:
    """Serialize CommandTrustConfig to YAML lines."""
    lines = ["command_trust:"]
    lines.append(f"  enabled: {str(config.enabled).lower()}")
    lines.append(f"  yolo_mode: {str(config.yolo_mode).lower()}")
    lines.append(f"  approval_mode: {config.approval_mode}")
    
    if config.allowlist:
        lines.append("  allowlist:")
        for pattern in config.allowlist:
            lines.append(f"    - {pattern}")
    
    if config.denylist:
        lines.append("  denylist:")
        for pattern in config.denylist:
            lines.append(f"    - {pattern}")
    
    return lines
