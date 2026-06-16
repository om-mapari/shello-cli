"""Abstract interface for terminal backends."""

import os
from abc import ABC, abstractmethod
from typing import Final, Optional
from pydantic import BaseModel, Field
from shello_cli.tools.terminal.constants import NO_CHANGE_TIMEOUT_SECONDS
from shello_cli.tools.terminal.metadata import CmdOutputMetadata

SUPPORTED_SPECIAL_KEYS: Final[frozenset[str]] = frozenset(
    {
        "ENTER",
        "TAB",
        "BS",
        "ESC",
        "UP",
        "DOWN",
        "LEFT",
        "RIGHT",
        "HOME",
        "END",
        "PGUP",
        "PGDN",
        "C-L",
        "C-D",
        "C-C",
    }
)


def parse_ctrl_key(text: str) -> Optional[str]:
    """Parse a Ctrl-<letter> token and return the normalized form ``C-x``."""
    upper = text.strip().upper()
    key: Optional[str] = None
    if upper.startswith("C-"):
        key = upper[2:]
    elif upper.startswith("CTRL-"):
        key = upper[5:]
    elif upper.startswith("CTRL+"):
        key = upper[5:]
    if key and len(key) == 1 and "A" <= key <= "Z":
        return f"C-{key.lower()}"
    return None


class TerminalAction(BaseModel):
    """Schema for terminal command execution."""
    command: str
    is_input: bool = False
    timeout: Optional[float] = None
    reset: bool = False


class TerminalObservation(BaseModel):
    """Result that represents a CLI output."""
    command: Optional[str] = None
    exit_code: Optional[int] = None
    timeout: bool = False
    text: str = ""
    metadata: CmdOutputMetadata = Field(default_factory=CmdOutputMetadata)

    @classmethod
    def from_text(
        cls,
        text: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        metadata: Optional[CmdOutputMetadata] = None,
        is_error: bool = False,
    ) -> "TerminalObservation":
        """Create a TerminalObservation helper."""
        meta = metadata or CmdOutputMetadata(exit_code=exit_code if exit_code is not None else -1)
        return cls(
            command=command,
            exit_code=exit_code,
            text=text,
            metadata=meta,
        )


class TerminalInterface(ABC):
    """Abstract interface for terminal backends."""

    work_dir: str
    username: Optional[str]
    _initialized: bool
    _closed: bool

    def __init__(
        self,
        work_dir: str,
        username: Optional[str] = None,
    ):
        self.work_dir = work_dir
        self.username = username
        self._initialized = False
        self._closed = False
        self.last_sent_command = ""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the terminal session."""

    @abstractmethod
    def close(self) -> None:
        """Clean up the terminal session."""

    @abstractmethod
    def send_keys(self, text: str, enter: bool = True, is_input: bool = False) -> None:
        """Send keys to the terminal."""

    @abstractmethod
    def read_screen(self) -> str:
        """Read current screen content."""

    @abstractmethod
    def clear_screen(self) -> None:
        """Clear screen."""

    @abstractmethod
    def interrupt(self) -> bool:
        """Send Ctrl+C."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if command is running."""

    @property
    def initialized(self) -> bool:
        return self._initialized

    @property
    def closed(self) -> bool:
        return self._closed

    def is_powershell(self) -> bool:
        return False


class TerminalSessionBase(ABC):
    """Abstract base class for terminal sessions."""

    work_dir: str
    username: Optional[str]
    no_change_timeout_seconds: int
    _initialized: bool
    _closed: bool
    _cwd: str

    def __init__(
        self,
        work_dir: str,
        username: Optional[str] = None,
        no_change_timeout_seconds: Optional[int] = None,
    ):
        self.work_dir = work_dir
        self.username = username
        self.no_change_timeout_seconds = (
            no_change_timeout_seconds or NO_CHANGE_TIMEOUT_SECONDS
        )
        self._initialized = False
        self._closed = False
        self._cwd = os.path.abspath(work_dir)

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the terminal session."""

    @abstractmethod
    def execute(self, action: TerminalAction) -> TerminalObservation:
        """Execute a command in the terminal session."""

    @abstractmethod
    def close(self) -> None:
        """Clean up the terminal session."""

    @abstractmethod
    def interrupt(self) -> bool:
        """Interrupt the currently running command."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if a command is currently running."""

    @property
    def cwd(self) -> str:
        return self._cwd

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
