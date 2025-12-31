"""System information utilities for Shello CLI"""
import os
import platform
import subprocess


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
            return {
                "os_name": os_name,
                "shell": "powershell",
                "shell_executable": os.environ.get('COMSPEC', 'cmd.exe'),
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
