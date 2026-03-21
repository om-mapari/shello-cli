# Session History

Shello CLI automatically records every session to disk. The `/history` command lets you browse past sessions in an interactive list, replay what happened, and seamlessly resume the conversation with full AI context.

---

## Table of Contents

- [Session History](#session-history)
  - [Table of Contents](#table-of-contents)
  - [Quick Start](#quick-start)
  - [Commands](#commands)
    - [`/history`](#history)
    - [`/history clear`](#history-clear)
    - [`/history delete`](#history-delete)
  - [How It Works](#how-it-works)
    - [Recording](#recording)
    - [Browsing](#browsing)
    - [Viewing and Resuming](#viewing-and-resuming)
    - [Storage Management](#storage-management)
  - [Configuration](#configuration)
  - [Storage Layout](#storage-layout)
  - [Session Entry Types](#session-entry-types)
  - [File Formats](#file-formats)
    - [Session File (`.jsonl`)](#session-file-jsonl)
    - [Session Index (`index.json`)](#session-index-indexjson)
  - [Architecture](#architecture)
    - [Components](#components)
    - [Integration Points](#integration-points)
    - [Data Models](#data-models)
  - [Error Handling](#error-handling)
  - [Limitations](#limitations)

---

## Quick Start

```
/history           # Browse and resume a past session
/history clear     # Delete all session history
/history delete    # Pick and delete a specific session
```

---

## Commands

### `/history`

Opens an interactive, arrow-key-navigable list of all past sessions sorted newest first. Each entry shows the first message you sent in that session, the date/time, and the provider/model used.

```
 > debug the failing kubernetes pod          2025-01-15 14:30  bedrock/claude-sonnet
   list all python files in the project      2025-01-14 09:15  openai/gpt-4o
   why is my docker container OOMKilling     2025-01-13 22:40  openai/gpt-4o
```

**Navigation:**
- `↑` / `↓` — move between sessions
- `Enter` — select and view/resume
- `Escape` or `Ctrl+C` — cancel and return to the prompt

If no sessions exist, a message is displayed and you return to the normal prompt.

### `/history clear`

Deletes all session files and resets the index. Requires confirmation.

```
⚠️  Delete ALL session history? This cannot be undone [y/N]:
```

### `/history delete`

Opens the session picker to select a specific session to delete. Requires confirmation before deletion.

---

## How It Works

### Recording

A new session file is created automatically when Shello starts. Every visible terminal event is captured as a timestamped entry:

- The welcome banner
- Every prompt you submit
- Every AI response
- Every tool execution and its output
- Direct commands (those executed without AI routing)
- Errors

In addition to the terminal-visible events, each API-level message (the raw messages sent to and received from the AI provider) is also recorded. This is what enables conversation resumption.

Recording is **append-only** — each entry is flushed to disk immediately. If the process crashes, everything up to that point is preserved.

The session is finalized (end time written to the index) when you:
- Type `/quit` or `/exit`
- Press `Ctrl+C` or `Ctrl+D`
- Start a new conversation with `/new`

### Browsing

The session picker reads from a lightweight `index.json` file — it does not parse individual session files. This makes listing fast regardless of how many sessions exist or how large they are.

Sessions with no recorded user message (e.g. a session where you only pressed Ctrl+C immediately) are hidden from the list. If a session was resumed from another, the original is also hidden to avoid showing duplicates.

### Viewing and Resuming

When you select a session:

1. A summary header is printed:
   ```
   ── Session from 2025-01-15 14:30:00 │ 42 entries │ bedrock/claude-sonnet ──
   ```

2. The full session is replayed to the terminal with the original formatting:
   - User prompts with the `🌊` prefix
   - AI responses with the `🐚` prefix and markdown rendering
   - Tool executions with box-drawing headers
   - Direct commands with their output
   - Timestamps shown in dim text before each entry

3. The conversation is automatically resumed. The AI receives the full original message history so it has complete context of what was discussed.

**What changes on resume:**
- The system prompt is rebuilt fresh with your current OS, shell, working directory, and datetime — not the original session's system info.
- New entries are appended to the original session file (not a new file), with a `session_resumed` marker entry.
- The session index is updated with a `resumed_from` reference.

**Warnings shown on resume:**
- If the current provider or model differs from the original session, a yellow warning is printed and the current configuration is used.
- If the conversation history is too long for the model's context window, the oldest messages are trimmed and a warning is shown indicating how many were removed.

### Storage Management

Sessions are stored in `~/.shello_cli/sessions/`. The total size is capped at **50 MB** by default. After each new session starts, the pruner runs automatically and deletes the oldest sessions until the total is within the limit.

Corrupted or unreadable session files are skipped during pruning — they do not block deletion of other files.

---

## Configuration

Add a `session_history` section to `~/.shello_cli/user-settings.yml`:

```yaml
session_history:
  enabled: true        # Set to false to disable recording entirely (default: true)
  max_storage_mb: 50   # Maximum total storage for all session files (default: 50)
```

When `enabled: false`, the recorder is not started and no session files are written. All other Shello functionality is unaffected.

---

## Storage Layout

```
~/.shello_cli/sessions/
├── index.json                           # Lightweight index for fast session listing
├── session_20250115_143000_a1b2.jsonl   # Session file (JSON Lines)
├── session_20250114_091500_c3d4.jsonl
└── ...
```

**Session ID format:** `YYYYMMDD_HHMMSS_{4-char random}` — e.g. `20250115_143000_a1b2`

**Session file naming:** `session_{session_id}.jsonl`

---

## Session Entry Types

Each line in a `.jsonl` session file is one event. The `entry_type` field identifies what kind of event it is:

| `entry_type` | Description |
|---|---|
| `banner` | The welcome banner displayed at startup |
| `user_prompt` | A message submitted by the user. `metadata.working_directory` contains the cwd at the time. |
| `ai_response` | The complete AI response text |
| `tool_execution` | A tool call initiated by the AI. `metadata` contains `tool_name`, `parameters`, and `rendered_header`. |
| `tool_output` | Output returned from a tool execution. `metadata.tool_name` identifies the tool. |
| `direct_command` | A command executed directly (bypassing AI). `metadata` contains `command`, `cwd`, and `success`. |
| `error` | An error that occurred during processing |
| `api_message` | A raw API-level message (role, content, tool_calls, tool_call_id). Used for conversation resumption — not rendered during replay. |
| `session_resumed` | Marker written when a session is resumed. `metadata.original_session_id` references the source session. |

---

## File Formats

### Session File (`.jsonl`)

One JSON object per line. Each line is a serialized `SessionEntry`. Example:

```jsonl
{"content":"[banner text]","entry_type":"banner","metadata":{},"sequence":0,"timestamp":"2025-01-15T14:30:00.123456+00:00"}
{"content":"debug the failing kubernetes pod","entry_type":"user_prompt","metadata":{"working_directory":"/home/user/project"},"sequence":1,"timestamp":"2025-01-15T14:30:05.654321+00:00"}
{"content":"debug the failing kubernetes pod","entry_type":"api_message","metadata":{"role":"user","tool_call_id":null,"tool_calls":null},"sequence":2,"timestamp":"2025-01-15T14:30:05.654400+00:00"}
{"content":"I'll check the pod logs for you.","entry_type":"ai_response","metadata":{},"sequence":3,"timestamp":"2025-01-15T14:30:07.111111+00:00"}
{"content":"I'll check the pod logs for you.","entry_type":"api_message","metadata":{"role":"assistant","tool_call_id":null,"tool_calls":[{"id":"call_1","type":"function","function":{"name":"run_shell_command","arguments":"{\"command\":\"kubectl logs pod/my-pod\"}"}}]},"sequence":4,"timestamp":"2025-01-15T14:30:07.111200+00:00"}
```

Keys are sorted alphabetically and the file uses UTF-8 encoding. Malformed lines are skipped during reading — they do not cause the viewer or restorer to fail.

### Session Index (`index.json`)

A single JSON file mapping session IDs to metadata. Updated after each session is finalized.

```json
{
  "sessions": {
    "20250115_143000_a1b2": {
      "session_id": "20250115_143000_a1b2",
      "start_time": "2025-01-15T14:30:00.123456+00:00",
      "end_time": "2025-01-15T15:00:00.654321+00:00",
      "working_directory": "/home/user/project",
      "entry_count": 42,
      "provider": "bedrock",
      "model": "claude-sonnet",
      "first_user_message": "debug the failing kubernetes pod",
      "resumed_from": null
    }
  }
}
```

If `index.json` is corrupted or missing, it can be rebuilt by scanning all `.jsonl` files in the session store. The rebuild extracts `start_time` from the first valid entry, `end_time` from the last, `first_user_message` from the first `user_prompt` entry, and counts all valid entries.

---

## Architecture

The feature lives entirely in `shello_cli/session/` and integrates with the existing chat loop through minimal hooks.

### Components

**`SessionRecorder`** (`recorder.py`)

Captures events during a session and writes them to disk. Created at startup in `cli.py` and passed to `ChatSession`. Supports two modes:
- `start()` — creates a new session file and index entry
- `resume(session_id)` — reopens an existing session file for appending

Each call to `record()` assigns a monotonically increasing sequence number and immediately flushes the entry to disk. `record_api_message()` is a convenience wrapper that wraps a raw API message dict into a `SessionEntry` of type `api_message`.

If the session store directory is unwritable, `start()` sets `is_recording = False` and all subsequent `record()` calls become no-ops. Write failures mid-session are logged as warnings but do not stop recording.

---

**`SessionSerializer`** (`serializer.py`)

Converts `SessionEntry` objects to and from JSON Lines format, and `SessionIndex` to and from JSON.

- `serialize(entry)` — uses Pydantic's `model_dump(mode="json")` then `json.dumps` with `sort_keys=True` for deterministic, byte-stable output
- `deserialize(line)` — returns `None` for malformed lines, logging a warning
- `serialize_index(index)` / `deserialize_index(data)` — full index serialization with pretty-printing

---

**`SessionPicker`** (`picker.py`)

Interactive session browser built with `prompt_toolkit`. Reads the index on construction and displays sessions in reverse chronological order.

Label format per entry:
```
{first_user_message truncated to 80 chars}  {YYYY-MM-DD HH:MM}
```

Sessions with no `first_user_message` fall back to the date/time only. Sessions that were the source of a resume operation are hidden to avoid showing both the original and its continuation.

---

**`SessionViewer`** (`viewer.py`)

Reads a session `.jsonl` file and renders each entry to the terminal using the same visual formatting as the original session:

- `banner` entries — printed in dim style
- `user_prompt` entries — `🌊 username` header followed by the prompt text
- `ai_response` entries — `🐚` prefix with `EnhancedMarkdown` rendering
- `tool_execution` entries — rendered via `render_tool_execution()` using the stored `rendered_header` or reconstructed from `tool_name` + `parameters`
- `tool_output` entries — raw content printed directly
- `direct_command` entries — rendered via `render_direct_command_output()` followed by the output
- `error` entries — printed in red
- `session_resumed` entries — dim `↩ Session resumed from {id}` line
- `api_message` entries — skipped (not rendered)

`render()` returns `True` if any `api_message` entries were found (indicating the session can be resumed). `get_conversation_state()` extracts those entries as a list of API message dicts.

---

**`SessionRestorer`** (`restorer.py`)

Rebuilds `ShelloAgent` state from a stored conversation. Called after `SessionViewer.render()` when the session has conversation state.

Steps performed by `restore()`:

1. **Provider/model mismatch check** — compares the original session's provider/model against the current configuration. Prints a yellow warning if they differ.
2. **System prompt rebuild** — calls `agent._build_system_prompt()` to generate a fresh system prompt with current OS, shell, cwd, and datetime.
3. **Filter system messages** — removes any `role: system` messages from the original state (the new system prompt replaces them).
4. **Context window truncation** — estimates token counts using a 1 token ≈ 4 characters heuristic. Walks from newest to oldest, keeping messages until the budget (context window minus system prompt tokens) is exhausted. Prints a warning if any messages were trimmed.
5. **Tool pair sanitization** — ensures every `tool` result message has a matching `tool_calls` entry in the preceding assistant message. Handles three cases: orphaned tool results (synthesizes a minimal assistant message), assistant messages with tool_calls but no results (strips the `tool_calls` field), and partial matches (trims `tool_calls` to only matched IDs). This is required for Bedrock compatibility.
6. **State replacement** — sets `agent._messages` to `[system_message] + non_system` and rebuilds `agent._chat_history` as a list of `ChatEntry` objects.

---

**`SessionPruner`** (`pruner.py`)

Enforces storage limits by deleting old session files.

- `prune()` — calculates total `.jsonl` size, then deletes sessions oldest-first until under the limit. Returns the count deleted.
- `clear_all()` — deletes all `.jsonl` files and resets the index to empty.
- `delete_session(session_id)` — deletes a specific session file and removes it from the index.

Corrupted or unreadable files are skipped with a warning during `prune()`.

---

**`rebuild_index()`** (`rebuild.py`)

A standalone function that scans all `.jsonl` files in the session store and reconstructs the `SessionIndex` from scratch. Called automatically when `index.json` is found to be corrupted. Skips files that cannot be read or parsed.

### Integration Points

**`cli.py`**

- Creates a `SessionRecorder` at startup (if `session_history.enabled` is true in settings).
- Passes the recorder to `ChatSession` via `chat_session.set_recorder()`.
- Handles `/history`, `/history clear`, and `/history delete` via `handle_history_command()` before any other command routing.
- Finalizes the recorder on `/quit`, `/exit`, `/new`, `Ctrl+C`, and `Ctrl+D`.
- Runs `SessionPruner.prune()` after the recorder starts.

**`ChatSession`** (`chat/chat_session.py`)

Records events as they occur during message processing:
- `user_prompt` — when the user submits a message
- `ai_response` — accumulated AI response text
- `tool_execution` — when a tool call begins
- `tool_output` — when tool output is received
- `error` — on exceptions
- `api_message` — for each API-level message (user, assistant, tool results)

**`ShelloAgent`** (`agent/shello_agent.py`)

`SessionRestorer` directly replaces `agent._messages` and `agent._chat_history` on resume, and calls `agent._build_system_prompt()` to generate the fresh system prompt.

### Data Models

All models use Pydantic v2 `BaseModel`.

**`SessionEntry`**

```python
class SessionEntry(BaseModel):
    entry_type: str           # See entry types table above
    timestamp: datetime       # UTC timestamp
    sequence: int             # Monotonically increasing within a session
    content: str = ""         # Primary text content
    metadata: Dict[str, Any]  # Entry-type-specific fields
```

**`SessionMetadata`**

```python
class SessionMetadata(BaseModel):
    session_id: str
    start_time: datetime
    end_time: Optional[datetime]
    working_directory: str
    entry_count: int
    provider: str
    model: str
    first_user_message: Optional[str]  # Used as the picker label
    resumed_from: Optional[str]        # session_id of the original if resumed
```

**`SessionIndex`**

```python
class SessionIndex(BaseModel):
    sessions: Dict[str, SessionMetadata]

    def sorted_sessions(self) -> List[SessionMetadata]:
        # Returns sessions in reverse chronological order (newest first)
```

**`SessionHistoryConfig`**

```python
class SessionHistoryConfig(BaseModel):
    enabled: bool = True
    max_storage_mb: int = 50
```

Added as an optional field on `UserSettings`:

```python
@dataclass
class UserSettings:
    # ... existing fields ...
    session_history: Optional[SessionHistoryConfig] = None
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| Session store directory unwritable | `SessionRecorder.start()` logs a warning and sets `is_recording = False`. All `record()` calls become no-ops. CLI continues normally. |
| Write failure mid-session | `record()` catches `OSError`, logs a warning, and continues. The partial session file remains valid JSONL. |
| Session file corrupted / unreadable | `SessionSerializer.deserialize()` returns `None` for bad lines. `SessionViewer` skips them and renders what it can. `SessionPruner` skips the file during size calculation. |
| Session index corrupted | `SessionIndex` deserialization fails. The index is rebuilt by scanning all `.jsonl` files in the session store. |
| Session file missing for selected session | `SessionViewer.render()` prints an error and returns `False`. The CLI returns to the prompt. |
| No conversation state in session file | `get_conversation_state()` returns `None`. The session is shown as read-only with a warning that it cannot be resumed. |
| Context window exceeded on resume | `SessionRestorer` trims oldest non-system messages and prints a warning with the count trimmed. |
| Provider/model mismatch on resume | A yellow warning is printed. The current provider/model is used. |
| Disk full during recording | `record()` catches `OSError`, logs a warning, and disables recording for the remainder of the session. |
| No sessions in index | `SessionPicker.pick()` prints "No session history available." and returns `None`. |

---

## Limitations

- **Token estimation is approximate.** The restorer uses a 1 token ≈ 4 characters heuristic. Actual token counts vary by model and tokenizer. The context window default is 128,000 tokens when the model limit is not known.
- **Sessions recorded before this feature was added** have no `api_message` entries and cannot be resumed — they are view-only.
- **The `max_storage_mb` limit applies to `.jsonl` files only.** The `index.json` file is not counted toward the limit.
- **Pruning runs after session start, not before.** In edge cases where a single session file exceeds the limit, pruning will delete all older sessions but cannot delete the currently active one.
