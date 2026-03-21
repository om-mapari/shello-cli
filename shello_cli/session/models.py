"""Data models for session history.

Defines Pydantic v2 models for session entries, metadata, index,
and configuration used throughout the session history feature.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionEntry(BaseModel):
    """A single timestamped record in a session file."""

    entry_type: str
    timestamp: datetime
    sequence: int
    content: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionMetadata(BaseModel):
    """Metadata for a single session in the index."""

    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    working_directory: str
    entry_count: int = 0
    provider: str
    model: str
    first_user_message: Optional[str] = None
    resumed_from: Optional[str] = None


class SessionIndex(BaseModel):
    """Index of all sessions for fast listing."""

    sessions: Dict[str, SessionMetadata] = Field(default_factory=dict)

    def sorted_sessions(self) -> List[SessionMetadata]:
        """Return sessions in reverse chronological order."""
        return sorted(
            self.sessions.values(),
            key=lambda s: s.start_time,
            reverse=True,
        )


class SessionHistoryConfig(BaseModel):
    """Configuration for session history feature."""

    enabled: bool = True
    max_storage_mb: int = 50
