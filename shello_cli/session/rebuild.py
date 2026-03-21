"""Index rebuild utility for session history.

Scans all .jsonl files in the session store and reconstructs the SessionIndex
from the actual file contents. Used when the index is corrupted or missing.
"""

import logging
import re
from pathlib import Path

from .models import SessionIndex, SessionMetadata
from .serializer import SessionSerializer

logger = logging.getLogger(__name__)

_SESSION_FILE_RE = re.compile(r"^session_(.+)\.jsonl$")


def rebuild_index(session_store_path: Path) -> SessionIndex:
    """Rebuild SessionIndex by scanning all .jsonl files in the session store.

    For each valid session file:
    - Extracts session_id from the filename
    - Parses the first entry for start_time and working_directory
    - Counts all valid entries for entry_count
    - Parses the last entry's timestamp for end_time
    - Extracts first_user_message from the first 'user_prompt' entry

    Corrupted or unreadable files are skipped with a warning.

    Args:
        session_store_path: Path to the session store directory.

    Returns:
        A freshly built SessionIndex.
    """
    index = SessionIndex()

    if not session_store_path.exists():
        return index

    for jsonl_file in sorted(session_store_path.glob("*.jsonl")):
        match = _SESSION_FILE_RE.match(jsonl_file.name)
        if not match:
            continue

        session_id = match.group(1)

        try:
            meta = _extract_metadata(jsonl_file, session_id)
        except Exception as e:
            logger.warning("Skipping corrupted session file %s: %s", jsonl_file.name, e)
            continue

        if meta is not None:
            index.sessions[session_id] = meta

    return index


def _extract_metadata(jsonl_file: Path, session_id: str) -> SessionMetadata | None:
    """Parse a single .jsonl file and extract SessionMetadata.

    Returns None if the file has no valid entries.
    """
    first_entry = None
    last_entry = None
    entry_count = 0
    first_user_message = None
    provider = ""
    model = ""
    working_directory = ""
    resumed_from = None

    try:
        lines = jsonl_file.read_text(encoding="utf-8").splitlines()
    except OSError as e:
        logger.warning("Cannot read session file %s: %s", jsonl_file.name, e)
        return None

    for line in lines:
        entry = SessionSerializer.deserialize(line)
        if entry is None:
            continue

        entry_count += 1

        if first_entry is None:
            first_entry = entry

        last_entry = entry

        if first_user_message is None and entry.entry_type == "user_prompt":
            first_user_message = entry.content or None

        if entry.entry_type == "session_resumed" and resumed_from is None:
            resumed_from = entry.metadata.get("original_session_id")

        # Extract provider/model from banner or api_message metadata if present
        if not provider and entry.entry_type == "banner":
            provider = entry.metadata.get("provider", "")
            model = entry.metadata.get("model", "")

        if not working_directory and entry.entry_type == "user_prompt":
            working_directory = entry.metadata.get("working_directory", "")

    if first_entry is None:
        return None

    return SessionMetadata(
        session_id=session_id,
        start_time=first_entry.timestamp,
        end_time=last_entry.timestamp if last_entry is not first_entry else None,
        working_directory=working_directory,
        entry_count=entry_count,
        provider=provider,
        model=model,
        first_user_message=first_user_message,
        resumed_from=resumed_from,
    )
