"""Session recorder for capturing terminal events during a Shello CLI session.

Writes SessionEntry records to a JSON Lines file and maintains the SessionIndex.
Designed for crash-safety via append-only writes and graceful error handling
that never interferes with normal CLI operation.
"""

import logging
import os
import random
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .models import SessionEntry, SessionIndex, SessionMetadata
from .serializer import SessionSerializer

logger = logging.getLogger(__name__)


class SessionRecorder:
    """Captures session events and persists them to disk.

    Usage:
        recorder = SessionRecorder(store_path, provider="openai", model="gpt-4o")
        recorder.start()
        recorder.record(SessionEntry(...))
        recorder.record_api_message({"role": "user", "content": "hello"})
        recorder.finalize()
    """

    def __init__(self, session_store_path: Path, provider: str, model: str) -> None:
        self._store_path = session_store_path
        self._provider = provider
        self._model = model
        self._session_id: Optional[str] = None
        self._file_handle = None
        self._sequence: int = 0
        self._is_recording: bool = False
        self._index: Optional[SessionIndex] = None
        self._entry_count: int = 0
        self._first_user_message_captured: bool = False

    @property
    def session_id(self) -> Optional[str]:
        return self._session_id

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    def start(self) -> None:
        """Create a new session file and begin recording."""
        try:
            self._store_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Cannot create session store directory %s: %s", self._store_path, e)
            self._is_recording = False
            return

        self._session_id = self._generate_session_id()
        session_file = self._store_path / f"session_{self._session_id}.jsonl"

        try:
            self._file_handle = open(session_file, "a", encoding="utf-8")  # noqa: SIM115
        except OSError as e:
            logger.warning("Cannot open session file %s: %s", session_file, e)
            self._is_recording = False
            return

        self._is_recording = True
        self._sequence = 0
        self._entry_count = 0
        self._first_user_message_captured = False

        # Load or create the index
        self._index = self._load_index()
        self._index.sessions[self._session_id] = SessionMetadata(
            session_id=self._session_id,
            start_time=datetime.now(timezone.utc),
            working_directory=os.getcwd(),
            provider=self._provider,
            model=self._model,
        )
        self._save_index()

    def resume(self, session_id: str) -> None:
        """Reopen an existing session file for appending (resume mode).

        Instead of creating a new session, this attaches the recorder to an
        existing session file so all new entries are appended to it.
        """
        try:
            self._store_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Cannot access session store directory %s: %s", self._store_path, e)
            self._is_recording = False
            return

        session_file = self._store_path / f"session_{session_id}.jsonl"
        try:
            self._file_handle = open(session_file, "a", encoding="utf-8")  # noqa: SIM115
        except OSError as e:
            logger.warning("Cannot open session file %s for resume: %s", session_file, e)
            self._is_recording = False
            return

        self._session_id = session_id
        self._is_recording = True
        self._first_user_message_captured = True  # Don't overwrite existing first_user_message

        # Load index and count existing entries to continue sequence numbering
        self._index = self._load_index()
        existing_meta = self._index.sessions.get(session_id)
        self._sequence = existing_meta.entry_count if existing_meta else 0
        self._entry_count = self._sequence

    def record(self, entry: SessionEntry) -> None:
        """Assign a sequence number and append the entry to the session file.

        Auto-starts the session on first call if not already started.
        On first user_prompt entry, captures first_user_message in the index.
        If a write fails, logs a warning and continues.
        """
        # Lazy start: create the session file on first record() call.
        if not self._is_recording and self._session_id is None:
            self.start()

        if not self._is_recording or self._file_handle is None:
            return

        entry.sequence = self._sequence
        self._sequence += 1

        # Capture first user message for the index label
        if (
            entry.entry_type == "user_prompt"
            and not self._first_user_message_captured
            and self._index is not None
            and self._session_id is not None
        ):
            meta = self._index.sessions.get(self._session_id)
            if meta is not None:
                meta.first_user_message = entry.content
                self._first_user_message_captured = True
                self._save_index()

        try:
            line = SessionSerializer.serialize(entry)
            self._file_handle.write(line + "\n")
            self._file_handle.flush()
            self._entry_count += 1
        except OSError as e:
            logger.warning("Failed to write session entry: %s", e)

    def record_api_message(self, message: Dict[str, Any]) -> None:
        """Record an API-level message as a SessionEntry of type 'api_message'."""
        if not self._is_recording and self._session_id is None:
            self.start()
        if not self._is_recording:
            return

        entry = SessionEntry(
            entry_type="api_message",
            timestamp=datetime.now(timezone.utc),
            sequence=0,  # Will be assigned by record()
            content=message.get("content", "") or "",
            metadata={
                "role": message.get("role", ""),
                "tool_calls": message.get("tool_calls"),
                "tool_call_id": message.get("tool_call_id"),
            },
        )
        self.record(entry)

    def finalize(self) -> None:
        """Write end_time to the index, flush and close the file handle."""
        if self._index is not None and self._session_id is not None:
            meta = self._index.sessions.get(self._session_id)
            if meta is not None:
                meta.end_time = datetime.now(timezone.utc)
                meta.entry_count = self._entry_count
                self._save_index()

        if self._file_handle is not None:
            try:
                self._file_handle.flush()
                self._file_handle.close()
            except OSError as e:
                logger.warning("Error closing session file: %s", e)
            finally:
                self._file_handle = None

        self._is_recording = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_session_id() -> str:
        """Generate a session ID in the format YYYYMMDD_HHMMSS_{short_random}."""
        now = datetime.now(timezone.utc)
        timestamp_part = now.strftime("%Y%m%d_%H%M%S")
        random_part = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
        return f"{timestamp_part}_{random_part}"

    def _load_index(self) -> SessionIndex:
        """Load the session index from disk, or return an empty one."""
        index_path = self._store_path / "index.json"
        if index_path.exists():
            try:
                data = index_path.read_text(encoding="utf-8")
                return SessionSerializer.deserialize_index(data)
            except OSError as e:
                logger.warning("Failed to read session index: %s", e)
        return SessionIndex()

    def _save_index(self) -> None:
        """Persist the session index to disk."""
        if self._index is None:
            return
        index_path = self._store_path / "index.json"
        try:
            data = SessionSerializer.serialize_index(self._index)
            index_path.write_text(data, encoding="utf-8")
        except OSError as e:
            logger.warning("Failed to write session index: %s", e)
