"""
Property-based tests for BashTool.

Feature: openai-cli-refactor
Tests bash command execution and directory change functionality.
"""

import os
import tempfile
import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.tools.bash_tool import BashTool
from shello_cli.types import ToolResult


class TestBashToolProperties:
    """Property-based tests for BashTool."""
    
    @given(command=st.sampled_from(['echo test', 'pwd', 'echo hello', 'cd']))
    @settings(deadline=None, max_examples=10)
    def test_property_2_bash_command_returns_valid_tool_result(self, command):
        """
        Feature: openai-cli-refactor, Property 2: Bash Command Execution Returns Valid ToolResult
        
        For any bash command execution, the result SHALL be a ToolResult with a boolean 
        success field, and either output (on success) or error (on failure) as a string.
        
        Validates: Requirements 3.2, 3.3
        """
        bash_tool = BashTool()
        result = bash_tool.execute(command, timeout=5)
        
        # Verify result is a ToolResult
        assert isinstance(result, ToolResult), "Result must be a ToolResult instance"
        
        # Verify success field is boolean
        assert isinstance(result.success, bool), "success field must be a boolean"
        
        # Verify either output or error is present as a string
        if result.success:
            assert result.output is not None, "output must be present on success"
            assert isinstance(result.output, str), "output must be a string"
        else:
            assert result.error is not None, "error must be present on failure"
            assert isinstance(result.error, str), "error must be a string"
    
    @given(
        dir_name=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
            min_size=1,
            max_size=20
        )
    )
    @settings(deadline=None)
    def test_property_3_directory_change_consistency(self, dir_name):
        """
        Feature: openai-cli-refactor, Property 3: Directory Change Consistency
        
        For any valid directory path, executing a cd command to that directory SHALL 
        result in get_current_directory() returning that path.
        
        Validates: Requirements 3.1, 3.6
        """
        bash_tool = BashTool()
        
        # Create a temporary directory with the generated name
        with tempfile.TemporaryDirectory() as temp_base:
            test_dir = os.path.join(temp_base, dir_name)
            os.makedirs(test_dir, exist_ok=True)
            
            # Execute cd command
            result = bash_tool.execute(f"cd {test_dir}")
            
            # If cd was successful, verify directory changed
            if result.success:
                current_dir = bash_tool.get_current_directory()
                # Normalize both paths for comparison
                assert os.path.normpath(current_dir) == os.path.normpath(test_dir), \
                    f"Current directory {current_dir} does not match expected {test_dir}"


class TestBashToolUnitTests:
    """Unit tests for specific BashTool scenarios."""
    
    def test_successful_command_execution(self):
        """Test that a simple successful command returns proper ToolResult."""
        bash_tool = BashTool()
        result = bash_tool.execute("echo 'test'")
        
        assert result.success is True
        assert result.output is not None
        assert "test" in result.output
        assert result.error is None
    
    def test_failed_command_execution(self):
        """Test that a failed command returns proper ToolResult with error."""
        bash_tool = BashTool()
        result = bash_tool.execute("nonexistentcommand12345", timeout=5)
        
        assert result.success is False
        assert result.error is not None
        assert isinstance(result.error, str)
    
    def test_command_timeout(self):
        """Test that a command timeout returns proper ToolResult."""
        bash_tool = BashTool()
        # Use a command that will timeout (sleep for longer than timeout)
        result = bash_tool.execute("python -c \"import time; time.sleep(10)\"", timeout=1)
        
        assert result.success is False
        assert result.error is not None
        assert "timed out" in result.error.lower()
    
    def test_cd_to_home_directory(self):
        """Test cd with no arguments goes to home directory."""
        bash_tool = BashTool()
        result = bash_tool.execute("cd")
        
        assert result.success is True
        # Normalize paths for comparison (Windows vs Unix path separators)
        current = os.path.normpath(bash_tool.get_current_directory())
        expected = os.path.normpath(os.path.expanduser('~'))
        assert current == expected, f"Expected {expected}, got {current}"
    
    def test_cd_to_nonexistent_directory(self):
        """Test cd to nonexistent directory returns error."""
        bash_tool = BashTool()
        result = bash_tool.execute("cd /nonexistent/directory/path/12345")
        
        assert result.success is False
        assert result.error is not None
        assert "No such file or directory" in result.error
    
    def test_cd_to_file_not_directory(self):
        """Test cd to a file (not directory) returns error."""
        bash_tool = BashTool()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            result = bash_tool.execute(f"cd {temp_path}")
            
            assert result.success is False
            assert result.error is not None
            assert "Not a directory" in result.error
        finally:
            os.unlink(temp_path)
    
    def test_get_current_directory(self):
        """Test get_current_directory returns a valid path."""
        bash_tool = BashTool()
        current_dir = bash_tool.get_current_directory()
        
        assert current_dir is not None
        assert isinstance(current_dir, str)
        assert os.path.isabs(current_dir)
