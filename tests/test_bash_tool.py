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

    def test_command_timeout_returns_partial_output(self):
        """Test that a command timeout returns partial output and exit_code = -1."""
        bash_tool = BashTool()
        cmd = 'python -c "import time, sys; print(\'hello_partial\'); sys.stdout.flush(); time.sleep(5)"'
        result = bash_tool.execute(cmd, timeout=1)
        
        try:
            assert result.success is False
            assert result.output is not None
            assert "hello_partial" in result.output
            assert result.error is not None
            assert "timed out" in result.error.lower() or "no output" in result.error.lower()
            assert result.data is not None
            assert result.data.get("exit_code") == -1
            assert bash_tool._active_process is not None
            assert bash_tool._active_process.poll() is None
        finally:
            bash_tool._reset_active_process()

    def test_polling_continuation(self):
        """Test that calling with command="" continues polling/waiting on the active process."""
        bash_tool = BashTool()
        cmd = 'python -c "import time, sys; print(\'first\'); sys.stdout.flush(); time.sleep(2); print(\'second\'); sys.stdout.flush()"'
        result1 = bash_tool.execute(cmd, timeout=1)
        
        try:
            assert result1.success is False
            assert "first" in result1.output
            assert "second" not in (result1.output or "")
            assert bash_tool._active_process is not None
            
            # Poll continuation
            result2 = bash_tool.execute("", timeout=3)
            assert result2.success is True
            assert "second" in result2.output
            assert result2.data.get("exit_code") == 0
            assert bash_tool._active_process is None
        finally:
            bash_tool._reset_active_process()

    def test_interactive_stdin_write(self):
        """Test that writing interactive stdin via is_input=true works."""
        bash_tool = BashTool()
        cmd = 'python -c "import sys; print(\'Enter name:\'); sys.stdout.flush(); val = sys.stdin.readline().strip(); print(\'Hello \' + val); sys.stdout.flush()"'
        result1 = bash_tool.execute(cmd, timeout=1)
        
        try:
            assert result1.success is False
            assert "Enter name:" in result1.output
            assert bash_tool._active_process is not None
            
            # Send input
            result2 = bash_tool.execute("Alice", is_input=True, timeout=2)
            assert result2.success is True
            assert "Hello Alice" in result2.output
            assert bash_tool._active_process is None
        finally:
            bash_tool._reset_active_process()

    def test_abort_execution_cc(self):
        """Test aborting execution using command="C-c" and is_input=true."""
        bash_tool = BashTool()
        cmd = 'python -c "import time, sys; print(\'started\'); sys.stdout.flush(); time.sleep(10)"'
        result1 = bash_tool.execute(cmd, timeout=1)
        
        try:
            assert result1.success is False
            assert "started" in result1.output
            assert bash_tool._active_process is not None
            
            # Abort via C-c
            result2 = bash_tool.execute("C-c", is_input=True)
            assert result2.success is False
            assert "interrupted" in result2.error.lower() or "sigint" in result2.error.lower()
            assert result2.error_type == "process_control"
            assert result2.data.get("exit_code") == -1
            assert bash_tool._active_process is None
        finally:
            bash_tool._reset_active_process()

    def test_send_eof_cd(self):
        """Test sending EOF via command="C-d" and is_input=true."""
        bash_tool = BashTool()
        cmd = 'python -c "import sys; lines = sys.stdin.read(); print(\'EOF received: \' + lines.strip()); sys.stdout.flush()"'
        result1 = bash_tool.execute(cmd, timeout=1)
        
        try:
            assert result1.success is False
            assert bash_tool._active_process is not None
            
            # Write some input (will still block because read() waits for EOF)
            result2 = bash_tool.execute("hello", is_input=True, timeout=1)
            assert result2.success is False
            assert bash_tool._active_process is not None
            
            # Send EOF C-d
            result3 = bash_tool.execute("C-d", is_input=True, timeout=2)
            assert result3.success is True
            assert "EOF received: hello" in result3.output
            assert bash_tool._active_process is None
        finally:
            bash_tool._reset_active_process()

    def test_reset_active_session(self):
        """Test resetting active sessions via reset=true."""
        bash_tool = BashTool()
        cmd = 'python -c "import time, sys; print(\'running\'); sys.stdout.flush(); time.sleep(10)"'
        result1 = bash_tool.execute(cmd, timeout=1)
        
        try:
            assert result1.success is False
            assert bash_tool._active_process is not None
            
            # Reset session
            result2 = bash_tool.execute("", reset=True)
            assert result2.success is True
            assert "reset" in result2.output.lower()
            assert bash_tool._active_process is None
        finally:
            bash_tool._reset_active_process()
