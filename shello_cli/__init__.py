"""Shello CLI
AI Assistant with Command Execution"""

import logging
import sys

# Force UTF-8 encoding for stdout and stderr to prevent UnicodeEncodeError on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Set up default null handlers to prevent unconfigured logging from printing to stderr
logging.getLogger("shello").addHandler(logging.NullHandler())
logging.getLogger("shello_cli").addHandler(logging.NullHandler())

# Suppress verbose fastmcp logs (such as proxy warnings) at startup
try:
    import fastmcp
    logging.getLogger("fastmcp").setLevel(logging.WARNING)
except Exception:
    pass

__version__ = "0.8.1"

