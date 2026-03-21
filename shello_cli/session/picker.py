"""Interactive session picker using prompt_toolkit.

Displays a scrollable list of past sessions in reverse chronological order,
allowing the user to select one with arrow keys and Enter.
"""

from pathlib import Path
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl

from .models import SessionIndex, SessionMetadata
from .serializer import SessionSerializer

_MAX_MSG_LEN = 80


def _truncate(text: str, max_len: int = _MAX_MSG_LEN) -> str:
    """Truncate text to max_len chars, appending '...' if truncated."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _format_date(meta: SessionMetadata) -> str:
    """Format start_time as YYYY-MM-DD HH:MM."""
    return meta.start_time.strftime("%Y-%m-%d %H:%M")


def _make_label(meta: SessionMetadata) -> str:
    """Build the display label for a session entry."""
    date_part = _format_date(meta)
    if meta.first_user_message:
        msg = _truncate(meta.first_user_message)
        return f"{msg}  {date_part}"
    return date_part


class SessionPicker:
    """Interactive prompt_toolkit picker for browsing session history.

    Usage:
        picker = SessionPicker(Path("~/.shello_cli/sessions/").expanduser())
        session_id = picker.pick()  # Returns session_id or None
    """

    def __init__(self, session_store_path: Path) -> None:
        self._store_path = session_store_path
        self._index = self._load_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pick(self) -> Optional[str]:
        """Display interactive picker. Returns selected session_id or None."""
        sessions = self._index.sorted_sessions()

        # Filter: only show sessions that have a first_user_message.
        # Sessions with no user message (banner-only, empty) add noise.
        sessions = [s for s in sessions if s.first_user_message]

        # Deduplicate: if a session was resumed from another, hide the original
        # so the list doesn't show both the source and the continuation.
        resumed_from_ids = {s.resumed_from for s in sessions if s.resumed_from}
        sessions = [s for s in sessions if s.session_id not in resumed_from_ids]

        if not sessions:
            print("No session history available.")
            return None

        labels = [_make_label(s) for s in sessions]
        state = {"selected": 0, "result": None, "done": False}

        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            state["selected"] = (state["selected"] - 1) % len(sessions)

        @kb.add("down")
        def _down(event):
            state["selected"] = (state["selected"] + 1) % len(sessions)

        @kb.add("enter")
        def _enter(event):
            state["result"] = sessions[state["selected"]].session_id
            state["done"] = True
            event.app.exit()

        @kb.add("escape")
        def _escape(event):
            state["done"] = True
            event.app.exit()

        @kb.add("c-c")
        def _ctrl_c(event):
            state["done"] = True
            event.app.exit()

        def _get_content():
            lines = []
            for i, label in enumerate(labels):
                if i == state["selected"]:
                    lines.append(("class:selected", f" > {label}\n"))
                else:
                    lines.append(("", f"   {label}\n"))
            return FormattedText(lines)

        layout = Layout(
            HSplit([
                Window(
                    content=FormattedTextControl(text=_get_content, focusable=True),
                    wrap_lines=False,
                )
            ])
        )

        from prompt_toolkit.styles import Style
        style = Style.from_dict({"selected": "reverse bold"})

        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=False,
        )

        app.run()
        return state["result"]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_index(self) -> SessionIndex:
        """Load the session index from disk, or return an empty one."""
        index_path = self._store_path / "index.json"
        if index_path.exists():
            try:
                data = index_path.read_text(encoding="utf-8")
                return SessionSerializer.deserialize_index(data)
            except OSError:
                pass
        return SessionIndex()
