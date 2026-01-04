"""
Property-based tests for DirectExecutor.

Feature: direct-command-execution
Tests direct command execution and directory state management.
"""

import pytest
import os
import tempfile
from hypothesis import given, strategies as st, settings, assume
from shello_cli.commands.direct_executor import DirectExecutor, ExecutionResult
from shello_cli.tools.bash_tool import BashTool
from shello_cli.commands.command_detector import CommandDetector


class TestDirectExecutorProperties:
    """Property-based tests for DirectExecutor."""
    
    @given(
        command=st.sampled_from(['pwd', 'echo', 'ls', 'dir'])
    )
    @settings(max_examples=100, deadline=None)
    def test_property_3_command_execution_produces_output(self, command):
        """
        Feature: direct-command-execution, Property 3: Command Execution Produces Output
        
        For any valid direct command, executing it through DirectExecutor SHALL return 
        an ExecutionResult with either success=True and non-empty output, OR 
        success=False and non-empty error.
        
        Validates: Requirements 2.1, 2.3
        """
        bash_tool = BashTool()
        executor = DirectExecutor(bash_tool)
        
        # Execute the command
        result = executor.execute(command)
        
        # Verify that we get either success with output OR failure with error
        if result.success:
            assert result.output, \
                f"Successful execution of '{command}' should produce non-empty output"
            assert result.error is None, \
                f"Successful execution should not have error message"
        else:
            assert result.error, \
                f"Failed execution of '{command}' should produce non-empty error"
        
        # Verify result is an ExecutionResult
        assert isinstance(result, ExecutionResult), \
            f"Result should be an ExecutionResult instance"
    
    @given(
        # Generate a sequence of cd commands
        cd_sequence=st.lists(
            st.sampled_from(['.', '..', tempfile.gettempdir()]),
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_4_directory_state_consistency(self, cd_sequence):
        """
        Feature: direct-command-execution, Property 4: Directory State Consistency
        
        For any sequence of cd commands executed through DirectExecutor, the current 
        directory state SHALL be consistent with the expected path resolution, and 
        this state SHALL be accessible to both direct execution and AI execution contexts.
        
        Validates: Requirements 2.4, 2.5
        """
        executor = DirectExecutor()
        
        # Track the starting directory
        start_dir = executor.get_current_directory()
        
        # Execute the sequence of cd commands
        for target in cd_sequence:
            # Track directory before this cd
            before_dir = executor.get_current_directory()
            
            result = executor.execute('cd', target)
            
            # If cd succeeded, verify directory state
            if result.success:
                after_dir = executor.get_current_directory()
                
                # Resolve what the target directory should be
                if target == '.':
                    expected_dir = before_dir
                elif target == '..':
                    expected_dir = os.path.dirname(before_dir)
                else:
                    # Absolute path
                    expected_dir = os.path.normpath(target)
                
                # Check if directory actually changed
                actually_changed = (before_dir != after_dir)
                
                # Verify directory_changed flag matches reality
                assert result.directory_changed == actually_changed, \
                    f"directory_changed should be {actually_changed} when cd from '{before_dir}' to '{target}'"
                
                if result.directory_changed:
                    assert result.new_directory is not None, \
                        f"directory_changed=True should provide new_directory"
                    
                    # Verify the new directory is what we expect
                    assert after_dir == result.new_directory, \
                        f"get_current_directory() should match new_directory from result"
                    
                    # Verify the directory actually exists
                    assert os.path.exists(after_dir), \
                        f"Current directory '{after_dir}' should exist"
                    
                    assert os.path.isdir(after_dir), \
                        f"Current directory '{after_dir}' should be a directory"
        
        # Clean up: return to start directory
        executor._current_directory = start_dir


class TestDirectExecutorUnitTests:
    """Unit tests for specific DirectExecutor scenarios."""
    
    def test_simple_command_execution(self):
        """Test executing a simple command like 'pwd'."""
        executor = DirectExecutor()
        
        result = executor.execute('pwd')
        
        assert result.success
        assert result.output
        assert result.error is None
        assert not result.directory_changed
        assert result.new_directory is None
    
    def test_command_with_args(self):
        """Test executing a command with arguments."""
        executor = DirectExecutor()
        
        # Use 'ls' which is in the default allowlist
        result = executor.execute('ls', '.')
        
        assert result.success
        assert result.output
        assert result.error is None
        assert not result.directory_changed
    
    def test_cd_command_changes_directory(self):
        """Test that cd command changes directory."""
        executor = DirectExecutor()
        
        start_dir = executor.get_current_directory()
        
        # Change to temp directory
        temp_dir = tempfile.gettempdir()
        result = executor.execute('cd', temp_dir)
        
        assert result.success
        assert result.directory_changed
        assert result.new_directory == temp_dir
        assert executor.get_current_directory() == temp_dir
        
        # Clean up: return to start directory
        executor._current_directory = start_dir
    
    def test_cd_to_nonexistent_directory_fails(self):
        """Test that cd to nonexistent directory fails."""
        executor = DirectExecutor()
        
        start_dir = executor.get_current_directory()
        
        result = executor.execute('cd', '/nonexistent/directory/path/12345')
        
        assert not result.success
        assert result.error
        assert not result.directory_changed
        assert result.new_directory is None
        assert executor.get_current_directory() == start_dir
    
    def test_cd_dot_does_not_change_directory(self):
        """Test that 'cd .' does not change directory."""
        executor = DirectExecutor()
        
        start_dir = executor.get_current_directory()
        
        result = executor.execute('cd', '.')
        
        assert result.success
        # Directory didn't actually change
        assert not result.directory_changed
        assert executor.get_current_directory() == start_dir
    
    def test_cd_dotdot_changes_to_parent(self):
        """Test that 'cd ..' changes to parent directory."""
        executor = DirectExecutor()
        
        start_dir = executor.get_current_directory()
        parent_dir = os.path.dirname(start_dir)
        
        # Only test if we're not at root
        if parent_dir != start_dir:
            result = executor.execute('cd', '..')
            
            assert result.success
            assert result.directory_changed
            assert executor.get_current_directory() == parent_dir
            
            # Clean up: return to start directory
            executor._current_directory = start_dir
    
    def test_failed_command_returns_error(self):
        """Test that a failed command returns an error."""
        executor = DirectExecutor()
        
        # Try to execute a command that doesn't exist
        result = executor.execute('nonexistentcommand12345')
        
        assert not result.success
        assert result.error
        assert not result.directory_changed
    
    def test_get_current_directory(self):
        """Test that get_current_directory returns the current directory."""
        executor = DirectExecutor()
        
        current_dir = executor.get_current_directory()
        
        assert current_dir
        assert os.path.exists(current_dir)
        assert os.path.isdir(current_dir)
