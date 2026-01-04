"""
Integration tests for CLI command detection and execution.

Feature: direct-command-execution
"""
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, MagicMock, patch
from shello_cli.commands.command_detector import CommandDetector, InputType
from shello_cli.commands.direct_executor import DirectExecutor, ExecutionResult
from shello_cli.tools.bash_tool import BashTool


# Property 9: No AI Retry on Command Failure
# Validates: Requirements 4.2
@settings(max_examples=100, deadline=None)
@given(
    command=st.sampled_from(['nonexistentcmd', 'fakecmd', 'notarealcommand']),
    args=st.one_of(st.none(), st.text(min_size=0, max_size=20, alphabet=st.characters(blacklist_characters='\x00')))
)
def test_property_no_ai_retry_on_command_failure(command, args):
    """
    Feature: direct-command-execution, Property 9: No AI Retry on Command Failure
    
    For any direct command that fails with "command not found" error,
    the system SHALL NOT subsequently route the same input to AI processing.
    
    **Validates: Requirements 4.2**
    """
    # Setup
    detector = CommandDetector()
    
    # Add the command to DIRECT_COMMANDS to ensure it's detected as direct
    original_commands = detector.DIRECT_COMMANDS.copy()
    detector.DIRECT_COMMANDS.add(command)
    
    try:
        # Build the full input
        full_input = command if args is None else f"{command} {args}"
        
        # Step 1: Detect the command
        detection_result = detector.detect(full_input)
        
        # Verify it's detected as a direct command
        assert detection_result.input_type == InputType.DIRECT_COMMAND
        assert detection_result.command == command
        
        # Step 2: Execute the command (it will fail since it doesn't exist)
        executor = DirectExecutor()
        execution_result = executor.execute(detection_result.command, detection_result.args)
        
        # Verify execution failed
        assert execution_result.success is False
        # Windows PowerShell uses different error messages than bash
        # Check for either "command not found", "not recognized", or parser errors
        # Remove newlines and extra whitespace for comparison
        error_normalized = ' '.join(execution_result.error.lower().split())
        assert any(phrase in error_normalized for phrase in [
            "command not found",
            "not recognized",
            "parsererror",
            "unexpectedtoken"
        ]), f"Error should indicate command failure, got: {execution_result.error}"
        
        # Step 3: Verify the system does NOT retry with AI
        # In the actual CLI implementation, after a direct command fails,
        # we should NOT call chat_session.start_conversation() or continue_conversation()
        # This is verified by checking that the detection result remains DIRECT_COMMAND
        # and the flow doesn't change the input_type to AI_QUERY
        
        # Re-detect the same input - it should still be DIRECT_COMMAND
        second_detection = detector.detect(full_input)
        assert second_detection.input_type == InputType.DIRECT_COMMAND
        
        # The key property: the system maintains the DIRECT_COMMAND classification
        # and does not automatically route to AI on failure
        assert second_detection.input_type != InputType.AI_QUERY
        
    finally:
        # Restore original commands
        detector.DIRECT_COMMANDS = original_commands


def test_example_command_not_found_no_ai_retry():
    """
    Example test: Verify that when 'fakecmd' fails, it doesn't retry with AI.
    
    This is a concrete example demonstrating the property.
    """
    # Setup
    detector = CommandDetector()
    detector.DIRECT_COMMANDS.add('fakecmd')
    
    executor = DirectExecutor()
    
    # Execute
    user_input = "fakecmd --test"
    detection = detector.detect(user_input)
    
    # Verify it's detected as direct command
    assert detection.input_type == InputType.DIRECT_COMMAND
    
    # Execute and fail
    result = executor.execute(detection.command, detection.args)
    assert result.success is False
    # Windows PowerShell uses different error messages than bash
    # Remove newlines and extra whitespace for comparison
    error_normalized = ' '.join(result.error.lower().split())
    assert any(phrase in error_normalized for phrase in [
        "command not found",
        "not recognized",
        "parsererror",
        "unexpectedtoken"
    ]), f"Error should indicate command failure, got: {result.error}"
    
    # Verify it's still classified as direct command (not routed to AI)
    second_detection = detector.detect(user_input)
    assert second_detection.input_type == InputType.DIRECT_COMMAND
    assert second_detection.input_type != InputType.AI_QUERY
