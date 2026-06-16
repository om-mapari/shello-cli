"""Command splitting and escape utilities."""

def split_bash_commands(commands: str) -> list[str]:
    """Split a multi-statement bash input into top-level statements.
    
    A lightweight parser-free fallback splitting on un-escaped newlines.
    """
    if not commands.strip():
        return [""]
    
    lines = []
    current = []
    for line in commands.splitlines():
        stripped = line.strip()
        if stripped.endswith("\\"):
            current.append(line.rstrip()[:-1])
        else:
            current.append(line)
            lines.append(" ".join(current).strip())
            current = []
    if current:
        lines.append(" ".join(current).strip())
    return [l for l in lines if l]


def escape_bash_special_chars(command: str) -> str:
    """Double the escape on special characters.
    
    In Shello CLI, commands are sent directly to the shell, so we keep the
    command as-is to preserve original behavior.
    """
    return command
