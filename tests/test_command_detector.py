"""
Property-based tests for CommandDetector.

Feature: direct-command-execution
Tests command detection and routing logic.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from shello_cli.commands.command_detector import CommandDetector, InputType, DetectionResult


class TestCommandDetectorProperties:
    """Property-based tests for CommandDetector."""
    
    @given(
        command=st.sampled_from(list(CommandDetector.DIRECT_COMMANDS)),
        args=st.one_of(
            st.none(),
            st.text(min_size=1, max_size=50).filter(lambda x: x.strip())
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_1_direct_command_detection(self, command, args):
        """
        Feature: direct-command-execution, Property 1: Direct Command Detection
        
        For any input string that starts with a command from the DIRECT_COMMANDS set 
        (optionally followed by arguments), the CommandDetector SHALL classify it as 
        InputType.DIRECT_COMMAND.
        
        Validates: Requirements 1.1, 1.2
        """
        detector = CommandDetector()
        
        # Build input string
        if args:
            user_input = f"{command} {args}"
        else:
            user_input = command
        
        result = detector.detect(user_input)
        
        # Verify classification
        assert result.input_type == InputType.DIRECT_COMMAND, \
            f"Input '{user_input}' should be classified as DIRECT_COMMAND"
        
        # Verify command is extracted correctly
        assert result.command == command.lower(), \
            f"Command should be '{command.lower()}', got '{result.command}'"
        
        # Verify args are extracted correctly
        # Note: args may be normalized (whitespace stripped) by the detector
        if args:
            assert result.args is not None, \
                f"Args should not be None when provided"
            # The args should contain the essential content
            assert result.args.strip() == args.strip(), \
                f"Args should be '{args.strip()}', got '{result.args.strip()}'"
        else:
            assert result.args is None, \
                f"Args should be None, got '{result.args}'"
        
        # Verify original input is preserved
        assert result.original_input == user_input, \
            f"Original input should be preserved"
    
    @given(
        non_command_text=st.one_of(
            # Natural language queries
            st.text(min_size=10, max_size=100),
            # Questions
            st.from_regex(r"(what|how|why|when|where|who) .+", fullmatch=True),
            # Commands that don't exist
            st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=15, max_size=30)
        )
    )
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.filter_too_much])
    def test_property_2_ai_routing_for_non_commands(self, non_command_text):
        """
        Feature: direct-command-execution, Property 2: AI Routing for Non-Commands
        
        For any input string that does NOT start with a command from the DIRECT_COMMANDS 
        set, the CommandDetector SHALL classify it as InputType.AI_QUERY.
        
        Validates: Requirements 1.3, 1.4, 4.1
        """
        detector = CommandDetector()
        
        # Skip if by chance we generated a direct command
        if non_command_text.strip():
            first_word = non_command_text.strip().split()[0].lower()
            if first_word in CommandDetector.DIRECT_COMMANDS:
                return
        
        result = detector.detect(non_command_text)
        
        # Verify classification
        assert result.input_type == InputType.AI_QUERY, \
            f"Input '{non_command_text}' should be classified as AI_QUERY"
        
        # Verify original input is preserved
        assert result.original_input == non_command_text, \
            f"Original input should be preserved"


class TestCommandDetectorUnitTests:
    """Unit tests for specific CommandDetector scenarios."""
    
    def test_empty_input_routes_to_ai(self):
        """Test that empty input is routed to AI."""
        detector = CommandDetector()
        result = detector.detect("")
        
        assert result.input_type == InputType.AI_QUERY
        assert result.command is None
        assert result.args is None
    
    def test_whitespace_only_input_routes_to_ai(self):
        """Test that whitespace-only input is routed to AI."""
        detector = CommandDetector()
        result = detector.detect("   \t\n  ")
        
        assert result.input_type == InputType.AI_QUERY
        assert result.command is None
        assert result.args is None
    
    def test_ls_command_detected(self):
        """Test that 'ls' command is detected as direct command."""
        detector = CommandDetector()
        result = detector.detect("ls")
        
        assert result.input_type == InputType.DIRECT_COMMAND
        assert result.command == "ls"
        assert result.args is None
    
    def test_ls_with_args_detected(self):
        """Test that 'ls -la' is detected as direct command with args."""
        detector = CommandDetector()
        result = detector.detect("ls -la")
        
        assert result.input_type == InputType.DIRECT_COMMAND
        assert result.command == "ls"
        assert result.args == "-la"
    
    def test_cd_command_detected(self):
        """Test that 'cd' command is detected as direct command."""
        detector = CommandDetector()
        result = detector.detect("cd /home/user")
        
        assert result.input_type == InputType.DIRECT_COMMAND
        assert result.command == "cd"
        assert result.args == "/home/user"
    
    def test_natural_language_routes_to_ai(self):
        """Test that natural language input routes to AI."""
        detector = CommandDetector()
        result = detector.detect("list files in current directory")
        
        assert result.input_type == InputType.AI_QUERY
        assert result.command is None
    
    def test_unknown_command_routes_to_ai(self):
        """Test that unknown commands route to AI."""
        detector = CommandDetector()
        result = detector.detect("unknowncommand123")
        
        assert result.input_type == InputType.AI_QUERY
        assert result.command is None
    
    def test_windows_dir_command_detected(self):
        """Test that Windows 'dir' command is detected."""
        detector = CommandDetector()
        result = detector.detect("dir")
        
        assert result.input_type == InputType.DIRECT_COMMAND
        assert result.command == "dir"
    
    def test_windows_cls_command_detected(self):
        """Test that Windows 'cls' command is detected."""
        detector = CommandDetector()
        result = detector.detect("cls")
        
        assert result.input_type == InputType.DIRECT_COMMAND
        assert result.command == "cls"
    
    def test_case_insensitive_detection(self):
        """Test that command detection is case-insensitive."""
        detector = CommandDetector()
        
        result_lower = detector.detect("ls")
        result_upper = detector.detect("LS")
        result_mixed = detector.detect("Ls")
        
        assert result_lower.input_type == InputType.DIRECT_COMMAND
        assert result_upper.input_type == InputType.DIRECT_COMMAND
        assert result_mixed.input_type == InputType.DIRECT_COMMAND
        
        assert result_lower.command == "ls"
        assert result_upper.command == "ls"
        assert result_mixed.command == "ls"
