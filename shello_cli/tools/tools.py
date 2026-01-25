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
                "- ALWAYS filter at source (jq, Select-Object, findstr, head)\n"
                "- For AWS/cloud: pipe to jq for specific fields\n"
                "- For file searches: ALWAYS limit results (Select-Object -First 50, head -50)\n\n"
                "Examples:\n"
                "  ✅ aws lambda list-functions | jq '.Functions[].FunctionName'\n"
                "  ✅ Get-ChildItem -Recurse -Filter '*.py' | Select-Object -First 50\n"
                "  ✅ find . -name '*.py' -type f | head -50\n"
                "  ❌ aws lambda list-functions (dumps everything)\n"
                "  ❌ Get-ChildItem -Recurse (no limit)\n\n"
                "RULES:\n"
                "- Use shell-appropriate commands for detected OS/shell\n"
                "- Output shown to user - DON'T repeat in response\n"
                "- NEVER use echo to communicate\n"
                "- For git: use --no-pager (git --no-pager diff)\n\n"
                "SAFETY:\n"
                "- is_safe=true: read-only (dir, cat, grep)) - runs immediately\n"
                "- is_safe=false: destructive (rm, dd) - needs user approval\n"
                "- Command visible to user before execution"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute. Use appropriate syntax for user's OS/shell."
                    },
                    "is_safe": {
                        "type": "boolean",
                        "description": "true=read-only (ls, cat), false=destructive (rm, dd). When unsure, use false."
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
                "Analyze JSON structure of a command's output WITHOUT showing raw JSON.\n\n"
                "USE WHEN: You don't know the JSON structure and need jq paths.\n\n"
                "HOW: Pass COMMAND (not JSON) → Returns jq paths with types.\n\n"
                "EXAMPLE:\n"
                "  analyze_json(command='aws lambda list-functions')\n"
                "  → .Functions[].FunctionName | string\n"
                "  Then: run_shell_command(\"aws lambda list-functions | jq '.Functions[].FunctionName'\")"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command that produces JSON (e.g., 'aws s3api list-buckets', 'docker inspect id')"
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
                "Retrieve cached output from previous command.\n\n"
                "USE WHEN: Output was truncated, user asks about earlier command, need specific lines.\n\n"
                "LINE SELECTION:\n"
                "  '-100'    → Last 100 lines (best for logs)\n"
                "  '+50'     → First 50 lines\n"
                "  '+20,-80' → First 20 + last 80\n"
                "  '10-50'   → Lines 10-50\n"
                "  (omit)    → Full output (50K limit)\n\n"
                "EXAMPLE: get_cached_output(cache_id='cmd_001', lines='-100')"
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
                        "description": "Line selection: '+N' first, '-N' last, '+N,-M' both, 'N-M' range. Omit for full."
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
