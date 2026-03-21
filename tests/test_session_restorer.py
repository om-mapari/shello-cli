"""Tests for SessionRestorer.

Includes property-based tests for correctness properties from the design doc.
"""

from datetime import datetime
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from shello_cli.session.models import SessionMetadata
from shello_cli.session.restorer import SessionRestorer

settings.load_profile("default")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NON_SYSTEM_ROLES = ["user", "assistant", "tool"]


def _make_agent(system_prompt: str = "system prompt", model: str = "unknown-model") -> MagicMock:
    """Return a minimal mock ShelloAgent."""
    agent = MagicMock()
    agent._messages = []
    agent._chat_history = []
    agent._build_system_prompt.return_value = system_prompt
    agent.get_current_model.return_value = model
    return agent


def _make_meta(provider: str = "openai", model: str = "gpt-4o") -> SessionMetadata:
    return SessionMetadata(
        session_id="20250101_120000_abcd",
        start_time=datetime(2025, 1, 1, 12, 0, 0),
        working_directory="/tmp",
        provider=provider,
        model=model,
    )


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Simple text content for messages
_text = st.text(min_size=0, max_size=200)

# A single non-system API message dict
_non_system_message = st.fixed_dictionaries(
    {
        "role": st.sampled_from(NON_SYSTEM_ROLES),
        "content": _text,
    }
)

# A system message (should be filtered out by the restorer)
_system_message = st.fixed_dictionaries(
    {
        "role": st.just("system"),
        "content": _text,
    }
)

# A conversation state: mix of system and non-system messages
_conversation_state = st.lists(
    st.one_of(_non_system_message, _system_message),
    min_size=0,
    max_size=20,
)


# ---------------------------------------------------------------------------
# Property 8: Non-system messages preserved on restore
# Feature: session-history, Property 8: Non-system messages preserved on restore
# ---------------------------------------------------------------------------

@given(conversation_state=_conversation_state)
def test_property8_non_system_messages_preserved(conversation_state: List[Dict[str, Any]]):
    """**Validates: Requirements 4.8**

    For any conversation state, after SessionRestorer.restore() rebuilds the
    agent state, all messages with role != "system" from the original state
    should appear in agent._messages in the same order with identical content.
    """
    # Feature: session-history, Property 8: Non-system messages preserved on restore
    agent = _make_agent()
    meta = _make_meta()
    restorer = SessionRestorer()

    restorer.restore(agent, conversation_state, meta)

    # Collect expected non-system messages (original order)
    expected = [m for m in conversation_state if m.get("role") != "system"]

    # agent._messages[0] is always the (new) system prompt; the rest are non-system
    actual_non_system = [m for m in agent._messages if m.get("role") != "system"]

    assert len(actual_non_system) == len(expected), (
        f"Expected {len(expected)} non-system messages, got {len(actual_non_system)}"
    )

    for i, (actual_msg, expected_msg) in enumerate(zip(actual_non_system, expected)):
        assert actual_msg["role"] == expected_msg["role"], (
            f"Message {i}: role mismatch — expected {expected_msg['role']!r}, "
            f"got {actual_msg['role']!r}"
        )
        assert actual_msg["content"] == expected_msg["content"], (
            f"Message {i}: content mismatch — expected {expected_msg['content']!r}, "
            f"got {actual_msg['content']!r}"
        )


@given(conversation_state=_conversation_state)
def test_property8_system_message_is_rebuilt(conversation_state: List[Dict[str, Any]]):
    """**Validates: Requirements 4.5, 4.8**

    The first message in agent._messages after restore must be a system message
    built from the current system info (not from the original conversation state).
    """
    # Feature: session-history, Property 8: Non-system messages preserved on restore
    fresh_prompt = "fresh system prompt for current env"
    agent = _make_agent(system_prompt=fresh_prompt)
    meta = _make_meta()
    restorer = SessionRestorer()

    restorer.restore(agent, conversation_state, meta)

    assert len(agent._messages) >= 1
    first = agent._messages[0]
    assert first["role"] == "system"
    assert first["content"] == fresh_prompt


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_restore_empty_conversation_state():
    """Restoring an empty conversation state leaves only the system message."""
    agent = _make_agent()
    meta = _make_meta()
    restorer = SessionRestorer()

    restorer.restore(agent, [], meta)

    assert len(agent._messages) == 1
    assert agent._messages[0]["role"] == "system"
    assert agent._chat_history == []


def test_restore_filters_system_messages():
    """System messages in the original state are not carried over."""
    conversation_state = [
        {"role": "system", "content": "old system prompt"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    agent = _make_agent()
    meta = _make_meta()
    restorer = SessionRestorer()

    restorer.restore(agent, conversation_state, meta)

    roles = [m["role"] for m in agent._messages]
    # Only one system message (the rebuilt one), then user + assistant
    assert roles.count("system") == 1
    assert roles[0] == "system"
    assert roles[1:] == ["user", "assistant"]


def test_restore_preserves_order():
    """Non-system messages appear in original order after restore."""
    conversation_state = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "second"},
        {"role": "user", "content": "third"},
        {"role": "tool", "content": "fourth"},
    ]
    agent = _make_agent()
    meta = _make_meta()
    restorer = SessionRestorer()

    restorer.restore(agent, conversation_state, meta)

    non_system = [m for m in agent._messages if m["role"] != "system"]
    contents = [m["content"] for m in non_system]
    assert contents == ["first", "second", "third", "fourth"]


def test_restore_rebuilds_chat_history():
    """agent._chat_history is rebuilt with correct types and content."""
    conversation_state = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "world"},
    ]
    agent = _make_agent()
    meta = _make_meta()
    restorer = SessionRestorer()

    restorer.restore(agent, conversation_state, meta)

    assert len(agent._chat_history) == 2
    assert agent._chat_history[0].type == "user"
    assert agent._chat_history[0].content == "hello"
    assert agent._chat_history[1].type == "assistant"
    assert agent._chat_history[1].content == "world"
