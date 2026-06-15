# Remote Execution Guide

Shello CLI supports native remote shell command execution (`run_remote_command`) on a configured remote server over SSH.

This guide explains how remote execution works, how to configure it, and its security mechanisms.

---

## How It Works

1. **Conditional Registration**: The `run_remote_command` tool is dynamically registered in the AI assistant's schema **only if** you have configured a remote server in your settings. If not configured, the tool is completely hidden from the AI to keep your prompts clean.
2. **Native Python Backend**: Remote execution is performed natively in Python using the `paramiko` library. There are no external Node.js, npm, or MCP server dependencies required.
3. **Connection Caching**: SSH connections are established lazily (only when a remote command is actually run) and cached across tool calls. This prevents handshake delays on subsequent remote commands.
4. **Output Pipeline Integration**: Remote command outputs flow through the exact same processing pipeline as local commands (line-padding stripping, progress bar compression, JSON structure analysis, and semantic-aware truncation).

---

## Configuration

You can configure the remote server either globally (in user-level settings) or locally (in project-specific settings). Project-level settings override user-level settings.

### Configuration File Locations
* **Global Settings**: `~/.shello_cli/user-settings.yml`
* **Project Settings**: `.shello/settings.yml` (relative to the directory where you launch Shello)

### Configuration Schema

Add a `remote-server` block to your configuration file:

```yaml
remote-server:
  host: 13.126.25.225            # Remote host IP address or hostname (Required)
  port: 22                       # SSH port (Optional, default: 22)
  username: ec2user              # SSH username (Required)
  password: TempDevom123!2026    # SSH password (Optional if using private key)
  private_key_path: /path/to/key # Path to SSH private key file (Optional if using password)
  sudo_password: sudopassword    # Password for running commands with sudo (Optional)
  disable_sudo: false            # Set true to completely disable sudo commands (Optional, default: false)
  timeout: 60                    # Connection and command execution timeout in seconds (Optional, default: 60)
```

> [!NOTE]
> For backwards compatibility, the legacy `ssh` config key is also parsed, but `remote-server` is the preferred key name.

---

## Elevation (Sudo)

When the AI assistant needs to execute a command with elevated privileges (root), it passes `use_sudo=true` to the tool. Shello CLI automatically wraps the command:

* **If `sudo_password` is configured**:
  Pipes the password securely into `sudo` using a non-interactive shell command wrapper:
  ```bash
  printf '%s\n' '<sudo_password>' | sudo -p "" -S sh -c '<command>'
  ```
* **If `sudo_password` is NOT configured**:
  Assumes passwordless sudo, running:
  ```bash
  sudo -n sh -c '<command>'
  ```
  *(If passwordless sudo is not allowed on the server, the command will fail gracefully with a permission error).*

---

## Security & Command Trust

Just like local execution, all remote commands are evaluated by the **Trust Manager**:
- **Allowlist / Denylist**: Commands are checked against your configured trust lists.
- **Approval Dialogs**: If a command is classified as destructive (e.g. `rm -rf`, `format`, etc.), Shello CLI will prompt you with an interactive confirmation dialog showing the exact command and remote path context (`[remote] ~`) before it runs on the server.
