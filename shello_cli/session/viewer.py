"""Session viewer for rendering past session contents to the terminal.

Reads a session .jsonl file via SessionSerializer and renders each entry
with the same visual formatting used during the original session.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import SessionEntry
from .serializer import SessionSerializer
from ..ui.ui_renderer import console, render_tool_execution, render_direct_command_output
from ..ui.custom_markdown import EnhancedMarkdown


class SessionViewer:
    """Reads and renders a session file to the terminal."""

    def __init__(self, session_store_path: Path) -> None:
        self._store_path = session_store_path

    def render(self, session_id: str) -> bool:
        """Render session contents to terminal.

        Reads the session .jsonl file, renders each entry with original
        formatting, and displays timestamps. Returns True if any api_message
        entries exist (i.e. conversation state is present).
        """
        session_file = self._store_path / f"session_{session_id}.jsonl"

        if not session_file.exists():
            console.print(f"[red]Session file not found: session_{session_id}.jsonl[/red]")
            return False

        has_conversation_state = False

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = SessionSerializer.deserialize(line)
                    if entry is None:
                        continue

                    if entry.entry_type == "api_message":
                        has_conversation_state = True
                        continue  # Don't render api_message entries

                    self._render_entry(entry)
        except OSError as e:
            console.print(f"[red]Error reading session file: {e}[/red]")
            return False

        return has_conversation_state

    def get_conversation_state(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        """Extract API messages from session file for resumption.

        Returns a list of API message dicts (role, content, tool_calls,
        tool_call_id), or None if no api_message entries are found.
        """
        session_file = self._store_path / f"session_{session_id}.jsonl"

        if not session_file.exists():
            return None

        messages: List[Dict[str, Any]] = []

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                for line in f:
                    entry = SessionSerializer.deserialize(line)
                    if entry is None:
                        continue
                    if entry.entry_type == "api_message":
                        msg: Dict[str, Any] = {
                            "role": entry.metadata.get("role", ""),
                            "content": entry.content,
                        }
                        tool_calls = entry.metadata.get("tool_calls")
                        if tool_calls is not None:
                            msg["tool_calls"] = tool_calls
                        tool_call_id = entry.metadata.get("tool_call_id")
                        if tool_call_id is not None:
                            msg["tool_call_id"] = tool_call_id
                        messages.append(msg)
        except OSError:
            return None

        return messages if messages else None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _render_entry(self, entry: SessionEntry) -> None:
        """Render a single session entry to the console."""
        # Print dim timestamp before each entry
        ts = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        console.print(f"[dim]{ts}[/dim]")

        entry_type = entry.entry_type

        if entry_type == "banner":
            console.print(entry.content, style="dim")

        elif entry_type == "user_prompt":
            username = entry.metadata.get("username", "user")
            console.print(f"🌊 [bold]{username}[/bold]")
            console.print(entry.content)

        elif entry_type == "ai_response":
            console.print("🐚 ", end="")
            console.print(EnhancedMarkdown(entry.content))

        elif entry_type == "tool_execution":
            rendered_header = entry.metadata.get("rendered_header")
            if rendered_header:
                console.print(rendered_header)
            else:
                tool_name = entry.metadata.get("tool_name", "")
                parameters = entry.metadata.get("parameters", {})
                cwd = entry.metadata.get("cwd")
                render_tool_execution(tool_name, parameters, cwd)

        elif entry_type == "tool_output":
            console.print(entry.content)

        elif entry_type == "direct_command":
            command = entry.metadata.get("command", entry.content)
            cwd = entry.metadata.get("cwd")
            render_direct_command_output(command, cwd)
            console.print(entry.content)

        elif entry_type == "error":
            console.print(entry.content, style="red")

        elif entry_type == "session_resumed":
            original_id = entry.metadata.get("original_session_id", "unknown")
            console.print(
                f"[dim]↩ Session resumed from {original_id}[/dim]"
            )

        # api_message is handled in render() — skipped here
