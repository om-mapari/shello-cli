"""Application-wide constants and paths."""
from pathlib import Path

# Application paths
APP_DIR = Path.home() / ".shello_cli"

# Ensure directory exists
APP_DIR.mkdir(exist_ok=True)

# =============================================================================
# OUTPUT MANAGEMENT CONSTANTS
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
# COMMAND DETECTION PATTERNS
# =============================================================================

# Patterns to detect output type from command
COMMAND_PATTERNS = {
    "list": [
        r"^ls\b",
        r"^dir\b",
        r"docker\s+ps",
        r"docker\s+images",
        r"aws\s+\S+\s+list",
        r"kubectl\s+get",
        r"Get-ChildItem",
    ],
    "search": [
        r"^grep\b",
        r"^find\b",
        r"^rg\b",
        r"^ag\b",
        r"Select-String",
        r"findstr",
    ],
    "log": [
        r"^tail\b",
        r"^head\b",
        r"cat\s+.*\.log",
        r"docker\s+logs",
        r"journalctl",
        r"Get-EventLog",
        r"Get-Content\s+.*\.log",
    ],
    "install": [
        r"npm\s+(install|i|add|ci)\b",
        r"yarn\s+(install|add)\b",
        r"pip\s+install\b",
        r"pip3\s+install\b",
        r"cargo\s+(install|add)\b",
        r"gem\s+install\b",
        r"apt(-get)?\s+install\b",
        r"yum\s+install\b",
        r"brew\s+install\b",
        r"choco\s+install\b",
    ],
    "build": [
        r"npm\s+run\s+build\b",
        r"yarn\s+build\b",
        r"cargo\s+build\b",
        r"go\s+build\b",
        r"mvn\s+(compile|package|install)\b",
        r"gradle\s+build\b",
        r"docker\s+build\b",
        r"make\b",
    ],
    "test": [
        r"pytest\b",
        r"python\s+-m\s+pytest\b",
        r"npm\s+(test|run\s+test)\b",
        r"yarn\s+test\b",
        r"jest\b",
        r"vitest\b",
        r"cargo\s+test\b",
        r"go\s+test\b",
        r"mvn\s+test\b",
    ],
}

# =============================================================================
# CONTENT DETECTION PATTERNS
# =============================================================================

# Patterns to detect output type from content
CONTENT_PATTERNS = {
    "json": [
        r"^\s*[\[{]",  # Starts with [ or {
    ],
    "test": [
        r"\d+\s+(passed|failed|skipped)",
        r"PASSED|FAILED|ERROR",
        r"✓|✗|✔|✘",
        r"Tests:\s+\d+",
    ],
    "build": [
        r"Build\s+(succeeded|failed|completed)",
        r"Compiled\s+successfully",
        r"BUILD\s+(SUCCESS|FAILURE)",
        r"webpack\s+\d+\.\d+",
    ],
}

# =============================================================================
# SEMANTIC CLASSIFICATION PATTERNS
# =============================================================================

# Patterns for line importance classification
IMPORTANCE_PATTERNS = {
    "critical": [
        r"\b(error|err|fail|failed|failure|exception|fatal|critical|panic)\b",
        r"\b(ENOENT|EACCES|EPERM|ECONNREFUSED|ETIMEDOUT)\b",
        r"Traceback\s+\(most\s+recent",
        r"^\s*at\s+.*\(.*:\d+:\d+\)",  # Stack trace lines
    ],
    "high": [
        r"\b(warn|warning|deprecated|caution)\b",
        r"\b(success|successfully|completed|done|finished)\b",
        r"\b(summary|total|result|final)\b",
        r"^\s*\d+\s+(passed|failed|skipped|pending)",
        r"^\s*=+\s*$",  # Separator lines
        r"^-{3,}$",
    ],
    "medium": [
        r"[✓✗❌✅⚠️🔴🟢🟡]",  # Status indicators
        r"^\s*\[\s*(OK|FAIL|PASS|SKIP|WARN)\s*\]",
        r"^\s*(PASS|FAIL|OK|ERROR):",
    ],
}

# =============================================================================
# PROGRESS BAR PATTERNS
# =============================================================================

# Patterns to detect progress bars for compression
PROGRESS_BAR_PATTERNS = [
    r".*\d+%.*",                    # Percentage: 50%
    r".*\[\s*#+\s*\].*",           # Bar: [####    ]
    r".*\[\s*=+>\s*\].*",          # Bar: [===>    ]
    r".*⠋|⠙|⠹|⠸|⠼|⠴|⠦|⠧|⠇|⠏.*",  # Spinner characters
    r".*downloading.*\d+/\d+.*",   # Downloading 5/10
    r".*\(\d+/\d+\).*",            # (5/10)
]

# =============================================================================
# TRUNCATION SUMMARY TEMPLATES
# =============================================================================

TRUNCATION_SUMMARY_TEMPLATE = """
───────────────────────────────────────────────────────────
📊 OUTPUT SUMMARY
───────────────────────────────────────────────────────────
Total: {total_chars:,} chars ({total_lines} lines) | Shown: {shown_chars:,} chars ({shown_lines} lines)
Strategy: {strategy}
{optimizations}
{semantic_stats}

💾 Cache ID: {cache_id}
💡 {suggestion}
───────────────────────────────────────────────────────────
"""

JSON_ANALYZER_SUMMARY_TEMPLATE = """
───────────────────────────────────────────────────────────
📊 OUTPUT SUMMARY
───────────────────────────────────────────────────────────
Total: {total_chars:,} chars | JSON structure analyzed using json_analyzer_tool
Above: jq paths for querying the data

💾 Cache ID: {cache_id}
💡 Use get_cached_output(cache_id="{cache_id}", lines="+50") to see first 50 lines of raw JSON
───────────────────────────────────────────────────────────
"""
# =============================================================================
# COMMAND TRUST AND SAFETY CONSTANTS
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
