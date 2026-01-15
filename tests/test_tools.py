"""
Property-based tests for tool definitions.

Feature: openai-cli-refactor
Tests tool definition validity and structure.
"""

import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.tools.tools import SHELLO_TOOLS, get_all_tools
from shello_cli.types import ShelloTool


class TestToolDefinitionProperties:
    """Property-based tests for tool definitions."""
    
    def test_property_1_tool_definition_validity(self):
        """
        Feature: openai-cli-refactor, Property 1: Tool Definition Validity
        
        For any tool in the tool registry, the tool SHALL have a valid structure containing 
        type="function", and a function object with name (non-empty string), description 
        (non-empty string), and parameters (object with type="object").
        
        Validates: Requirements 2.1, 2.3
        """
        tools = get_all_tools()
        
        # Verify we have at least one tool
        assert len(tools) > 0, "Tool registry must contain at least one tool"
        
        # Check each tool in the registry
        for tool in tools:
            # Verify tool is a ShelloTool instance
            assert isinstance(tool, ShelloTool), f"Tool must be a ShelloTool instance, got {type(tool)}"
            
            # Verify type field is "function"
            assert tool.type == "function", f"Tool type must be 'function', got '{tool.type}'"
            
            # Verify function object exists
            assert tool.function is not None, "Tool must have a function object"
            assert isinstance(tool.function, dict), "Tool function must be a dictionary"
            
            # Verify function has required fields
            assert "name" in tool.function, "Tool function must have a 'name' field"
            assert "description" in tool.function, "Tool function must have a 'description' field"
            assert "parameters" in tool.function, "Tool function must have a 'parameters' field"
            
            # Verify name is a non-empty string
            assert isinstance(tool.function["name"], str), "Tool name must be a string"
            assert len(tool.function["name"]) > 0, "Tool name must be non-empty"
            
            # Verify description is a non-empty string
            assert isinstance(tool.function["description"], str), "Tool description must be a string"
            assert len(tool.function["description"]) > 0, "Tool description must be non-empty"
            
            # Verify parameters is an object with type="object"
            assert isinstance(tool.function["parameters"], dict), "Tool parameters must be a dictionary"
            assert "type" in tool.function["parameters"], "Tool parameters must have a 'type' field"
            assert tool.function["parameters"]["type"] == "object", \
                f"Tool parameters type must be 'object', got '{tool.function['parameters']['type']}'"


class TestToolDefinitionUnitTests:
    """Unit tests for specific tool definition scenarios."""
    
    def test_shello_tools_is_list(self):
        """Test that SHELLO_TOOLS is a list."""
        assert isinstance(SHELLO_TOOLS, list), "SHELLO_TOOLS must be a list"
    
    def test_get_all_tools_returns_list(self):
        """Test that get_all_tools returns a list."""
        tools = get_all_tools()
        assert isinstance(tools, list), "get_all_tools must return a list"
    
    def test_run_shell_command_tool_exists(self):
        """Test that run_shell_command tool is defined in the registry."""
        tools = get_all_tools()
        shell_tools = [t for t in tools if t.function.get("name") == "run_shell_command"]
        
        assert len(shell_tools) > 0, "run_shell_command tool must be defined in the registry"
    
    def test_run_shell_command_tool_has_command_parameter(self):
        """Test that run_shell_command tool has a command parameter."""
        tools = get_all_tools()
        shell_tool = next((t for t in tools if t.function.get("name") == "run_shell_command"), None)
        
        assert shell_tool is not None, "run_shell_command tool must exist"
        assert "properties" in shell_tool.function["parameters"], \
            "run_shell_command tool parameters must have properties"
        assert "command" in shell_tool.function["parameters"]["properties"], \
            "run_shell_command tool must have a command parameter"
    
    def test_run_shell_command_tool_command_is_required(self):
        """Test that run_shell_command tool command parameter is required."""
        tools = get_all_tools()
        shell_tool = next((t for t in tools if t.function.get("name") == "run_shell_command"), None)
        
        assert shell_tool is not None, "run_shell_command tool must exist"
        assert "required" in shell_tool.function["parameters"], \
            "run_shell_command tool parameters must have required field"
        assert "command" in shell_tool.function["parameters"]["required"], \
            "run_shell_command tool command parameter must be required"
    
    def test_tool_function_schema_structure(self):
        """Test that tool function follows OpenAI schema structure."""
        tools = get_all_tools()
        
        for tool in tools:
            # Check parameters schema structure
            params = tool.function["parameters"]
            assert "type" in params, "Parameters must have type field"
            assert "properties" in params, "Parameters must have properties field"
            assert isinstance(params["properties"], dict), "Properties must be a dictionary"
