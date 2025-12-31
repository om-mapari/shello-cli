"""Configuration management for Shello CLI"""
import os
import json
from pathlib import Path

# Application paths
APP_DIR = Path.home() / ".shello_cli"
HISTORY_FILE = APP_DIR / ".bai_shell_history"
CONFIG_FILE = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"

# Ensure directories exist
APP_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True, parents=True)


def load_config_as_env():
    """Load configuration and set as environment variables"""
    config = get_config()
    
    # Map config keys to environment variable names
    env_mapping = {
        "gitlab_url": "GITLAB_URL",
        "max_output_size": "MAX_OUTPUT_SIZE",
        "debug": "DEBUG"
    }
    
    # Set environment variables from config
    for config_key, env_key in env_mapping.items():
        if config_key in config:
            # Convert boolean to string for environment variables
            value = str(config[config_key]).lower() if isinstance(config[config_key], bool) else str(config[config_key])
            os.environ[env_key] = value


def get_config():
    """Get configuration, initializing if needed"""
    if not CONFIG_FILE.exists():
        return initialize_config()
    
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        # If config file is corrupted, recreate it
        return initialize_config()


def initialize_config():
    """Initialize configuration file if it doesn't exist"""
    # Default values (fallback if no env vars exist)
    default_config = {
        "gitlab_url": os.getenv("GITLAB_URL", "https://app.gitlab.server.com"),
        "max_output_size": int(os.getenv("MAX_OUTPUT_SIZE", "4000")),
        "debug": os.getenv("DEBUG", "false").lower() == "true",
        "theme": "dark",
        "completion_style": "multi-column"
    }
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(default_config, f, indent=2)
    
    return default_config


def update_config(key, value):
    """Update a specific configuration value"""
    config = get_config()
    config[key] = value
    
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    # Update environment variable immediately
    env_mapping = {
        "gitlab_url": "GITLAB_URL",
        "max_output_size": "MAX_OUTPUT_SIZE",
        "debug": "DEBUG"
    }
    
    if key in env_mapping:
        env_value = str(value).lower() if isinstance(value, bool) else str(value)
        os.environ[env_mapping[key]] = env_value
    
    return config


# Load config as environment variables when module is imported
load_config_as_env()

# Application settings (now read from environment variables set above)
GITLAB_URL = os.getenv("GITLAB_URL", "https://app.gitlab.server.com")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
MAX_OUTPUT_SIZE = int(os.getenv("MAX_OUTPUT_SIZE", "4000"))
