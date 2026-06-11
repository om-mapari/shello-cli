"""Shello CLI
AI Assistant with Command Execution"""

import logging

# Set up default null handlers to prevent unconfigured logging from printing to stderr
logging.getLogger("shello").addHandler(logging.NullHandler())
logging.getLogger("shello_cli").addHandler(logging.NullHandler())

__version__ = "0.8.0"

