"""Type definitions for output management."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict


class OutputType(Enum):
    """Types of command output with different truncation limits and strategies."""
    LIST = "list"
    SEARCH = "search"
    LOG = "log"
    JSON = "json"
    INSTALL = "install"
    BUILD = "build"
    TEST = "test"
    DEFAULT = "default"


class TruncationStrategy(Enum):
    """Strategies for truncating output."""
    FIRST_ONLY = "first_only"    # First N chars (cut at line boundary)
    LAST_ONLY = "last_only"      # Last N chars
    FIRST_LAST = "first_last"    # 20% first + 80% last
    SEMANTIC = "semantic"        # Keep important lines from anywhere


class LineImportance(Enum):
    """Importance levels for semantic line classification."""
    CRITICAL = 3  # Errors, failures, exceptions
    HIGH = 2      # Warnings, success messages
    MEDIUM = 1    # Test results, status indicators
    LOW = 0       # Normal output


@dataclass
class CompressionStats:
    """Statistics from progress bar compression."""
    lines_before: int
    lines_after: int
    lines_saved: int
    sequences_compressed: int


@dataclass
class CacheEntry:
    """Entry in the output cache."""
    output: str
    command: str
    created_at: float
    size_bytes: int


@dataclass
class TruncationResult:
    """Result of output truncation.
    
    Attributes:
        output: The truncated/processed output string
        was_truncated: Whether truncation occurred
        total_chars: Total characters in original output
        shown_chars: Characters shown after truncation
        total_lines: Total lines in original output
        shown_lines: Lines shown after truncation
        output_type: Detected type of the output
        strategy: Truncation strategy used
        cache_id: Cache ID for retrieval (if cached)
        compression_stats: Progress bar compression stats (if applied)
        semantic_stats: Importance level counts (if semantic applied)
        used_json_analyzer: Whether json_analyzer_tool was used
        summary: Formatted summary for AI
    """
    output: str
    was_truncated: bool
    total_chars: int
    shown_chars: int
    total_lines: int
    shown_lines: int
    output_type: OutputType
    strategy: TruncationStrategy
    cache_id: Optional[str] = None
    compression_stats: Optional[CompressionStats] = None
    semantic_stats: Optional[Dict[str, int]] = None
    used_json_analyzer: bool = False
    summary: str = ""
