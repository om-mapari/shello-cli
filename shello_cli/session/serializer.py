"""Session serializer for converting between SessionEntry objects and JSON Lines format.

Handles serialization/deserialization of individual session entries and the session index.
Malformed input is handled gracefully by returning None and logging a warning.
"""

import json
import logging
from typing import Optional

from .models import SessionEntry, SessionIndex

logger = logging.getLogger(__name__)


class SessionSerializer:
    """Converts SessionEntry objects to/from JSON Lines and SessionIndex to/from JSON."""

    @staticmethod
    def serialize(entry: SessionEntry) -> str:
        """Convert a SessionEntry to a single JSON line (no trailing newline).

        Uses Pydantic's model_dump with mode='json' for consistent datetime
        serialization, then json.dumps with sort_keys for deterministic output.
        """
        data = entry.model_dump(mode="json")
        return json.dumps(data, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def deserialize(line: str) -> Optional[SessionEntry]:
        """Parse a JSON line into a SessionEntry.

        Returns None for malformed lines, logging a warning per Requirement 6.4.
        """
        stripped = line.strip()
        if not stripped:
            return None
        try:
            data = json.loads(stripped)
            return SessionEntry.model_validate(data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Skipping malformed session entry: %s", e)
            return None

    @staticmethod
    def serialize_index(index: SessionIndex) -> str:
        """Serialize the full SessionIndex to a JSON string."""
        data = index.model_dump(mode="json")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @staticmethod
    def deserialize_index(data: str) -> SessionIndex:
        """Parse JSON into a SessionIndex.

        Returns an empty SessionIndex if the data is malformed.
        """
        try:
            parsed = json.loads(data)
            return SessionIndex.model_validate(parsed)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to deserialize session index, returning empty: %s", e)
            return SessionIndex()
