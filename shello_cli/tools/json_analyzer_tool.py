"""
JSON analyzer tool for Shello CLI.

This module provides the JsonAnalyzerTool class for analyzing JSON structures
and generating jq paths with data types.
"""

import json
from typing import List, Dict, Any
from shello_cli.types import ToolResult


class JsonAnalyzerTool:
    """JSON structure analyzer tool.
    
    This tool analyzes JSON data and generates jq paths with data types,
    helping users understand JSON structure for jq queries.
    """
    
    def analyze(self, json_input: str) -> ToolResult:
        """Analyze JSON structure and return jq paths with data types.
        
        Args:
            json_input: JSON string to analyze
        
        Returns:
            ToolResult with jq paths and data types
        """
        try:
            data = json.loads(json_input)
            paths = self._extract_paths(data)
            
            # Sort paths for consistent output
            paths.sort()
            
            # Format output
            output_lines = ["jq path | data type", "=" * 50] + paths
            output = "\n".join(output_lines)
            
            return ToolResult(
                success=True,
                output=output,
                error=None
            )
        
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Invalid JSON format: {str(e)}"
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=f"Error analyzing JSON: {str(e)}"
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
