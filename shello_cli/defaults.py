"""Default values for user-changeable settings."""

# =============================================================================
# OUTPUT MANAGEMENT DEFAULTS
# =============================================================================

# Default character limits per output type (~4 chars = 1 token)
DEFAULT_CHAR_LIMITS = {
    "list": 5_000,       # ~1.2K tokens
    "search": 10_000,    # ~2.5K tokens
    "log": 15_000,       # ~3.7K tokens
    "json": 20_000,      # ~5K tokens
    "install": 8_000,    # ~2K tokens
    "build": 8_000,      # ~2K tokens
    "test": 15_000,      # ~3.7K tokens
    "default": 8_000,    # ~2K tokens
    "safety": 50_000,    # ~12.5K tokens (hard max)
}

# Default truncation strategies per output type
DEFAULT_STRATEGIES = {
    "list": "first_only",
    "search": "first_only",
    "log": "last_only",
    "json": "first_only",
    "install": "first_last",
    "build": "first_last",
    "test": "first_last",    
    "default": "first_last",
}

# First/Last split ratio for FIRST_LAST strategy
DEFAULT_FIRST_RATIO = 0.2   # 20% from beginning
DEFAULT_LAST_RATIO = 0.8    # 80% from end

# Cache settings
DEFAULT_CACHE_MAX_SIZE_MB = 100   # 100MB total cache size (no TTL - persists for conversation)

# =============================================================================
# COMMAND TRUST AND SAFETY DEFAULTS
# =============================================================================

# Default allowlist patterns (safe commands that execute without approval)
# These patterns are used when no user configuration is provided.
# Users can override this list completely in their settings.
# Supports three pattern types:
#   1. Exact match: "git status"
#   2. Wildcard: "git *" (matches git status, git log, etc.)
#   3. Regex: "^git (status|log)$" (patterns starting with ^)
DEFAULT_ALLOWLIST = [
    # Navigation and inspection
    "ls", "ls *", "pwd", "cd", "cd *",
    # Git read-only operations
    "git status", "git log", "git log *", "git diff", "git diff *",
    "git show", "git show *", "git branch", "git branch *",
    # File viewing
    "cat *", "less *", "more *", "head *", "tail *",
    # Search
    "grep *", "find *", "rg *", "ag *",
    # Process inspection
    "ps", "ps *", "top", "htop",
    # Network inspection
    "ping *", "curl -I *", "wget --spider *",
    # Package inspection
    "npm list", "pip list", "pip show *",
    # Output commands (safe for testing and general use)
    "echo", "echo *",
    # Python commands with -c flag (commonly used in tests)
    "python -c *", "python3 -c *",
]

# Default denylist patterns (dangerous commands that always show warnings)
# These patterns are ALWAYS active and cannot be removed by user configuration.
# User denylist patterns are ADDED to these defaults (additive for safety).
# When a command matches the denylist, a critical warning dialog is shown
# regardless of YOLO mode, allowlist, or AI safety flags.
DEFAULT_DENYLIST = [
    # Destructive filesystem operations
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf ~/*",
    # Disk operations
    "dd if=/dev/zero*",
    "dd if=*of=/dev/sd*",
    "mkfs*",
    "format*",
    "> /dev/sd*",
    # System modifications
    "chmod -R 777 /",
    "chown -R * /",
    # Dangerous redirects
    "> /dev/sda",
    "> /dev/null &",
]

# Default approval mode
# "user_driven" - Always prompt for non-allowlist commands (safer default)
# "ai_driven" - Trust AI safety flags; only prompt when AI flags as unsafe
DEFAULT_APPROVAL_MODE = "user_driven"  # "ai_driven" or "user_driven"

# =============================================================================
# PROVIDER CONFIGURATION DEFAULTS
# =============================================================================

# Default provider configurations
DEFAULT_PROVIDER_CONFIGS = {
    "openai": {
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ],
    },
    "bedrock": {
        "provider_type": "bedrock",
        "aws_region": "us-east-1",
        "default_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "models": [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-sonnet-20240229-v1:0",
            "anthropic.claude-3-haiku-20240307-v1:0",
        ],
    },
}
