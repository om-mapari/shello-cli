"""Unified terminal session using TerminalInterface backends."""

import re
import time
import logging
from enum import Enum
from typing import Optional

from shello_cli.tools.terminal.constants import (
    CMD_OUTPUT_PS1_END,
    MAX_CMD_OUTPUT_SIZE,
    NO_CHANGE_TIMEOUT_SECONDS,
    POLL_INTERVAL,
    TIMEOUT_MESSAGE_TEMPLATE,
)
from shello_cli.tools.terminal.interface import (
    TerminalAction,
    TerminalObservation,
    TerminalInterface,
    TerminalSessionBase,
)
from shello_cli.tools.terminal.metadata import CmdOutputMetadata
from shello_cli.tools.terminal.command import (
    escape_bash_special_chars,
    split_bash_commands,
)
from shello_cli.tools.terminal.escape_filter import TerminalQueryFilter

logger = logging.getLogger(__name__)


class TerminalCommandStatus(Enum):
    """Status of a terminal command execution."""

    CONTINUE = "continue"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    NO_CHANGE_TIMEOUT = "no_change_timeout"
    HARD_TIMEOUT = "hard_timeout"


def maybe_truncate(content: str, truncate_after: int) -> str:
    """Cap output length to prevent excessive log sizes."""
    if len(content) <= truncate_after:
        return content
    half = truncate_after // 2
    return (
        content[:half]
        + f"\n\n... [Output truncated to {truncate_after} characters] ...\n\n"
        + content[-half:]
    )


def _remove_command_prefix(command_output: str, command: str) -> str:
    return command_output.lstrip().removeprefix(command.lstrip()).lstrip()


def _remove_powershell_echo(command_output: str, command: str, is_input: bool = False, last_sent_command: Optional[str] = None) -> str:
    command_output = command_output.lstrip()
    command = command.strip()
    if command_output:
        first_line = command_output.splitlines()[0].strip()
        last_sent = last_sent_command.strip() if last_sent_command else None
        
        matched = False
        if not is_input:
            if (command and first_line.startswith(command)) or (last_sent and first_line.startswith(last_sent)):
                matched = True
        else:
            if (command and first_line == command) or (last_sent and first_line == last_sent):
                matched = True
                
        if matched:
            _, separator, rest = command_output.partition("\n")
            command_output = rest if separator else ""
            
    return re.sub(r"(?:\r?\n)?PS [^\r\n]*>\s*$", "", command_output).lstrip()


