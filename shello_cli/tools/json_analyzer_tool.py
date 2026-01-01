"""
JSON analyzer tool for Shello CLI.

This module provides the JsonAnalyzerTool class for executing commands that
produce JSON output and analyzing the structure to generate jq paths.
"""

import json
import subprocess
import os
import platform
from typing import List, Dict, Any
from shello_cli.types import ToolResult


class JsonAnalyzerTool:
    """JSON structure analyzer tool.
    
    This tool executes a command that produces JSON output, analyzes the
    JSON structure, and returns jq paths with data types. This helps the AI
    understand JSON structure without flooding the terminal with large outputs.
    """
    
    def __init__(self):
        """Initialize the JSON analyzer tool."""
        self._detect_shell()
    
    def _detect_shell(self):
        """Detect which shell to use for command execution."""
        os_name = platform.system()
        
        if os_name == 'Windows':
            # Check for bash first (Git Bash, WSL, etc.)
            if os.environ.get('BASH') or os.environ.get('BASH_VERSION'):
                self._shell_type = 'bash'
            elif (os.environ.get('SHELL') and 'bash' in os.environ.get('SHELL', '').lower()) or \
                 os.environ.get('SHLVL'):
                self._shell_type = 'bash'
            elif os.environ.get('PSExecutionPolicyPreference') or \
                 (os.environ.get('PSModulePath') and not os.environ.get('PROMPT', '').startswith('$P$G')):
                self._shell_type = 'powershell'
            else:
                self._shell_type = 'cmd'
        else:
            self._shell_type = 'bash'
    
    def analyze(self, command: str, timeout: int = 60) -> ToolResult:
        """Execute a command and analyze its JSON output structure.
        
        Args:
            command: The command to execute (should produce JSON output)
            timeout: Maximum execution time in seconds (default: 60)
        
        Returns:
            ToolResult with jq paths and data types
        """
        try:
            # Execute the command based on shell type
            if self._shell_type == 'powershell':
                result = subprocess.run(
                    ['powershell.exe', '-Command', command],
                    capture_output=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace'  # Replace invalid chars instead of failing
                )
            else:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    timeout=timeout,
                    encoding='utf-8',
                    errors='replace'  # Replace invalid chars instead of failing
                )
            
            # Check if command failed
            if result.returncode != 0:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command failed: {result.stderr or 'Unknown error'}"
                )
            
            output = result.stdout.strip() if result.stdout else ""
            
            # Check if output is empty
            if not output:
                return ToolResult(
                    success=False,
                    output=None,
                    error="Command produced no output"
                )
            
            # Try to parse as JSON
            try:
                data = json.loads(output)
            except json.JSONDecodeError as e:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Command output is not valid JSON: {str(e)}"
                )
            
            # Extract jq paths
            paths = self._extract_paths(data)
            
            # Sort paths for consistent output
            paths.sort()
            
            # Format output
            output_lines = ["jq path | data type", "=" * 50] + paths
            formatted_output = "\n".join(output_lines)
            
            return ToolResult(
                success=True,
                output=formatted_output,
                error=None
            )
        
        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                output=None,
                error=f"Command timed out after {timeout} seconds"
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error executing command: {str(e)}"
            )
    
    def _extract_paths(self, obj: Any, jq_path: str = "") -> List[str]:
        """Recursively extract jq paths from JSON object.
        
        Args:
            obj: JSON object to analyze
            jq_path: Current jq path being built
        
        Returns:
            List of jq paths with data types
        """
        paths = []
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_jq_path = f"{jq_path}.{key}" if jq_path else f".{key}"
                
                if isinstance(value, dict):
                    # Nested object - recurse deeper
                    paths.extend(self._extract_paths(value, new_jq_path))
                
                elif isinstance(value, list):
                    # Array field
                    paths.append(f"{new_jq_path}[] | array[{len(value)}]")
                    
                    # If array contains primitives, add array item type
                    if value and not isinstance(value[0], (dict, list)):
                        item_type = type(value[0]).__name__
                        if item_type == 'str':
                            paths.append(f"{new_jq_path}[] | array_item_str")
                        elif item_type == 'int':
                            paths.append(f"{new_jq_path}[] | array_item_int")
                        elif item_type == 'float':
                            paths.append(f"{new_jq_path}[] | array_item_float")
                        elif item_type == 'bool':
                            paths.append(f"{new_jq_path}[] | array_item_bool")
                        elif value[0] is None:
                            paths.append(f"{new_jq_path}[] | array_item_null")
                    
                    # If array contains objects, analyze their structure
                    if value and isinstance(value[0], dict):
                        paths.extend(self._extract_paths(value[0], f"{new_jq_path}[]"))
                
                else:
                    # Leaf node
                    type_name = self._get_type_name(value)
                    paths.append(f"{new_jq_path} | {type_name}")
        
        elif isinstance(obj, list) and obj:
            # Root is array - analyze first item
            paths.append(f".[] | array[{len(obj)}]")
            if isinstance(obj[0], dict):
                paths.extend(self._extract_paths(obj[0], ".[]"))
            else:
                type_name = self._get_type_name(obj[0])
                paths.append(f".[] | {type_name}")
        
        return paths
    
    def _get_type_name(self, value: Any) -> str:
        """Get human-readable type name for a value.
        
        Args:
            value: Value to get type for
        
        Returns:
            Type name string
        """
        if value is None:
            return "null"
        
        type_name = type(value).__name__
        
        # Map Python types to JSON types
        type_mapping = {
            'str': 'string',
            'int': 'number',
            'float': 'number',
            'bool': 'boolean',
            'NoneType': 'null'
        }
        
        return type_mapping.get(type_name, type_name)
