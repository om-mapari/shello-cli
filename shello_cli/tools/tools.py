"""
Tool definitions for Shello CLI.

This module defines all available tools in OpenAI function calling format,
providing a registry of tools that the AI agent can invoke.
"""

from typing import List
from shello_cli.types import ShelloTool


# Registry of all available tools in OpenAI function calling format
SHELLO_TOOLS: List[ShelloTool] = [
    ShelloTool(
        type="function",
        function={
            "name": "bash",
            "description": "Execute a bash command in the current working directory. "
                         "Use this to run shell commands, navigate directories, read files, "
                         "and perform system operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute (e.g., 'ls -la', 'cd /tmp', 'cat file.txt')"
                    }
                },
                "required": ["command"]
            }
        }
    )
]


def get_all_tools() -> List[ShelloTool]:
    """Return all available tools for the AI agent.
    
    Returns:
        List[ShelloTool]: A list of all tool definitions in OpenAI function calling format.
    """
    return SHELLO_TOOLS
