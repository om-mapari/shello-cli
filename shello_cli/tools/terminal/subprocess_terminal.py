"""PTY-based terminal backend implementation (replaces pipe-based subprocess)."""

import os
import platform
import re
import shutil
import signal
import subprocess
import threading
import time
import logging
from collections import deque
from typing import Optional

if platform.system() == "Windows":
    # Placeholder on Windows to prevent import errors at module loading time
    # (since we won't instantiate this backend on Windows anyway)
    fcntl = None
    pty = None
    select = None
else:
    import fcntl
    import pty
    import select

from shello_cli.tools.terminal.constants import (
    CMD_OUTPUT_PS1_BEGIN,
    CMD_OUTPUT_PS1_END,
    HISTORY_LIMIT,
)
from shello_cli.tools.terminal.metadata import CmdOutputMetadata
from shello_cli.tools.terminal.interface import (
    TerminalInterface,
    parse_ctrl_key,
)

logger = logging.getLogger(__name__)

ENTER = b"\n"

# Map normalized special key names to ANSI escape bytes for PTY.
_SUBPROCESS_SPECIALS: dict[str, bytes] = {
    "ENTER": ENTER,
    "TAB": b"\t",
    "BS": b"\x7f",  # Backspace (DEL)
    "ESC": b"\x1b",
    "UP": b"\x1b[A",
    "DOWN": b"\x1b[B",
    "RIGHT": b"\x1b[C",
    "LEFT": b"\x1b[D",
    "HOME": b"\x1b[H",
    "END": b"\x1b[F",
    "PGUP": b"\x1b[5~",
    "PGDN": b"\x1b[6~",
    "C-L": b"\x0c",  # Ctrl+L
    "C-D": b"\x04",  # Ctrl+D (EOF)
    "C-C": b"\x03",  # Ctrl+C (SIGINT)
}


def _normalize_eols(raw: bytes) -> bytes:
    # CRLF/LF/CR -> CR, so each logical line is terminated with \r for the TTY
    raw = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return ENTER.join(raw.split(b"\n"))


