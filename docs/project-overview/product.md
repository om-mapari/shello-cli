# Shello CLI - Product Overview & Capabilities

Shello CLI is an AI-powered, terminal-native assistant designed to safely execute commands, run diagnostics, and debug production infrastructure (Cloud, Kubernetes, Docker, logging systems).

---

## Core Value Proposition

### 1. Interactive Command Execution
Unlike basic wrapper scripts that merely output suggestions, Shello executes actual local and remote shell commands statefully. It maintains context directories and active subprocess states across multiple prompt/response turns.

### 2. Token-Optimized Output Pipeline
Dumping thousands of lines of terminal logs to an LLM is expensive and causes context window exhaustion. Shello filters and reduces payload sizes automatically:
* **Semantic Truncation**: Intelligently keeps the critical parts (e.g. the end of stack traces, both ends of compilation logs, or the top of directories/lists).
* **Progress Bar Compression**: Condenses hundreds of repeating lines of build outputs (e.g. `npm install` or `docker build` progress steps) into their single final status line.
* **JSON Intelligence**: Uses the `analyze_json` tool to inspect massive API outputs. It summarizes the JSON structure with `jq` paths, letting the LLM construct specific, targeted `jq` queries instead of reading raw logs.
* **100MB Output Cache**: Truncated outputs are stored in a local cache. The LLM can retrieve specific slices using a `cache_id` (e.g. `cmd_002`) and standard line offset syntax.

---

## Technical Features

### 1. Native Remote Execution
Shello natively supports SSH command execution via the cached `run_remote_command` tool.
* **Configuration**: Seamlessly handles project-level `.shello/settings.yml` connection specifications (supporting keys, password credentials, and ports).
* **Sudo Wrapping**: Automatically wraps elevated commands non-interactively using password pipes or passwordless sudo configurations.

### 2. Command Safety & Trust Manager
Security is first-class. Every shell command is run through a local evaluation pipeline:
* **Allowlist & Denylist**: Checks regex patterns to block or instantly approve commands.
* **Safety Modes**:
  - `user_driven`: Destructive/untrusted commands show an interactive keyboard picker dialog before executing.
  - `yolo_mode`: Automatically runs commands for CI/CD automation while still enforcing denylist rules.

### 3. Developer UI Aesthetics
The console is designed to look like a premium terminal, using box-drawing characters and clean color-coded feedback:
* **Headers**: Distinct headers separate local execution (`┌─[💻 user@host]─[path]`) from remote connections (`┌─[🖥️ username@host]─[~]`).
* **Command Indicators**: Includes specific icons for execution (`$`), input injection (`→ stdin:`), signal interrupts (`⌃C`), and session resets (`↺`).
* **Contextual Status**: Integrates traffic-light color codes:
  - ⏳ **Yellow**: Process is still active in the background, waiting for input or polling.
  - ℹ **Cyan**: Informational updates, signals, or process control completions.
  - ✗ **Red**: True command failures or syntax crashes.
