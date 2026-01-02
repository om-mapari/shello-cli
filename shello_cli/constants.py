"""Application-wide constants and paths."""
from pathlib import Path

# Application paths
APP_DIR = Path.home() / ".shello_cli"

# Ensure directory exists
APP_DIR.mkdir(exist_ok=True)
