"""
Unit tests for natural language detection in CommandDetector.

Feature: direct-command-execution
Tests Requirement 1.3: Natural language context should route to AI
"""
import pytest
from shello_cli.commands.command_detector import CommandDetector, InputType


class TestNaturalLanguageDetection:
    """Tests for detecting natural language vs shell commands."""
    
    def test_which_model_question_routes_to_ai(self):
        """
        Regression test for issue where "which model are you using" was
        incorrectly detected as a shell command.
        
        Validates: Requirement 1.3
        """
        detector = CommandDetector()
        
        # The exact input that was causing the issue
        result = detector.detect("which model are you using")
        
        assert result.input_type == InputType.AI_QUERY, \
            "Natural language question should route to AI"
    
    def test_which_command_with_path_is_direct(self):
        """
        Verify that legitimate 'which' commands are still detected.
        
        Validates: Requirement 1.1
        """
        detector = CommandDetector()
        
        test_cases = [
            "which python",
            "which node",
            "which npm",
            "which git"
        ]
        
        for user_input in test_cases:
            result = detector.detect(user_input)
            assert result.input_type == InputType.DIRECT_COMMAND, \
                f"'{user_input}' should be detected as direct command"
            assert result.command == "which"
    
    def test_natural_language_with_question_words(self):
        """
        Test various natural language patterns with question words.
        
        Validates: Requirement 1.3
        """
        detector = CommandDetector()
        
        natural_language_inputs = [
            "which model are you using",
            "which version are you",
            "which one should I use",
            "what is your model",
            "can you help me",
            "do you support python",
            "tell me about your capabilities",
            "find out what model you use",
            "show me the version"
        ]
        
        for user_input in natural_language_inputs:
            result = detector.detect(user_input)
            assert result.input_type == InputType.AI_QUERY, \
                f"'{user_input}' should route to AI (natural language)"
    
    def test_shell_commands_remain_direct(self):
        """
        Verify that legitimate shell commands are not affected by
        natural language detection.
        
        Validates: Requirement 1.1
        """
        detector = CommandDetector()
        
        shell_commands = [
            "ls -la",
            "pwd",
            "cd /home/user",
            "grep pattern file.txt",
            "find . -name '*.py'",
            "cat README.md",
            "which python3",
            "echo hello",
            "dir /s"
        ]
        
        for user_input in shell_commands:
            result = detector.detect(user_input)
            assert result.input_type == InputType.DIRECT_COMMAND, \
                f"'{user_input}' should be detected as direct command"
    
    def test_question_mark_at_end_with_context(self):
        """
        Test that question marks at the end with natural language context
        route to AI.
        
        Validates: Requirement 1.3
        """
        detector = CommandDetector()
        
        # Questions with context
        result = detector.detect("what is your model?")
        assert result.input_type == InputType.AI_QUERY
        
        result = detector.detect("which model do you use?")
        assert result.input_type == InputType.AI_QUERY
        
        # But single argument with ? should still be direct (shell wildcard/help)
        result = detector.detect("ls ?")
        assert result.input_type == InputType.DIRECT_COMMAND
        
        result = detector.detect("dir ?")
        assert result.input_type == InputType.DIRECT_COMMAND
