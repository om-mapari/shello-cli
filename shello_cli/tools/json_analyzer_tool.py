"""
JSON analyzer tool for Shello CLI.

Analyzes JSON structure of a command output and returns jq paths with
data types - without flooding the terminal with raw JSON.

Security: when a bash_tool is provided (production), command execution
delegates to BashTool so all commands pass through TrustManager.
When no bash_tool is provided (tests / standalone use), falls back to
a direct subprocess call matching the original behaviour.
"""

import json
import subprocess
import os
import platform
from typing import Any, Optional, TYPE_CHECKING

from shello_cli.types import ToolResult, ShelloTool
from shello_cli.tools.base import ShelloToolBase

if TYPE_CHECKING:
    from shello_cli.tools.bash_tool import BashTool


def _detect_shell_type() -> str:
    if platform.system() != "Windows":
        return "bash"
    if os.environ.get("BASH") or os.environ.get("BASH_VERSION"):
        return "bash"
    if (os.environ.get("SHELL") and "bash" in os.environ.get("SHELL", "").lower()) \
            or os.environ.get("SHLVL"):
        return "bash"
    if os.environ.get("PSExecutionPolicyPreference") or \
            (os.environ.get("PSModulePath")
             and not os.environ.get("PROMPT", "").startswith("$P$G")):
        return "powershell"
    return "cmd"


class JsonAnalyzerTool(ShelloToolBase):
    """JSON structure analyzer tool."""

    tool_name = "analyze_json"

    _SCHEMA = ShelloTool(
        type="function",
        function={
            "name": "analyze_json",
            "description": (
                "Analyze JSON structure of a command output WITHOUT showing raw JSON.\n\n"
                "USE WHEN: You don't know the JSON structure and need jq paths.\n\n"
                "HOW: Pass COMMAND (not JSON) -> Returns jq paths with types.\n\n"
                "EXAMPLE:\n"
                "  analyze_json(command='aws lambda list-functions')\n"
                "  -> .Functions[].FunctionName | string\n"
                "  Then: run_shell_command(\"aws lambda list-functions | jq '.Functions[].FunctionName'\")"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command that produces JSON (e.g., 'aws s3api list-buckets')"
                    }
                },
                "required": ["command"]
            }
        }
    )

    def __init__(self, bash_tool: Optional["BashTool"] = None):
        """
        Args:
            bash_tool: Optional shared BashTool instance. When provided, all
                       command execution goes through TrustManager (production).
                       When None, uses direct subprocess (tests / standalone).
        """
        self._bash_tool = bash_tool
        self._shell_type = _detect_shell_type()

    @property
    def schema(self) -> ShelloTool:
        return self._SCHEMA

    def execute(self, command: str, **_) -> ToolResult:
        """Execute command and analyze its JSON output (ShelloToolBase interface)."""
        return self.analyze(command)

    def analyze(self, command: str, timeout: int = 60) -> ToolResult:
        """Execute command and analyze its JSON output.

        Args:
            command: Shell command expected to produce JSON output.
            timeout: Max execution time in seconds (only used in fallback path).
        """
        if self._bash_tool is not None:
            # Production path: goes through TrustManager
            result = self._bash_tool.execute(command, is_safe=True)
            if not result.success:
                return result
            raw = (result.output or "").strip()
        else:
            # Fallback path: direct subprocess (tests / standalone)
            raw, err = self._run_subprocess(command, timeout)
            if err is not None:
                return err
            if not raw:
                return ToolResult(success=False, output=None,
                                  error="Command produced no output")

        return self.analyze_json_string(raw)

    def analyze_json_string(self, json_string: str) -> ToolResult:
        """Analyze an already-captured JSON string and return jq paths.

        Used by output management when JSON output exceeds character limits.
        """
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            return ToolResult(success=False, output=None,
                              error=f"not valid JSON: {e}")

        paths = sorted(self._extract_paths(data))
        output = "\n".join(["jq path | data type", "=" * 50] + paths)
        return ToolResult(success=True, output=output, error=None)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_subprocess(self, command: str, timeout: int):
        """Run command directly via subprocess. Returns (output_str, None) or (None, ToolResult)."""
        try:
            if self._shell_type == "powershell":
                result = subprocess.run(
                    ["powershell.exe", "-Command", command],
                    capture_output=True, timeout=timeout,
                    encoding="utf-8", errors="replace"
                )
            else:
                result = subprocess.run(
                    command, shell=True,
                    capture_output=True, timeout=timeout,
                    encoding="utf-8", errors="replace"
                )
            if result.returncode != 0:
                return None, ToolResult(
                    success=False, output=None,
                    error=f"Command failed: {result.stderr or 'Unknown error'}"
                )
            return (result.stdout.strip() if result.stdout else ""), None
        except subprocess.TimeoutExpired:
            return None, ToolResult(success=False, output=None,
                                    error=f"Command timed out after {timeout} seconds")
        except Exception as e:
            return None, ToolResult(success=False, output=None,
                                    error=f"Error executing command: {e}")

    def _extract_paths(self, obj: Any, jq_path: str = "") -> list[str]:
        paths: list[str] = []
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_path = f"{jq_path}.{key}" if jq_path else f".{key}"
                if isinstance(value, dict):
                    paths.extend(self._extract_paths(value, new_path))
                elif isinstance(value, list):
                    paths.append(f"{new_path}[] | array[{len(value)}]")
                    if value:
                        if not isinstance(value[0], (dict, list)):
                            paths.append(f"{new_path}[] | array_item_{self._type_name(value[0])}")
                        elif isinstance(value[0], dict):
                            paths.extend(self._extract_paths(value[0], f"{new_path}[]"))
                else:
                    paths.append(f"{new_path} | {self._type_name(value)}")
        elif isinstance(obj, list) and obj:
            paths.append(f".[] | array[{len(obj)}]")
            if isinstance(obj[0], dict):
                paths.extend(self._extract_paths(obj[0], ".[]"))
            else:
                paths.append(f".[] | {self._type_name(obj[0])}")
        return paths

    def _type_name(self, value: Any) -> str:
        if value is None:
            return "null"
        return {"str": "string", "int": "number", "float": "number",
                "bool": "boolean"}.get(type(value).__name__, type(value).__name__)