class TerminalSession(TerminalSessionBase):
    """Unified bash session that works with any TerminalInterface backend."""

    terminal: TerminalInterface
    prev_status: Optional[TerminalCommandStatus]
    prev_output: str

    def __init__(
        self,
        terminal: TerminalInterface,
        no_change_timeout_seconds: Optional[int] = None,
    ):
        super().__init__(
            terminal.work_dir,
            terminal.username,
            no_change_timeout_seconds,
        )
        self.terminal = terminal
        self.no_change_timeout_seconds = (
            no_change_timeout_seconds or NO_CHANGE_TIMEOUT_SECONDS
        )
        self.prev_status = None
        self.prev_output = ""
        self._query_filter = TerminalQueryFilter()

    def initialize(self) -> None:
        """Initialize the terminal backend."""
        self.terminal.initialize()
        self._initialized = True
        logger.debug(f"Unified session initialized with {type(self.terminal).__name__}")

    def close(self) -> None:
        """Clean up the terminal backend."""
        if self._closed:
            return
        self.terminal.close()
        self._closed = True

    def interrupt(self) -> bool:
        """Interrupt the currently running command (Ctrl+C)."""
        return self.terminal.interrupt()

    def is_running(self) -> bool:
        """Check if a command is currently running."""
        if not self._initialized:
            return False
        return self.prev_status in {
            TerminalCommandStatus.CONTINUE,
            TerminalCommandStatus.NO_CHANGE_TIMEOUT,
            TerminalCommandStatus.HARD_TIMEOUT,
        }

    def _is_special_key(self, command: str) -> bool:
        """Check if the command is a special key."""
        _command = command.strip()
        return _command.startswith("C-") and len(_command) == 3

    def _get_command_output(
        self,
        command: str,
        raw_command_output: str,
        metadata: CmdOutputMetadata,
        continue_prefix: str = "",
        is_final: bool = False,
        is_input: bool = False,
    ) -> str:
        """Get the command output with the previous command output removed."""
        if self.prev_output:
            command_output = raw_command_output.removeprefix(self.prev_output)
            metadata.prefix = continue_prefix
        else:
            command_output = raw_command_output
        self.prev_output = raw_command_output
        if self.terminal.is_powershell():
            command_output = _remove_powershell_echo(
                command_output,
                command,
                is_input=is_input,
                last_sent_command=getattr(self.terminal, "last_sent_command", None)
            )
        else:
            if not is_input:
                command_output = _remove_command_prefix(command_output, command)

        command_output = self._query_filter.filter(command_output)
        if is_final:
            command_output += self._query_filter.flush()

        return command_output.rstrip()

    def _handle_completed_command(
        self,
        command: str,
        terminal_content: str,
        ps1_matches: list[re.Match],
        is_input: bool = False,
    ) -> TerminalObservation:
        """Handle a completed command."""
        is_special_key = self._is_special_key(command)

        if len(ps1_matches) == 0:
            logger.warning(
                "No PS1 metadata found in terminal output. "
                "Command output may have overwritten the markers."
            )
            exit_code = -1
            if self.terminal.process is not None and self.terminal.process.poll() is not None:
                exit_code = self.terminal.process.poll()
            metadata = CmdOutputMetadata(exit_code=exit_code, working_dir=self._cwd)
            metadata.suffix = (
                "\n[The command completed but the exit code could not "
                "be determined. Terminal output may have corrupted the "
                "PS1 metadata markers.]"
            )
            command_output = self._get_command_output(
                command,
                terminal_content,
                metadata,
                is_final=True,
                is_input=is_input,
            )
            command_output = maybe_truncate(
                command_output, truncate_after=MAX_CMD_OUTPUT_SIZE
            )
            self.prev_status = TerminalCommandStatus.COMPLETED
            self.prev_output = ""
            self._query_filter.reset()
            self._ready_for_next_command()
            return TerminalObservation.from_text(
                command=command,
                text=command_output,
                metadata=metadata,
                exit_code=metadata.exit_code,
            )

        metadata = CmdOutputMetadata.from_ps1_match(ps1_matches[-1])
        get_content_before_last_match = bool(len(ps1_matches) == 1)
        if self.terminal.process is not None and self.terminal.process.poll() is not None:
            get_content_before_last_match = False
            metadata.exit_code = self.terminal.process.poll()

        if metadata.working_dir != self._cwd and metadata.working_dir:
            self._cwd = metadata.working_dir

        raw_command_output = self._combine_outputs_between_matches(
            terminal_content,
            ps1_matches,
            get_content_before_last_match=get_content_before_last_match,
        )

        if get_content_before_last_match:
            num_lines = len(raw_command_output.splitlines())
            metadata.prefix = (
                f"[Previous command outputs are truncated. "
                f"Showing the last {num_lines} lines of the output below.]\n"
            )

        metadata.suffix = (
            f"\n[The command completed with exit code {metadata.exit_code}.]"
            if not is_special_key
            else (
                f"\n[The command completed with exit code {metadata.exit_code}. "
                f"CTRL+{command[-1].upper()} was sent.]"
            )
        )
        command_output = self._get_command_output(
            command,
            raw_command_output,
            metadata,
            is_final=True,
            is_input=is_input,
        )
        command_output = maybe_truncate(
            command_output, truncate_after=MAX_CMD_OUTPUT_SIZE
        )

        self.prev_status = TerminalCommandStatus.COMPLETED
        self.prev_output = ""
        self._query_filter.reset()
        self._ready_for_next_command()
        return TerminalObservation.from_text(
            command=command,
            text=command_output,
            metadata=metadata,
            exit_code=metadata.exit_code,
        )

    def _handle_nochange_timeout_command(
        self,
        command: str,
        terminal_content: str,
        ps1_matches: list[re.Match],
        is_input: bool = False,
    ) -> TerminalObservation:
        """Handle a command that timed out due to no output change."""
        self.prev_status = TerminalCommandStatus.NO_CHANGE_TIMEOUT
        raw_command_output = self._combine_outputs_between_matches(
            terminal_content, ps1_matches
        )
        metadata = CmdOutputMetadata()
        metadata.suffix = (
            f"\n[The command has no new output after "
            f"{self.no_change_timeout_seconds} seconds. {TIMEOUT_MESSAGE_TEMPLATE}]"
        )
        command_output = self._get_command_output(
            command,
            raw_command_output,
            metadata,
            continue_prefix="[Below is the output of the previous command.]\n",
            is_input=is_input,
        )
        command_output = maybe_truncate(
            command_output, truncate_after=MAX_CMD_OUTPUT_SIZE
        )
        return TerminalObservation.from_text(
            command=command,
            text=command_output,
            metadata=metadata,
            exit_code=metadata.exit_code,
        )

    def _handle_hard_timeout_command(
        self,
        command: str,
        terminal_content: str,
        ps1_matches: list[re.Match],
        timeout: float,
        is_input: bool = False,
    ) -> TerminalObservation:
        """Handle a command that timed out due to hard timeout."""
        self.prev_status = TerminalCommandStatus.HARD_TIMEOUT
        raw_command_output = self._combine_outputs_between_matches(
            terminal_content, ps1_matches
        )
        metadata = CmdOutputMetadata()
        metadata.suffix = (
            f"\n[The command timed out after {timeout} seconds. "
            f"{TIMEOUT_MESSAGE_TEMPLATE}]"
        )
        command_output = self._get_command_output(
            command,
            raw_command_output,
            metadata,
            continue_prefix="[Below is the output of the previous command.]\n",
            is_input=is_input,
        )
        command_output = maybe_truncate(
            command_output, truncate_after=MAX_CMD_OUTPUT_SIZE
        )
        return TerminalObservation.from_text(
            command=command,
            exit_code=metadata.exit_code,
            text=command_output,
            metadata=metadata,
        )

    def _ready_for_next_command(self) -> None:
        """Reset the content buffer for a new command."""
        self.terminal.clear_screen()

    def _combine_outputs_between_matches(
        self,
        terminal_content: str,
        ps1_matches: list[re.Match],
        get_content_before_last_match: bool = False,
    ) -> str:
        """Combine all outputs between PS1 matches."""
        if len(ps1_matches) == 1:
            if get_content_before_last_match:
                return terminal_content[: ps1_matches[0].start()]
            else:
                return terminal_content[ps1_matches[0].end() + 1 :]
        elif len(ps1_matches) == 0:
            return terminal_content
        combined_output = ""
        for i in range(len(ps1_matches) - 1):
            output_segment = terminal_content[
                ps1_matches[i].end() + 1 : ps1_matches[i + 1].start()
            ]
            combined_output += output_segment + "\n"
        combined_output += terminal_content[ps1_matches[-1].end() + 1 :]
        return combined_output

    def execute(self, action: TerminalAction) -> TerminalObservation:
        """Execute a command using the terminal backend."""
        if not self._initialized:
            raise RuntimeError("Unified session is not initialized")

        command = action.command.strip()
        is_input = action.is_input

        if self.prev_status not in {
            TerminalCommandStatus.CONTINUE,
            TerminalCommandStatus.NO_CHANGE_TIMEOUT,
            TerminalCommandStatus.HARD_TIMEOUT,
        }:
            if command == "":
                return TerminalObservation.from_text(
                    text="No previous running command to retrieve logs from.",
                    command=command,
                    is_error=True,
                )
            if is_input:
                return TerminalObservation.from_text(
                    text="No previous running command to interact with.",
                    command=command,
                    is_error=True,
                )

        splited_commands = split_bash_commands(command)
        if len(splited_commands) > 1:
            commands_list = "\n".join(
                f"({i + 1}) {cmd}" for i, cmd in enumerate(splited_commands)
            )
            return TerminalObservation.from_text(
                text=(
                    "Cannot execute multiple commands at once.\n"
                    "Please run each command separately OR chain them into a single "
                    f"command via && or ;\nProvided commands:\n{commands_list}"
                ),
                command=command,
                is_error=True,
            )

        initial_terminal_output = self.terminal.read_screen()
        initial_ps1_matches = CmdOutputMetadata.matches_ps1_metadata(
            initial_terminal_output
        )
        initial_ps1_count = len(initial_ps1_matches)

        start_time = time.time()
        last_change_time = start_time
        last_terminal_output = initial_terminal_output

        # Check if previous command is still running and a new one is sent
        if (
            self.prev_status
            in {
                TerminalCommandStatus.HARD_TIMEOUT,
                TerminalCommandStatus.NO_CHANGE_TIMEOUT,
            }
            and not last_terminal_output.rstrip().endswith(CMD_OUTPUT_PS1_END.rstrip())
            and not is_input
            and command != ""
        ):
            _ps1_matches = CmdOutputMetadata.matches_ps1_metadata(last_terminal_output)
            current_matches_for_output = (
                _ps1_matches if _ps1_matches else initial_ps1_matches
            )
            raw_command_output = self._combine_outputs_between_matches(
                last_terminal_output, current_matches_for_output
            )
            metadata = CmdOutputMetadata()
            metadata.suffix = (
                f'\n[Your command "{command}" is NOT executed. The previous command '
                f"is still running - You CANNOT send new commands until the previous "
                f"command is completed. By setting `is_input` to `true`, you can "
                f"interact with the current process: {TIMEOUT_MESSAGE_TEMPLATE}]"
            )
            command_output = self._get_command_output(
                command,
                raw_command_output,
                metadata,
                continue_prefix="[Below is the output of the previous command.]\n",
            )
            command_output = maybe_truncate(
                command_output, truncate_after=MAX_CMD_OUTPUT_SIZE
            )
            return TerminalObservation.from_text(
                command=command,
                text=command_output,
                metadata=metadata,
                exit_code=metadata.exit_code,
                is_error=True,
            )

        sent_command = command != ""
        if command != "":
            is_special_key = self._is_special_key(command)
            if is_input:
                if command == "C-d":
                    # Stdin was closed, skip writing keys
                    pass
                else:
                    self.terminal.send_keys(
                        command,
                        enter=not is_special_key,
                        is_input=True,
                    )
            else:
                if not self.terminal.is_powershell():
                    command = escape_bash_special_chars(command)
                self.terminal.send_keys(
                    command,
                    enter=not is_special_key,
                )

        while True:
            process_exited = False
            if self.terminal.process is not None and self.terminal.process.poll() is not None:
                time.sleep(0.05)
                process_exited = True

            cur_terminal_output = self.terminal.read_screen()
            ps1_matches = CmdOutputMetadata.matches_ps1_metadata(cur_terminal_output)
            current_ps1_count = len(ps1_matches)
            output_changed_since_command = (
                cur_terminal_output != initial_terminal_output
            )

            if cur_terminal_output != last_terminal_output:
                last_terminal_output = cur_terminal_output
                last_change_time = time.time()

            # Command execution completed checks
            if process_exited or (not sent_command or output_changed_since_command) and (
                current_ps1_count > initial_ps1_count
                or cur_terminal_output.rstrip().endswith(CMD_OUTPUT_PS1_END.rstrip())
            ):
                return self._handle_completed_command(
                    command,
                    terminal_content=cur_terminal_output,
                    ps1_matches=ps1_matches,
                    is_input=is_input,
                )

            # Timeout checks
            time_since_last_change = time.time() - last_change_time
            is_blocking = action.timeout is not None
            if (
                not is_blocking
                and self.no_change_timeout_seconds is not None
                and time_since_last_change >= self.no_change_timeout_seconds
            ):
                return self._handle_nochange_timeout_command(
                    command,
                    terminal_content=cur_terminal_output,
                    ps1_matches=ps1_matches,
                    is_input=is_input,
                )

            if action.timeout is not None:
                time_since_start = time.time() - start_time
                if time_since_start >= action.timeout:
                    return self._handle_hard_timeout_command(
                        command,
                        terminal_content=cur_terminal_output,
                        ps1_matches=ps1_matches,
                        timeout=action.timeout,
                        is_input=is_input,
                    )

            time.sleep(POLL_INTERVAL)
