"""
Improved tool definitions for Shello CLI.
"""

from typing import List
from shello_cli.types import ShelloTool


SHELLO_TOOLS: List[ShelloTool] = [
    ShelloTool(
        type="function",
        function={
            "name": "run_shell_command",
            "description": (
                "Execute a shell command on the user's machine.\n\n"
                "CRITICAL - Minimize Output:\n"
                "- Large outputs waste tokens and cost money\n"
                "- ALWAYS filter at source using pipes (jq, grep, head, Select-Object)\n"
                "- For AWS/cloud: NEVER dump raw JSON - pipe to jq for specific fields\n"
                "- For lists: limit items (--max-items, | head, Select-Object -First)\n\n"
                "Examples:\n"
                "  ✅ aws lambda list-functions | jq '.Functions[].FunctionName'\n"
                "  ✅ docker ps --format '{{.Names}}'\n"
                "  ❌ aws lambda list-functions (dumps everything)\n\n"
                "RULES:\n"
                "- Use shell-appropriate commands for detected OS/shell\n"
                "- Prefer absolute paths over cd commands\n"
                "- Output is shown to user - DON'T repeat it in response\n"
                "- NEVER use echo to communicate - respond directly\n\n"
                "SAFETY:\n"
                "- is_safe=true: read-only (ls, cat, git status) - executes immediately\n"
                "- is_safe=false: destructive (rm, dd) - requires user approval\n"
                "- Command is ALWAYS visible to user before execution\n"
                "- NEVER expose secrets in plain-text"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute. Must be appropriate for the user's OS and shell."
                    },
                    "is_safe": {
                        "type": "boolean",
                        "description": (
                            "true = read-only/safe operation (ls, cat, git status). "
                            "false = potentially destructive (rm, dd, format). "
                            "When unsure, use false."
                        )
                    }
                },
                "required": ["command", "is_safe"]
            }
        }
    ),
    ShelloTool(
        type="function",
        function={
            "name": "analyze_json",
            "description": (
                "Execute a command and analyze its JSON output structure WITHOUT showing raw JSON.\n\n"
                "WHEN TO USE:\n"
                "- You don't know the JSON structure of a command's output\n"
                "- You expect large JSON that would flood the terminal\n"
                "- You need to discover jq paths for filtering\n\n"
                "HOW IT WORKS:\n"
                "1. Pass the COMMAND (not JSON) - tool executes internally\n"
                "2. Returns ONLY jq paths with types (user never sees raw JSON)\n"
                "3. Use discovered paths to construct filtered shell command\n\n"
                "EXAMPLE:\n"
                "  analyze_json(command='aws lambda list-functions --output json')\n"
                "  → Returns: .Functions[].FunctionName | string\n"
                "  \n"
                "  Then use: run_shell_command(command=\"aws lambda list-functions | jq '.Functions[].FunctionName'\")\n\n"
                "IMPORTANT: Pass the COMMAND string, not JSON data."
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
            "description": (
                "Retrieve cached output from a previous command execution.\n\n"
                "WHEN TO USE:\n"
                "- Output was truncated and you need to see more\n"
                "- User asks about details from earlier command\n"
                "- You need specific lines from large output\n\n"
                "CACHE IDs:\n"
                "- Every command returns a cache_id (cmd_001, cmd_002, etc.)\n"
                "- Cache persists for entire conversation\n"
                "- Shown in truncation summary: 💾 Cache ID: cmd_001\n\n"
                "LINE SELECTION:\n"
                "- lines='-100'    → Last 100 lines (most common for logs)\n"
                "- lines='+50'     → First 50 lines\n"
                "- lines='+20,-80' → First 20 + last 80 lines\n"
                "- lines='10-50'   → Lines 10 through 50\n"
                "- (omit lines)    → Full output (50K char limit)\n\n"
                "EXAMPLE:\n"
                "  get_cached_output(cache_id='cmd_001', lines='-100')"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cache_id": {
                        "type": "string",
                        "description": "Cache ID from truncation summary (e.g., 'cmd_001')"
                    },
                    "lines": {
                        "type": "string",
                        "description": "Line selection: '+N' (first N), '-N' (last N), '+N,-M' (first+last), 'N-M' (range). Omit for full output."
                    }
                },
                "required": ["cache_id"]
            }
        }
    )
]


def get_all_tools() -> List[ShelloTool]:
    """Return all available tools for the AI agent."""
    return SHELLO_TOOLS


def get_tool_descriptions() -> str:
    """Generate formatted tool descriptions for system prompt."""
    descriptions = []
    for tool in SHELLO_TOOLS:
        name = tool.function["name"]
        desc = tool.function["description"]
        summary = desc.split('\n')[0]
        descriptions.append(f"- {name}: {summary}")
    return "\n".join(descriptions)
