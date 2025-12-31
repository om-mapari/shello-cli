"""System information utilities for Shello CLI"""
import os
import platform
import subprocess


def get_shell_info():
    """Determine the best shell to use based on system and available tools"""
    os_name = platform.system()
    
    if os_name == "Windows":
        # Method 1: Check if bash is directly available in PATH (most reliable)
        try:
            result = subprocess.run(
                ["bash", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return {
                    "os_name": os_name,
                    "shell": "bash",
                    "cwd": os.getcwd().replace("\\", "/"),
                    "shell_executable": "bash"  # Use 'bash' directly since it's in PATH
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Method 2: Check common Git Bash installation paths
        git_bash_paths = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Git\bin\bash.exe")
        ]
        
        for git_bash_path in git_bash_paths:
            if os.path.exists(git_bash_path):
                return {
                    "os_name": os_name,
                    "shell": "bash",
                    "shell_executable": git_bash_path,
                    "cwd": os.getcwd().replace("\\", "/")
                }
        
        # Method 3: Try to find bash.exe using where command
        try:
            result = subprocess.run(
                ["where", "bash"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                bash_path = result.stdout.strip().split('\n')[0]  # Get first result
                return {
                    "os_name": os_name,
                    "shell": "bash",
                    "shell_executable": bash_path,
                    "cwd": os.getcwd().replace("\\", "/")
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Fallback to cmd.exe if Git Bash not found
        return {
            "os_name": os_name,
            "shell": "cmd",
            "shell_executable": "cmd.exe",
            "cwd": os.getcwd().replace("\\", "/")
        }
    else:
        # Unix-like systems
        return {
            "os_name": os_name,
            "shell": os.environ.get("SHELL", "bash"),
            "shell_executable": os.environ.get("SHELL", "bash"),
            "cwd": os.getcwd().replace("\\", "/")
        }
