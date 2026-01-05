"""
Property-based tests for ShelloAgent.

Feature: openai-cli-refactor
Tests agent conversation history, tool execution, and error handling.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from hypothesis import given, strategies as st, settings
from shello_cli.agent.shello_agent import ShelloAgent, ChatEntry
from shello_cli.types import ToolResult


def _create_mock_client():
    """Helper to create a mock client with required methods."""
    mock_client = Mock()
    mock_client.chat = Mock()
    mock_client.get_current_model = Mock(return_value="gpt-4o")
    mock_client.set_model = Mock()
    return mock_client


class TestShelloAgentProperties:
    """Property-based tests for ShelloAgent."""
    
    @given(
        messages=st.lists(
            st.text(min_size=1, max_size=100),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=100, deadline=None)
    def test_property_6_conversation_history_preservation(self, messages):
        """
        Feature: openai-cli-refactor, Property 6: Conversation History Preservation
        
        For any sequence of user messages processed by the agent, get_chat_history() 
        SHALL contain entries for all messages in the order they were processed.
        
        Validates: Requirements 4.1
        """
        # Create mock client
        mock_client = _create_mock_client()
        mock_client.chat.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Response",
                    "tool_calls": None
                }
            }]
        }
        
        agent = ShelloAgent(client=mock_client)
        
        # Process each message
        for message in messages:
            agent.process_user_message(message)
        
        # Get chat history
        history = agent.get_chat_history()
        
        # Verify history contains entries for all messages
        user_entries = [entry for entry in history if entry.type == "user"]
        
        # Should have one user entry per message
        assert len(user_entries) == len(messages), \
            f"Expected {len(messages)} user entries, got {len(user_entries)}"
        
        # Verify messages are in order
        for i, (entry, original_message) in enumerate(zip(user_entries, messages)):
            assert entry.content == original_message, \
                f"Message {i}: expected '{original_message}', got '{entry.content}'"
        
        # Verify entries are in chronological order
        for i in range(len(history) - 1):
            assert history[i].timestamp <= history[i + 1].timestamp, \
                f"Entry {i} timestamp is after entry {i+1}"
    
    @given(max_rounds=st.integers(min_value=1, max_value=10))
    @settings(max_examples=100, deadline=None)
    def test_property_7_max_tool_rounds_enforcement(self, max_rounds):
        """
        Feature: openai-cli-refactor, Property 7: Max Tool Rounds Enforcement
        
        For any agent configured with max_tool_rounds=N, the agent SHALL not execute 
        more than N rounds of tool calls regardless of AI responses.
        
        Validates: Requirements 4.5
        """
        # Create mock client
        mock_client = _create_mock_client()
        mock_client.chat.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "bash",
                            "arguments": '{"command": "echo test"}'
                        }
                    }]
                }
            }]
        }
        
        agent = ShelloAgent(
            client=mock_client,
            max_tool_rounds=max_rounds
        )
        
        # Process a message
        entries = agent.process_user_message("test message")
        
        # Count tool execution rounds
        tool_call_entries = [entry for entry in entries if entry.type == "tool_call"]
        
        # Should not exceed max_rounds
        assert len(tool_call_entries) <= max_rounds, \
            f"Expected at most {max_rounds} tool rounds, got {len(tool_call_entries)}"
        
        # Should hit the limit (since we're simulating infinite loop)
        assert len(tool_call_entries) == max_rounds, \
            f"Expected exactly {max_rounds} tool rounds, got {len(tool_call_entries)}"
    
    @given(
        error_message=st.text(min_size=1, max_size=100)
    )
    @settings(max_examples=100, deadline=None)
    def test_property_8_failed_tool_execution_error_propagation(self, error_message):
        """
        Feature: openai-cli-refactor, Property 8: Failed Tool Execution Error Propagation
        
        For any tool execution that fails, the ToolResult SHALL have success=False 
        and a non-empty error string describing the failure.
        
        Validates: Requirements 4.6, 1.6
        """
        # Create mock client and bash tool
        with patch('shello_cli.agent.tool_executor.BashTool') as MockBashTool:
            mock_client = _create_mock_client()
            mock_client.chat.side_effect = [
                # First call: return tool call
                {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "arguments": '{"command": "failing_command"}'
                                }
                            }]
                        }
                    }]
                },
                # Second call: return final response
                {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "Done",
                            "tool_calls": None
                        }
                    }]
                }
            ]
            
            # Setup mock bash tool to return failure
            mock_bash_instance = MockBashTool.return_value
            mock_bash_instance.execute.return_value = ToolResult(
                success=False,
                output=None,
                error=error_message
            )
            
            agent = ShelloAgent(client=mock_client)
            
            # Process a message
            entries = agent.process_user_message("test message")
            
            # Find tool result entries
            tool_result_entries = [entry for entry in entries if entry.type == "tool_result"]
            
            # Should have at least one tool result
            assert len(tool_result_entries) > 0, "Should have at least one tool result entry"
            
            # Check the tool result
            for entry in tool_result_entries:
                result = entry.tool_result
                
                # Verify it's a ToolResult
                assert isinstance(result, ToolResult), "tool_result must be a ToolResult instance"
                
                # Verify success is False
                assert result.success is False, "Failed tool execution must have success=False"
                
                # Verify error is non-empty string
                assert result.error is not None, "Failed tool execution must have error message"
                assert isinstance(result.error, str), "Error must be a string"
                assert len(result.error) > 0, "Error message must be non-empty"
                assert result.error == error_message, \
                    f"Expected error '{error_message}', got '{result.error}'"


class TestShelloAgentUnitTests:
    """Unit tests for specific ShelloAgent scenarios."""
    
    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        mock_client = _create_mock_client()
        agent = ShelloAgent(client=mock_client)
        
        assert agent is not None
        assert agent.get_chat_history() == []
    
    def test_agent_with_custom_max_rounds(self):
        """Test agent initialization with custom max_tool_rounds."""
        mock_client = _create_mock_client()
        agent = ShelloAgent(client=mock_client, max_tool_rounds=5)
        
        assert agent._message_processor._max_tool_rounds == 5
    
    def test_get_current_directory(self):
        """Test get_current_directory returns bash tool's directory."""
        with patch('shello_cli.agent.tool_executor.BashTool') as MockBashTool:
            mock_bash_instance = MockBashTool.return_value
            mock_bash_instance.get_current_directory.return_value = "/test/dir"
            
            mock_client = _create_mock_client()
            agent = ShelloAgent(client=mock_client)
            
            assert agent.get_current_directory() == "/test/dir"
    
    def test_get_current_model(self):
        """Test get_current_model returns client's model."""
        mock_client = _create_mock_client()
        mock_client.get_current_model.return_value = "gpt-4o"
        
        agent = ShelloAgent(client=mock_client)
        
        assert agent.get_current_model() == "gpt-4o"
    
    def test_set_model(self):
        """Test set_model calls client's set_model."""
        mock_client = _create_mock_client()
        
        agent = ShelloAgent(client=mock_client)
        agent.set_model("gpt-4-turbo")
        
        mock_client.set_model.assert_called_once_with("gpt-4-turbo")
    
    def test_process_message_with_no_tool_calls(self):
        """Test processing a message that doesn't require tools."""
        mock_client = _create_mock_client()
        mock_client.chat.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Hello!",
                    "tool_calls": None
                }
            }]
        }
        
        agent = ShelloAgent(client=mock_client)
        entries = agent.process_user_message("Hi")
        
        # Should have assistant entry (user entry is added to history but not returned in entries)
        assert len(entries) >= 1
        assert entries[0].type == "assistant"
        assert entries[0].content == "Hello!"
    
    def test_process_message_with_tool_call(self):
        """Test processing a message that requires a tool call."""
        with patch('shello_cli.agent.tool_executor.BashTool') as MockBashTool:
            mock_client = _create_mock_client()
            mock_client.chat.side_effect = [
                # First call: return tool call
                {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [{
                                "id": "call_123",
                                "type": "function",
                                "function": {
                                    "name": "bash",
                                    "arguments": '{"command": "echo test"}'
                                }
                            }]
                        }
                    }]
                },
                # Second call: return final response
                {
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": "Command executed",
                            "tool_calls": None
                        }
                    }]
                }
            ]
            
            mock_bash_instance = MockBashTool.return_value
            mock_bash_instance.execute.return_value = ToolResult(
                success=True,
                output="test",
                error=None
            )
            
            agent = ShelloAgent(client=mock_client)
            entries = agent.process_user_message("Run echo test")
            
            # Should have tool_call, tool_result, and assistant entries (user entry not returned)
            assert len(entries) >= 3
            assert any(e.type == "tool_call" for e in entries)
            assert any(e.type == "tool_result" for e in entries)
            assert entries[-1].type == "assistant"
    
    def test_execute_tool_with_invalid_json(self):
        """Test tool execution with invalid JSON arguments."""
        mock_client = _create_mock_client()
        agent = ShelloAgent(client=mock_client)
        
        tool_call = {
            "id": "call_123",
            "function": {
                "name": "bash",
                "arguments": "invalid json {"
            }
        }
        
        result = agent._tool_executor.execute_tool(tool_call)
        
        assert result.success is False
        assert "Failed to parse tool arguments" in result.error
    
    def test_execute_tool_with_unknown_tool(self):
        """Test tool execution with unknown tool name."""
        mock_client = _create_mock_client()
        agent = ShelloAgent(client=mock_client)
        
        tool_call = {
            "id": "call_123",
            "function": {
                "name": "unknown_tool",
                "arguments": '{"param": "value"}'
            }
        }
        
        result = agent._tool_executor.execute_tool(tool_call)
        
        assert result.success is False
        assert "Unknown tool" in result.error
    
    def test_execute_tool_with_missing_command(self):
        """Test bash tool execution with missing command parameter."""
        mock_client = _create_mock_client()
        agent = ShelloAgent(client=mock_client)
        
        tool_call = {
            "id": "call_123",
            "function": {
                "name": "bash",
                "arguments": '{}'
            }
        }
        
        result = agent._tool_executor.execute_tool(tool_call)
        
        assert result.success is False
        assert "No command provided" in result.error
    
    def test_api_error_handling(self):
        """Test that API errors are handled gracefully."""
        mock_client = _create_mock_client()
        mock_client.chat.side_effect = Exception("API Error")
        
        agent = ShelloAgent(client=mock_client)
        entries = agent.process_user_message("test")
        
        # Should have error entry (user entry is added to history but not returned in entries)
        assert len(entries) >= 1
        assert entries[0].type == "assistant"
        assert "Error communicating with AI" in entries[0].content
