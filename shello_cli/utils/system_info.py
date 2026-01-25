"""System information utilities for Shello CLI"""
import os
import platform
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


def get_shell_info():
    """Determine the actual shell the user is running in"""
    os_name = platform.system()
    
    if os_name == "Windows":
        # Check for bash first (Git Bash, WSL, etc.)
        # Git Bash sets BASH or BASH_VERSION environment variables
        if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
            return {
                "os_name": os_name,
                "shell": "bash",
                "shell_executable": os.environ.get('BASH', 'bash'),
                "cwd": os.getcwd()
            }
        
        # Check SHELL environment variable for bash (Git Bash on Windows)
        # Also check SHLVL which is set by bash but not cmd/PowerShell
        shell_env = os.environ.get('SHELL', '')
        if 'bash' in shell_env.lower() or os.environ.get('SHLVL'):
            return {
                "os_name": os_name,
                "shell": "bash",
                "shell_executable": shell_env if shell_env else 'bash',
                "cwd": os.getcwd()
            }
        
        # Check if running in PowerShell
        # Look for PowerShell-specific variables that aren't inherited
        # PSExecutionPolicyPreference is only set when actually running in PowerShell
        if os.environ.get('PSExecutionPolicyPreference') or \
           (os.environ.get('PSModulePath') and not os.environ.get('PROMPT', '').startswith('$P$G')):
            # Detect PowerShell version (Core vs Windows PowerShell)
            pwsh_path = os.environ.get('PWSH_PATH')  # PowerShell Core sets this
            if pwsh_path:
                shell_exe = pwsh_path
            elif os.path.exists(r'C:\Program Files\PowerShell\7\pwsh.exe'):
                shell_exe = r'C:\Program Files\PowerShell\7\pwsh.exe'
            else:
                # Windows PowerShell (5.1)
                shell_exe = 'powershell.exe'
            
            return {
                "os_name": os_name,
                "shell": "powershell",
                "shell_executable": shell_exe,
                "cwd": os.getcwd()
            }
        
        # Default to cmd
        return {
            "os_name": os_name,
            "shell": "cmd",
            "shell_executable": os.environ.get('COMSPEC', 'cmd.exe'),
            "cwd": os.getcwd()
        }
    else:
        # Unix-like systems
        return {
            "os_name": os_name,
            "shell": os.path.basename(os.environ.get("SHELL", "bash")),
            "shell_executable": os.environ.get("SHELL", "bash"),
            "cwd": os.getcwd()
        }


def detect_shell() -> Tuple[str, str]:
    """Detect the current shell being used.
    
    Returns:
        Tuple of (shell_name, shell_executable)
    """
    info = get_shell_info()
    return info['shell'], info['shell_executable']


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
