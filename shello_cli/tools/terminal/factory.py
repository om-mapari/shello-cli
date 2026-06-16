"""Factory for creating appropriate terminal sessions based on system capabilities."""

import platform
import subprocess
import logging
from typing import Literal, Optional

from shello_cli.tools.terminal.terminal_session import TerminalSession
from shello_cli.tools.terminal.interface import TerminalInterface

logger = logging.getLogger(__name__)


def _get_powershell_command(explicit_shell_path: Optional[str] = None) -> Optional[str]:
    """Return a usable PowerShell executable for the current platform."""
    candidates = [explicit_shell_path] if explicit_shell_path else []
    if platform.system() == "Windows":
        candidates.extend(["pwsh.exe", "pwsh", "powershell.exe", "powershell"])
    else:
        candidates.extend(["pwsh"])

    for candidate in candidates:
        if not candidate:
            continue
        try:
            result = subprocess.run(
                [candidate, "-Command", "Write-Host 'PowerShell Available'"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if result.returncode == 0:
                return candidate
        except (subprocess.TimeoutExpired, FileNotFoundError, PermissionError, OSError):
            continue
    return None


def create_terminal_session(
    work_dir: str,
    username: Optional[str] = None,
    no_change_timeout_seconds: Optional[int] = None,
    terminal_type: Optional[Literal["subprocess", "powershell"]] = None,
    shell_path: Optional[str] = None,
) -> TerminalSession:
    """Create an appropriate terminal session based on system capabilities.

    Args:
        work_dir: Working directory for the session
        username: Optional username for the session
        no_change_timeout_seconds: Timeout for no output change
        terminal_type: Force a specific session type ('subprocess' or 'powershell').
            If None, auto-detect based on OS.
        shell_path: Path to the shell binary.

    Returns:
        TerminalSession instance
    """
    if terminal_type == "powershell" or (terminal_type is None and platform.system() == "Windows"):
        from shello_cli.tools.terminal.windows_terminal import WindowsTerminal
        resolved_shell_path = _get_powershell_command(shell_path) or "powershell.exe"
        logger.info(f"Creating WindowsTerminal with shell: {resolved_shell_path}")
        terminal = WindowsTerminal(work_dir, username, shell_path=resolved_shell_path)
        return TerminalSession(terminal, no_change_timeout_seconds)
    else:
        from shello_cli.tools.terminal.subprocess_terminal import SubprocessTerminal
        logger.info("Creating SubprocessTerminal")
        terminal = SubprocessTerminal(work_dir, username, shell_path)
        return TerminalSession(terminal, no_change_timeout_seconds)
