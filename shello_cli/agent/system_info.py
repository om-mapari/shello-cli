"""
System information detection for the Shello Agent.

This module handles detection of OS, shell, and other system-level information.
"""

import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def detect_shell() -> Tuple[str, str]:
    """Detect the current shell being used.
    
    Returns:
        Tuple of (shell_name, shell_executable)
    """
    os_name = platform.system()
    
    if os_name == 'Windows':
        # Check for bash first (Git Bash, WSL, etc.)
        if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
            shell = os.environ.get('BASH', 'bash')
            shell_name = 'bash'
        # Check SHELL environment variable for bash (Git Bash on Windows)
        # Also check SHLVL which is set by bash but not cmd/PowerShell
        elif (os.environ.get('SHELL') and 'bash' in os.environ.get('SHELL', '').lower()) or \
             os.environ.get('SHLVL'):
            shell = os.environ.get('SHELL', 'bash')
            shell_name = 'bash'
        # Check if running in PowerShell (but not if bash is present)
        # PSExecutionPolicyPreference is only set when actually running in PowerShell
        elif os.environ.get('PSExecutionPolicyPreference') or \
             (os.environ.get('PSModulePath') and not os.environ.get('PROMPT', '').startswith('$P$G')):
            shell_name = 'powershell'
            shell = os.environ.get('COMSPEC', 'cmd.exe')
        else:
            shell = os.environ.get('COMSPEC', 'cmd.exe')
            shell_name = 'cmd'
    else:
        # On Unix-like systems, use SHELL environment variable
        shell = os.environ.get('SHELL', '/bin/bash')
        shell_name = os.path.basename(shell)
    
    return shell_name, shell


def load_custom_instructions() -> Optional[str]:
    """Load custom instructions from .shello/SHELLO.md if available.
    
    Checks in order:
    1. Current working directory: .shello/SHELLO.md
    2. User home directory: ~/.shello/SHELLO.md
    
    Returns:
        Optional[str]: Custom instructions content or None if not found
    """
    try:
        # Check current working directory
        cwd_path = Path.cwd() / ".shello" / "SHELLO.md"
        if cwd_path.exists():
            return cwd_path.read_text(encoding='utf-8').strip()
        
        # Check user home directory
        home_path = Path.home() / ".shello" / "SHELLO.md"
        if home_path.exists():
            return home_path.read_text(encoding='utf-8').strip()
        
        return None
    except Exception:
        # Silently fail if we can't load custom instructions
        return None


def get_current_datetime() -> str:
    """Get the current date and time as a formatted string.
    
    Returns:
        Current datetime in format "YYYY-MM-DD HH:MM:SS"
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
