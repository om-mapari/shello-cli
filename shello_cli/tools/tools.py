"""
Tool definitions for Shello CLI.

This module defines all available tools in OpenAI function calling format,
providing a registry of tools that the AI agent can invoke.
"""

from typing import List
from shello_cli.types import ShelloTool
from shello_cli.constants import GET_CACHED_OUTPUT_DESCRIPTION


# Registry of all available tools in OpenAI function calling format
SHELLO_TOOLS: List[ShelloTool] = [
    ShelloTool(
        type="function",
        function={
            "name": "bash",
            "description": (
                "Execute a shell command in the current working directory.\n\n"
                "USE FOR:\n"
                "- Running shell commands (ls, dir, grep, find, etc.)\n"
                "- File operations (cat, type, cp, mv, rm)\n"
                "- Directory navigation (cd)\n"
                "- System operations and utilities\n"
                "- AWS CLI, Docker, Git, and other CLI tools\n"
                "- Piping and filtering with jq, grep, awk\n\n"
                "RULES:\n"
                "- Use shell-appropriate commands for the detected OS/shell\n"
                "- For large outputs, use filtering flags (--max-items, | head, Select-Object -First)\n"
                "- cd command updates working directory for subsequent commands\n"
                "- Output is shown directly to user - don't repeat it in your response"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    ),
    ShelloTool(
        type="function",
        function={
            "name": "analyze_json",
            "description": (
                "Execute a command and analyze its JSON output structure.\n\n"
                "USE FOR:\n"
                "- Understanding JSON structure from AWS CLI, Docker, curl, etc.\n"
                "- Discovering jq paths before filtering large JSON outputs\n"
                "- Preventing terminal flooding from large JSON responses\n\n"
                "HOW IT WORKS:\n"
                "1. Pass the COMMAND (not JSON) - tool executes it internally\n"
                "2. Returns ONLY jq paths with data types (user never sees raw JSON)\n"
                "3. Use discovered paths to construct filtered bash command with jq\n\n"
                "EXAMPLE WORKFLOW:\n"
                "1. analyze_json(command='aws lambda list-functions --output json')\n"
                "   → Returns: .Functions[].FunctionName | string\n"
                "2. bash(command=\"aws lambda list-functions --output json | jq '.Functions[].FunctionName'\")\n"
                "   → Returns clean, filtered output\n\n"
                "WHEN TO USE:\n"
                "- You don't know the JSON structure of a command's output\n"
                "- You expect large JSON that would flood the terminal\n"
                "- You need to find the right jq path for filtering"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command that produces JSON output (e.g., 'aws s3api list-buckets', 'docker inspect container_id')"
                    }
                },
                "required": ["command"]
            }
        }
    ),
    ShelloTool(
        type="function",
        function={
            "name": "get_cached_output",
            "description": GET_CACHED_OUTPUT_DESCRIPTION,
            "parameters": {
                "type": "object",
                "properties": {
                    "cache_id": {
                        "type": "string",
                        "description": "Cache ID from truncation summary (e.g., 'cmd_001')"
                    },
                    "lines": {
                        "type": "string",
                        "description": "Line selection: '+N' (first N), '-N' (last N), '+N,-M' (first+last), 'N-M' (range)"
                    }
                },
                "required": ["cache_id"]
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


def get_tool_descriptions() -> str:
    """Generate a formatted string describing all available tools.
    
    Returns:
        str: A formatted string with tool names and descriptions for the system prompt.
    """
    descriptions = []
    for tool in SHELLO_TOOLS:
        name = tool.function["name"]
        desc = tool.function["description"]
        # Get first line as summary for the system prompt
        summary = desc.split('\n')[0]
        descriptions.append(f"- {name}: {summary}")
    
    return "\n".join(descriptions)
