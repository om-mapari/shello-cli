"""
Property-based tests for ContextManager.

Feature: direct-command-execution
Tests command history recording and AI context synchronization.
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime
from shello_cli.commands.context_manager import ContextManager, CommandRecord


class TestContextManagerProperties:
    """Property-based tests for ContextManager."""
    
    @given(
        commands=st.lists(
            st.tuples(
                st.text(
                    alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
                    min_size=1, 
                    max_size=50
                ).filter(lambda x: x.strip() and '\n' not in x),  # command (no newlines)
                st.text(min_size=0, max_size=200),  # output
                st.booleans(),  # success
                st.text(
                    alphabet=st.characters(blacklist_categories=('Cc', 'Cs')),
                    min_size=1, 
                    max_size=100
                ).filter(lambda x: x.strip() and '\n' not in x)  # directory (no newlines)
            ),
            min_size=1,
            max_size=15
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_8_command_history_recording(self, commands):
        """
        Feature: direct-command-execution, Property 8: Command History Recording
        
        For any direct command execution, the ContextManager SHALL record the command, 
        and the generated AI context string SHALL include all recorded commands in 
        chronological order.
        
        Validates: Requirements 5.1, 5.2, 5.3, 5.4
        """
        manager = ContextManager()
        
        # Record all commands
        for command, output, success, directory in commands:
            manager.record_command(command, output, success, directory)
        
        # Get AI context
        context = manager.get_context_for_ai()
        
        # Verify context is not empty when commands were recorded
        assert context, "Context should not be empty when commands are recorded"
        
        # Verify context contains header
        assert "Recent direct commands executed:" in context, \
            "Context should contain header"
        
        # Verify all commands appear in context (up to last 10)
        # ContextManager keeps only last 10 commands
        expected_commands = commands[-10:]
        
        for command, output, success, directory in expected_commands:
            # Command should appear in context
            assert command in context, \
                f"Command '{command}' should appear in context"
            
            # Directory should appear in context
            assert directory in context, \
                f"Directory '{directory}' should appear in context"
            
            # Success/failure indicator should appear
            status_indicator = "✓" if success else "✗"
            assert status_indicator in context, \
                f"Status indicator '{status_indicator}' should appear in context"
        
        # Verify chronological order by checking commands appear in sequence
        context_lines = context.split('\n')
        command_lines = [line for line in context_lines if line.strip() and not line.startswith("Recent")]
        
        # Extract commands from context lines
        context_commands = []
        for line in command_lines:
            if "$ " in line:
                # Extract command after the $ symbol
                cmd_part = line.split("$ ", 1)[1] if "$ " in line else ""
                context_commands.append(cmd_part)
        
        # Verify we have the expected number of commands in context
        assert len(context_commands) <= 10, \
            "Context should contain at most 10 commands"
        
        # Verify commands appear in chronological order
        expected_cmd_list = [cmd for cmd, _, _, _ in expected_commands]
        for i, expected_cmd in enumerate(expected_cmd_list):
            if i < len(context_commands):
                assert expected_cmd in context_commands[i], \
                    f"Command at position {i} should be '{expected_cmd}'"


class TestContextManagerUnitTests:
    """Unit tests for specific ContextManager scenarios."""
    
    def test_empty_context_when_no_commands(self):
        """Test that context is empty when no commands have been recorded."""
        manager = ContextManager()
        context = manager.get_context_for_ai()
        
        assert context == "", "Context should be empty when no commands recorded"
    
    def test_single_command_recording(self):
        """Test recording a single command."""
        manager = ContextManager()
        manager.record_command("ls -la", "file1.txt\nfile2.txt", True, "/home/user")
        
        context = manager.get_context_for_ai()
        
        assert "ls -la" in context
        assert "/home/user" in context
        assert "✓" in context
    
    def test_failed_command_recording(self):
        """Test recording a failed command."""
        manager = ContextManager()
        manager.record_command("rm nonexistent", "rm: cannot remove", False, "/home/user")
        
        context = manager.get_context_for_ai()
        
        assert "rm nonexistent" in context
        assert "✗" in context
    
    def test_clear_history(self):
        """Test clearing command history."""
        manager = ContextManager()
        manager.record_command("ls", "file.txt", True, "/home/user")
        manager.record_command("pwd", "/home/user", True, "/home/user")
        
        # Verify commands are recorded
        context_before = manager.get_context_for_ai()
        assert "ls" in context_before
        assert "pwd" in context_before
        
        # Clear history
        manager.clear_history()
        
        # Verify context is empty
        context_after = manager.get_context_for_ai()
        assert context_after == "", "Context should be empty after clearing history"
    
    def test_output_truncation(self):
        """Test that long output is truncated."""
        manager = ContextManager()
        long_output = "x" * 1000
        manager.record_command("cat large_file", long_output, True, "/home/user")
        
        # Access internal history to verify truncation
        assert len(manager._command_history) == 1
        record = manager._command_history[0]
        assert len(record.output) <= 500, "Output should be truncated to 500 chars"
    
    def test_history_limit(self):
        """Test that history is limited to 10 commands."""
        manager = ContextManager()
        
        # Record 15 commands with unique names that won't have substring issues
        for i in range(15):
            manager.record_command(f"testcmd{i:02d}", f"output{i}", True, f"/dir{i}")
        
        # Verify only last 10 are kept
        assert len(manager._command_history) == 10
        
        # Verify the last 10 commands are present (commands 05-14)
        context = manager.get_context_for_ai()
        for i in range(5, 15):
            assert f"testcmd{i:02d}" in context, f"Command testcmd{i:02d} should be in context"
        
        # Verify first 5 commands are not present (commands 00-04)
        for i in range(5):
            assert f"testcmd{i:02d}" not in context, f"Command testcmd{i:02d} should not be in context"
    
    def test_command_record_dataclass(self):
        """Test CommandRecord dataclass creation."""
        record = CommandRecord(
            command="ls",
            output="file.txt",
            success=True,
            timestamp=datetime.now(),
            directory="/home/user"
        )
        
        assert record.command == "ls"
        assert record.output == "file.txt"
        assert record.success is True
        assert isinstance(record.timestamp, datetime)
        assert record.directory == "/home/user"
    
    def test_context_does_not_include_output(self):
        """Test that context does not include output (feature removed)."""
        manager = ContextManager()
        manager.record_command("ls", "file1.txt\nfile2.txt\nfile3.txt", True, "/home/user")
        
        context = manager.get_context_for_ai()
        
        # Output should NOT be included in context
        assert "Output:" not in context, "Context should not include output line"
        assert "file1.txt" not in context, "Context should not include output content"
    
    def test_context_with_empty_output(self):
        """Test context generation with empty output."""
        manager = ContextManager()
        manager.record_command("clear", "", True, "/home/user")
        
        context = manager.get_context_for_ai()
        
        assert "clear" in context
        assert "✓" in context
        # Should not have "Output:" line for empty output
        lines = context.split('\n')
        output_lines = [line for line in lines if "Output:" in line]
        assert len(output_lines) == 0, "Should not have Output line for empty output"
    
    def test_multiple_commands_chronological_order(self):
        """Test that multiple commands appear in chronological order."""
        manager = ContextManager()
        
        manager.record_command("pwd", "/home/user", True, "/home/user")
        manager.record_command("ls", "file.txt", True, "/home/user")
        manager.record_command("cd /tmp", "", True, "/tmp")
        
        context = manager.get_context_for_ai()
        
        # Find positions of commands in context
        pwd_pos = context.find("pwd")
        ls_pos = context.find("ls")
        cd_pos = context.find("cd /tmp")
        
        assert pwd_pos < ls_pos < cd_pos, \
            "Commands should appear in chronological order"
