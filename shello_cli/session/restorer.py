"""Session restorer for resuming past Shello CLI sessions.

Rebuilds ShelloAgent state from a stored Conversation_State, replacing
_messages and _chat_history with the restored content. Handles system
prompt rebuilding, context window truncation, and provider/model mismatch
warnings.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rich.console import Console

from shello_cli.agent.models import ChatEntry
from shello_cli.session.models import SessionMetadata

if TYPE_CHECKING:
    from shello_cli.agent.shello_agent import ShelloAgent

logger = logging.getLogger(__name__)

# Conservative default context window (tokens) used when the model limit is unknown.
_DEFAULT_CONTEXT_WINDOW = 128_000

# Rough heuristic: 1 token ≈ 4 characters.
_CHARS_PER_TOKEN = 4

_console = Console()


def _estimate_tokens(message: Dict[str, Any]) -> int:
    """Estimate the token count for a single API message dict."""
    content = message.get("content") or ""
    if not isinstance(content, str):
        # content can be a list of content blocks (vision, etc.)
        try:
            content = str(content)
        except Exception:
            content = ""
    return max(1, len(content) // _CHARS_PER_TOKEN)


class SessionRestorer:
    """Restores a ShelloAgent's conversation state from a saved session.

    Usage::

        restorer = SessionRestorer()
        restorer.restore(agent, conversation_state, original_session_meta)
    """

    def restore(
        self,
        agent: "ShelloAgent",
        conversation_state: List[Dict[str, Any]],
        original_session_meta: SessionMetadata,
        context_window: Optional[int] = None,
    ) -> None:
        """Replace agent state with the restored conversation.

        Steps:
        1. Detect and warn about provider/model mismatch (Req 4.11).
        2. Rebuild the system prompt using current system info (Req 4.5).
        3. Filter out any system messages from the original state (Req 4.8).
        4. Truncate oldest non-system messages if context window exceeded (Req 4.10).
        5. Replace agent._messages and agent._chat_history (Req 4.4, 4.8).

        Args:
            agent: The ShelloAgent whose state will be replaced.
            conversation_state: List of API-level message dicts from the session file.
            original_session_meta: Metadata of the original session (provider, model, etc.).
            context_window: Optional token limit override. Defaults to _DEFAULT_CONTEXT_WINDOW.
        """
        limit = context_window if context_window is not None else _DEFAULT_CONTEXT_WINDOW

        # --- 1. Provider/model mismatch warning (Req 4.11) ---
        self._check_provider_model_mismatch(agent, original_session_meta)

        # --- 2. Rebuild system prompt with current system info (Req 4.5) ---
        new_system_prompt = agent._build_system_prompt()
        system_message: Dict[str, Any] = {"role": "system", "content": new_system_prompt}

        # --- 3. Filter out original system messages (Req 4.8) ---
        non_system = [m for m in conversation_state if m.get("role") != "system"]

        # --- 4. Context window truncation (Req 4.10) ---
        non_system = self._truncate_to_context_window(non_system, system_message, limit)

        # --- 4b. Sanitize tool call / tool result pairing ---
        non_system = self._sanitize_tool_pairs(non_system)

        # --- 5. Rebuild agent state ---
        agent._messages = [system_message] + non_system
        agent._chat_history = self._rebuild_chat_history(non_system)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_provider_model_mismatch(
        self,
        agent: "ShelloAgent",
        original_meta: SessionMetadata,
    ) -> None:
        """Warn if the current provider/model differs from the original session."""
        try:
            from shello_cli.settings.manager import SettingsManager
            settings = SettingsManager.get_instance()
            current_provider = settings.get_provider()
            current_model = agent.get_current_model()
        except Exception:
            # If we can't determine current settings, skip the check silently.
            return

        mismatches: List[str] = []
        if current_provider != original_meta.provider:
            mismatches.append(
                f"provider: original={original_meta.provider!r}, current={current_provider!r}"
            )
        if current_model != original_meta.model:
            mismatches.append(
                f"model: original={original_meta.model!r}, current={current_model!r}"
            )

        if mismatches:
            _console.print(
                f"[yellow]⚠ Provider/model mismatch — {', '.join(mismatches)}. "
                "Resuming with current configuration.[/yellow]"
            )

    def _truncate_to_context_window(
        self,
        non_system: List[Dict[str, Any]],
        system_message: Dict[str, Any],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Remove oldest non-system messages until total tokens fit within limit.

        The system message token cost is always counted. Remaining budget is
        filled from the newest messages backwards (Property 9: contiguous suffix).

        Args:
            non_system: Non-system messages in chronological order.
            system_message: The rebuilt system message (always included).
            limit: Maximum token budget.

        Returns:
            A (possibly truncated) list of non-system messages, newest-first preserved.
        """
        system_tokens = _estimate_tokens(system_message)
        budget = limit - system_tokens

        if budget <= 0:
            # Pathological: system prompt alone exceeds limit — keep nothing.
            _console.print(
                "[yellow]⚠ System prompt exceeds context window. "
                "Conversation history could not be restored.[/yellow]"
            )
            return []

        # Walk from newest to oldest, accumulating until budget exhausted.
        kept: List[Dict[str, Any]] = []
        used = 0
        for msg in reversed(non_system):
            cost = _estimate_tokens(msg)
            if used + cost > budget:
                break
            kept.append(msg)
            used += cost

        kept.reverse()  # restore chronological order

        trimmed = len(non_system) - len(kept)
        if trimmed > 0:
            _console.print(
                f"[yellow]⚠ Context window limit reached — {trimmed} oldest message(s) "
                "were trimmed to fit the restored conversation.[/yellow]"
            )

        return kept

    def _sanitize_tool_pairs(
        self, non_system: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Ensure every tool result has a matching tool_call in the preceding assistant message.

        Bedrock requires that every toolResult block has a matching toolUse in the
        immediately preceding assistant turn. After truncation or recording gaps
        (e.g. old sessions missing the assistant+tool_calls entry), this invariant
        can be violated.

        Strategy:
        1. Orphaned tool results (no preceding assistant with tool_calls) — synthesize
           a minimal assistant message with matching tool_calls so the pair is valid.
        2. Assistant messages with tool_calls but no following tool results — strip the
           tool_calls field so it becomes a plain assistant message.
        3. Partial matches — trim assistant tool_calls to only those with results.
        """
        if not non_system:
            return non_system

        sanitized: List[Dict[str, Any]] = []

        i = 0
        while i < len(non_system):
            msg = non_system[i]
            role = msg.get("role", "")

            if role == "tool":
                # Orphaned tool results — synthesize a minimal assistant message
                # with tool_calls matching all consecutive orphaned tool results.
                tool_msgs: List[Dict[str, Any]] = []
                while i < len(non_system) and non_system[i].get("role") == "tool":
                    tool_msgs.append(non_system[i])
                    i += 1

                synthetic_calls = []
                for t in tool_msgs:
                    tid = t.get("tool_call_id", "")
                    if tid:
                        synthetic_calls.append({
                            "id": tid,
                            "type": "function",
                            "function": {"name": "run_shell_command", "arguments": "{}"},
                        })

                if synthetic_calls:
                    sanitized.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": synthetic_calls,
                    })
                # Keep tool messages regardless — even without tool_call_ids.
                sanitized.extend(tool_msgs)
                continue

            if role == "assistant":
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    expected_ids = {tc.get("id") for tc in tool_calls if tc.get("id")}

                    # Peek ahead: gather consecutive tool-result messages.
                    j = i + 1
                    following_tool_msgs: List[Dict[str, Any]] = []
                    while j < len(non_system) and non_system[j].get("role") == "tool":
                        following_tool_msgs.append(non_system[j])
                        j += 1

                    matched = [
                        t for t in following_tool_msgs
                        if t.get("tool_call_id") in expected_ids
                    ]
                    matched_ids = {t.get("tool_call_id") for t in matched}

                    if not matched:
                        # No tool results — strip tool_calls, keep as plain assistant msg.
                        msg = dict(msg)
                        msg.pop("tool_calls", None)
                        sanitized.append(msg)
                        i = j
                        continue

                    if matched_ids != expected_ids:
                        # Partial match — trim tool_calls to only matched ones.
                        filtered_calls = [
                            tc for tc in tool_calls if tc.get("id") in matched_ids
                        ]
                        msg = dict(msg)
                        msg["tool_calls"] = filtered_calls

                    sanitized.append(msg)
                    sanitized.extend(matched)
                    i = j
                    continue
                else:
                    sanitized.append(msg)
                    i += 1
                    continue

            # user or other roles — keep as-is.
            sanitized.append(msg)
            i += 1

        return sanitized

    def _rebuild_chat_history(
        self, non_system: List[Dict[str, Any]]
    ) -> List[ChatEntry]:
        """Convert API message dicts back into ChatEntry objects.

        Only user, assistant, and tool messages are mapped; other roles are
        silently skipped.

        Args:
            non_system: Non-system API message dicts in chronological order.

        Returns:
            List of ChatEntry objects.
        """
        history: List[ChatEntry] = []
        now = datetime.now()

        for msg in non_system:
            role = msg.get("role", "")
            content = msg.get("content") or ""
            if not isinstance(content, str):
                content = str(content)

            if role == "user":
                history.append(ChatEntry(type="user", content=content, timestamp=now))
            elif role == "assistant":
                history.append(ChatEntry(type="assistant", content=content, timestamp=now))
            elif role == "tool":
                history.append(ChatEntry(type="tool_result", content=content, timestamp=now))
            # Other roles (e.g. function) are skipped.

        return history
