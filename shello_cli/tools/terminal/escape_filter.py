"""Filter terminal query sequences from captured output."""

import re

# DSR (Device Status Report) - cursor position query
_DSR_PATTERN = re.compile(rb"\x1b\[6n")

# OSC (Operating System Command) queries
_OSC_QUERY_PATTERN = re.compile(
    rb"\x1b\]"  # OSC introducer
    rb"\d+"  # Parameter number (10, 11, 4, 12, etc.)
    rb"(?:;[^;\x07\x1b]*)?"  # Optional sub-parameter (e.g., palette index)
    rb";\?"  # Query marker - the key indicator this is a query
    rb"(?:\x07|\x1b\\)"  # BEL or ST terminator
)

# DA (Device Attributes) primary query
_DA_PATTERN = re.compile(rb"\x1b\[0?c")

# DA2 (Secondary Device Attributes) query
_DA2_PATTERN = re.compile(rb"\x1b\[>0?c")

# DECRQSS (Request Selection or Setting) - various terminal state queries
_DECRQSS_PATTERN = re.compile(
    rb"\x1bP\$q"  # DCS introducer + DECRQSS
    rb"[^\x1b]*"  # Setting identifier
    rb"\x1b\\"  # ST terminator
)

_INCOMPLETE_ESC_PATTERN = re.compile(
    rb"(?:"
    rb"\x1b$|"  # ESC at end (might be start of any sequence)
    rb"\x1b\[[0-9;>]*$|"  # CSI without command char
    rb"\x1b\][^\x07]*$|"  # OSC without BEL terminator (ST needs \x1b\)
    rb"\x1bP(?:[^\x1b]|\x1b(?!\\))*$"  # DCS without complete ST terminator
    rb")"
)


def _filter_complete_queries(output_bytes: bytes) -> bytes:
    """Filter complete terminal query sequences from output bytes."""
    output_bytes = _DSR_PATTERN.sub(b"", output_bytes)
    output_bytes = _OSC_QUERY_PATTERN.sub(b"", output_bytes)
    output_bytes = _DA_PATTERN.sub(b"", output_bytes)
    output_bytes = _DA2_PATTERN.sub(b"", output_bytes)
    output_bytes = _DECRQSS_PATTERN.sub(b"", output_bytes)
    return output_bytes


class TerminalQueryFilter:
    """Stateful filter for terminal query sequences."""

    def __init__(self) -> None:
        self._pending: bytes = b""

    def reset(self) -> None:
        """Reset filter state between commands."""
        self._pending = b""

    def filter(self, output: str) -> str:
        """Filter terminal query sequences from captured terminal output."""
        output_bytes = output.encode("utf-8", errors="surrogateescape")

        if self._pending:
            output_bytes = self._pending + output_bytes
            self._pending = b""

        match = _INCOMPLETE_ESC_PATTERN.search(output_bytes)
        if match:
            self._pending = output_bytes[match.start() :]
            output_bytes = output_bytes[: match.start()]

        output_bytes = _filter_complete_queries(output_bytes)

        return output_bytes.decode("utf-8", errors="surrogateescape")

    def flush(self) -> str:
        """Flush any pending bytes that weren't part of a query."""
        if not self._pending:
            return ""
        pending = self._pending
        self._pending = b""
        filtered = _filter_complete_queries(pending)
        return filtered.decode("utf-8", errors="surrogateescape")


def filter_terminal_queries(output: str) -> str:
    """Filter terminal query sequences from captured terminal output (stateless)."""
    temp_filter = TerminalQueryFilter()
    result = temp_filter.filter(output)
    result += temp_filter.flush()
    return result
