"""Session pruner for enforcing storage limits on the session store.

Handles deletion of oldest sessions when total storage exceeds the configured
maximum, as well as clearing all sessions and deleting individual sessions.
"""

import logging
from pathlib import Path

from .models import SessionIndex
from .serializer import SessionSerializer

logger = logging.getLogger(__name__)


class SessionPruner:
    """Enforces storage limits by deleting old session files."""

    def __init__(self, session_store_path: Path, max_storage_mb: int = 50) -> None:
        self._store = session_store_path
        self._max_bytes = max_storage_mb * 1024 * 1024
        self._index_path = session_store_path / "index.json"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> SessionIndex:
        """Load the SessionIndex from disk, returning empty index on failure."""
        if not self._index_path.exists():
            return SessionIndex()
        try:
            return SessionSerializer.deserialize_index(self._index_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to read session index, treating as empty: %s", e)
            return SessionIndex()

    def _save_index(self, index: SessionIndex) -> None:
        """Persist the SessionIndex to disk."""
        try:
            self._index_path.write_text(
                SessionSerializer.serialize_index(index), encoding="utf-8"
            )
        except OSError as e:
            logger.warning("Failed to write session index: %s", e)

    def _session_file(self, session_id: str) -> Path:
        return self._store / f"session_{session_id}.jsonl"

    def _total_size(self) -> int:
        """Return total size in bytes of all .jsonl files in the store."""
        total = 0
        for f in self._store.glob("*.jsonl"):
            try:
                total += f.stat().st_size
            except OSError as e:
                logger.warning("Could not stat %s, skipping: %s", f, e)
        return total

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def prune(self) -> int:
        """Delete oldest sessions until total .jsonl size is within the limit.

        Returns the number of sessions deleted.
        """
        if self._total_size() <= self._max_bytes:
            return 0

        index = self._load_index()
        # sorted_sessions() returns newest-first; reverse for oldest-first
        ordered = list(reversed(index.sorted_sessions()))

        deleted = 0
        for meta in ordered:
            if self._total_size() <= self._max_bytes:
                break
            session_file = self._session_file(meta.session_id)
            try:
                if session_file.exists():
                    session_file.unlink()
            except (OSError, IOError) as e:
                logger.warning(
                    "Could not delete session file %s, skipping: %s", session_file, e
                )
                continue

            index.sessions.pop(meta.session_id, None)
            deleted += 1

        self._save_index(index)
        return deleted

    def clear_all(self) -> int:
        """Delete all session .jsonl files and reset the index to empty.

        Returns the number of sessions deleted.
        """
        deleted = 0
        for f in list(self._store.glob("*.jsonl")):
            try:
                f.unlink()
                deleted += 1
            except (OSError, IOError) as e:
                logger.warning("Could not delete session file %s: %s", f, e)

        self._save_index(SessionIndex())
        return deleted

    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session file and remove it from the index.

        Returns True if the session was found and deleted, False otherwise.
        """
        index = self._load_index()
        if session_id not in index.sessions:
            return False

        session_file = self._session_file(session_id)
        try:
            if session_file.exists():
                session_file.unlink()
        except (OSError, IOError) as e:
            logger.warning("Could not delete session file %s: %s", session_file, e)

        index.sessions.pop(session_id, None)
        self._save_index(index)
        return True