def sanitized_env() -> dict[str, str]:
    """Return a copy of os.environ with restored PyInstaller pathing."""
    env = dict(os.environ)
    for key in ["LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "PATH"]:
        orig_key = f"{key}_ORIG"
        if orig_key in env:
            env[key] = env[orig_key]
    return env


class SubprocessTerminal(TerminalInterface):
    """PTY-backed terminal backend."""

    PS1: str
    process: Optional[subprocess.Popen]
    _pty_master_fd: Optional[int]
    output_buffer: deque[str]
    output_lock: threading.Lock
    reader_thread: Optional[threading.Thread]
    _current_command_running: bool

    def __init__(
        self,
        work_dir: str,
        username: Optional[str] = None,
        shell_path: Optional[str] = None,
    ):
        super().__init__(work_dir, username)
        self.PS1 = CmdOutputMetadata.to_ps1_prompt()
        self.process = None
        self._pty_master_fd = None
        self.output_buffer = deque(maxlen=HISTORY_LIMIT + 50)
        self.output_lock = threading.Lock()
        self.reader_thread = None
        self._current_command_running = False
        self.shell_path = shell_path

    def initialize(self) -> None:
        """Initialize the PTY terminal session."""
        if platform.system() == "Windows":
            raise RuntimeError("SubprocessTerminal is not supported on Windows")

        if self._initialized:
            return

        resolved_shell_path: Optional[str]
        if self.shell_path:
            resolved_shell_path = self.shell_path
        else:
            resolved_shell_path = shutil.which("bash")
            if resolved_shell_path is None:
                raise RuntimeError(
                    "Could not find bash in PATH. "
                    "Please provide an explicit shell_path parameter."
                )

        if not os.path.isfile(resolved_shell_path):
            raise RuntimeError(f"Shell binary not found at: {resolved_shell_path}")
        if not os.access(resolved_shell_path, os.X_OK):
            raise RuntimeError(f"Shell binary is not executable: {resolved_shell_path}")

        self.shell_path = resolved_shell_path
        logger.info(f"Using shell: {resolved_shell_path}")

        env = sanitized_env()
        env["PS1"] = self.PS1
        env["PS2"] = ""
        env["TERM"] = "xterm-256color"

        bash_cmd = [resolved_shell_path, "-i"]
        master_fd, slave_fd = pty.openpty()

        logger.debug("Initializing PTY terminal with: %s", " ".join(bash_cmd))
        try:
            self.process = subprocess.Popen(
                bash_cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=self.work_dir,
                env=env,
                text=False,
                bufsize=0,
                preexec_fn=os.setsid,
                close_fds=True,
            )
        finally:
            try:
                os.close(slave_fd)
            except Exception:
                pass

        self._pty_master_fd = master_fd
        flags = fcntl.fcntl(self._pty_master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self._pty_master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        self.reader_thread = threading.Thread(
            target=self._read_output_continuously_pty, daemon=True
        )
        self.reader_thread.start()
        self._initialized = True

        init_cmd = (
            f'set +H; export PROMPT_COMMAND=\'export PS1="{self.PS1}"\'; export PS2=""'
        ).encode("utf-8", "ignore")

        self._write_pty(init_cmd + ENTER)
        time.sleep(1.0)

        self.clear_screen()
        logger.debug("PTY terminal initialized with work dir: %s", self.work_dir)

    def close(self) -> None:
        """Clean up the PTY terminal."""
        if self._closed:
            return

        try:
            if self.process:
                try:
                    self._write_pty(b"exit\n")
                except Exception:
                    pass
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                        self.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
        except Exception as e:
            logger.error(f"Error closing PTY terminal: {e}", exc_info=True)
        finally:
            try:
                if self._pty_master_fd is not None:
                    os.close(self._pty_master_fd)
            except Exception:
                pass
            self._pty_master_fd = None

            if self.reader_thread and self.reader_thread.is_alive():
                self.reader_thread.join(timeout=1)

            self.process = None
            self._closed = True

    def _write_pty(self, data: bytes) -> None:
        if not self._initialized and self._pty_master_fd is None:
            raise RuntimeError("PTY master FD not ready")
        if self._pty_master_fd is None:
            raise RuntimeError("PTY terminal is not initialized")
        try:
            logger.debug(f"Wrote to subprocess PTY: {data!r}")
            os.write(self._pty_master_fd, data)
        except Exception as e:
            logger.error(f"Failed to write to PTY: {e}", exc_info=True)
            raise

    def _read_output_continuously_pty(self) -> None:
        fd = self._pty_master_fd
        if fd is None:
            return

        try:
            while True:
                if self.process and self.process.poll() is not None:
                    break

                r, _, _ = select.select([fd], [], [], 0.1)
                if not r:
                    continue

                try:
                    chunk = os.read(fd, 4096)
                    if not chunk:
                        break
                    text = chunk.decode("utf-8", errors="replace")
                    with self.output_lock:
                        self._add_text_to_buffer(text)
                except OSError:
                    continue
                except Exception as e:
                    logger.debug(f"Error reading PTY output: {e}")
                    break
        except Exception as e:
            logger.error(f"PTY reader thread error: {e}", exc_info=True)

    def _add_text_to_buffer(self, text: str) -> None:
        if self.output_buffer and not self.output_buffer[-1].endswith("\n"):
            combined_text = self.output_buffer[-1] + text
            self.output_buffer.pop()
        else:
            combined_text = text

        lines = combined_text.split("\n")
        for line in lines[:-1]:
            self.output_buffer.append(line + "\n")
        if lines[-1]:
            self.output_buffer.append(lines[-1])

    _MULTILINE_THRESHOLD: int = 20
    _SELECT_WRITE_TIMEOUT: float = 0.05
    _LINE_PACING_DELAY: float = 0.002

    def send_keys(self, text: str, enter: bool = True, is_input: bool = False) -> None:
        """Send keystrokes to the PTY."""
        if not self._initialized:
            raise RuntimeError("PTY terminal is not initialized")

        upper = text.upper().strip()
        payload: Optional[bytes] = None

        if upper in _SUBPROCESS_SPECIALS:
            payload = _SUBPROCESS_SPECIALS[upper]
            append_eol = False
        elif (ctrl := parse_ctrl_key(text)) is not None:
            key_char = ctrl[-1].upper()
            payload = bytes([ord(key_char) & 0x1F])
            append_eol = False
        else:
            input_lines = text.split("\n")
            if len(input_lines) > self._MULTILINE_THRESHOLD:
                self._send_multiline_with_flow_control(input_lines, enter)
                return

            raw = text.encode("utf-8", "ignore")
            payload = _normalize_eols(raw) if enter else raw
            append_eol = enter and not payload.endswith(ENTER)

        if append_eol:
            payload += ENTER

        self._write_pty(payload)
        self._current_command_running = self._current_command_running or (
            append_eol or payload.endswith(ENTER)
        )

    def _wait_for_pty_writable(self, timeout: float) -> bool:
        if self._pty_master_fd is None:
            return False
        _, writable, _ = select.select([], [self._pty_master_fd], [], timeout)
        return len(writable) > 0

    def _send_multiline_with_flow_control(self, lines: list[str], enter: bool) -> None:
        for i, line in enumerate(lines):
            is_last = i == len(lines) - 1
            payload = line.encode("utf-8", "ignore")

            if not is_last or enter:
                payload += ENTER

            self._wait_for_pty_writable(self._SELECT_WRITE_TIMEOUT)
            self._write_pty(payload)

            if not is_last:
                time.sleep(self._LINE_PACING_DELAY)

        self._current_command_running = True

    def read_screen(self) -> str:
        if not self._initialized:
            raise RuntimeError("PTY terminal is not initialized")

        time.sleep(0.01)
        with self.output_lock:
            content = "".join(self.output_buffer)
            lines = content.split("\n")
            content = "\n".join(lines).replace("\r", "")
            logger.debug(f"Read from subprocess PTY: {content!r}")
            return content

    def clear_screen(self) -> None:
        if not self._initialized:
            return

        need_prompt_nudge = False
        with self.output_lock:
            if not self.output_buffer:
                need_prompt_nudge = True
            else:
                data = "".join(self.output_buffer)
                start_idx = data.rfind(CMD_OUTPUT_PS1_BEGIN)
                end_idx = data.rfind(CMD_OUTPUT_PS1_END)
                if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
                    tail = data[start_idx:]
                    self.output_buffer.clear()
                    self.output_buffer.append(tail)
                else:
                    self.output_buffer.clear()
                    need_prompt_nudge = True

        if need_prompt_nudge:
            try:
                self._write_pty(ENTER)
            except Exception:
                pass

    def interrupt(self) -> bool:
        if not self._initialized or not self.process:
            return False

        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self._current_command_running = False
            return True
        except Exception as e:
            logger.error(f"Failed to interrupt subprocess: {e}", exc_info=True)
            return False

    def is_running(self) -> bool:
        if not self._initialized or not self.process:
            return False
        if self.process.poll() is not None:
            return False

        try:
            content = self.read_screen()
            return not content.rstrip().endswith(CMD_OUTPUT_PS1_END.rstrip())
        except Exception:
            return self._current_command_running
