"""
Test message processor handling of different response scenarios.

Tests three key scenarios:
1. Content only (no tool calls)
2. Tool calls only (no content)
3. Content + tool calls (both present)
"""

import unittest
from unittest.mock import Mock, MagicMock, patch
from shello_cli.agent.message_processor import MessageProcessor
from shello_cli.agent.models import ChatEntry, StreamingChunk
from shello_cli.types import ToolResult
from datetime import datetime


class TestMessageProcessorScenarios(unittest.TestCase):
    """Test different response scenarios from the AI."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_client = Mock()
        self.mock_tool_executor = Mock()
        self.processor = MessageProcessor(
            client=self.mock_client,
            tool_executor=self.mock_tool_executor,
            max_tool_rounds=10
        )
        self.messages = [{"role": "user", "content": "test"}]
        self.chat_history = []
    
    @patch('shello_cli.agent.message_processor.get_all_tools')
    def test_content_only_response(self, mock_get_tools):
        """Test response with content only (no tool calls)."""
        mock_get_tools.return_value = []
        
        # Mock API response with content only
        self.mock_client.chat.return_value = {
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Here is my response without any tool calls."
                }
            }]
        }
        
        # Process message
        entries = self.processor.process_message(self.messages, self.chat_history)
        
        # Verify
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].type, "assistant")
        self.assertEqual(entries[0].content, "Here is my response without any tool calls.")
        self.assertIsNone(entries[0].tool_calls)
        
        # Verify message was added to history
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(self.messages[1]["role"], "assistant")
        self.assertEqual(self.messages[1]["content"], "Here is my response without any tool calls.")
        self.assertNotIn("tool_calls", self.messages[1])
    
    @patch('shello_cli.agent.message_processor.get_all_tools')
    def test_tool_calls_only_response(self, mock_get_tools):
        """Test response with tool calls only (no content)."""
        mock_get_tools.return_value = []
        
        # Mock API response with tool calls only (no content)
        tool_call = {
            "id": "call_123",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": '{"command": "ls -la"}'
            }
        }
        
        # First response: tool calls only
        self.mock_client.chat.side_effect = [
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": None,  # No content
                        "tool_calls": [tool_call]
                    }
                }]
            },
            # Second response: final answer after tool execution
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Here are the files in the directory."
                    }
                }]
            }
        ]
        
        # Mock tool execution
        self.mock_tool_executor.execute_tool.return_value = ToolResult(
            success=True,
            output="file1.txt\nfile2.txt",
            error=None
        )
        
        # Process message
        entries = self.processor.process_message(self.messages, self.chat_history)
        
        # Verify we got tool call, tool result, and final response
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].type, "tool_call")
        self.assertEqual(entries[1].type, "tool_result")
        self.assertEqual(entries[2].type, "assistant")
        
        # Verify tool call entry
        self.assertIsNotNone(entries[0].tool_calls)
        self.assertEqual(len(entries[0].tool_calls), 1)
        self.assertEqual(entries[0].tool_calls[0]["id"], "call_123")
        
        # Verify message history includes tool call with None content
        assistant_msg = self.messages[1]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertIsNone(assistant_msg["content"])
        self.assertIn("tool_calls", assistant_msg)
    
    @patch('shello_cli.agent.message_processor.get_all_tools')
    def test_content_and_tool_calls_response(self, mock_get_tools):
        """Test response with BOTH content and tool calls."""
        mock_get_tools.return_value = []
        
        # Mock API response with BOTH content and tool calls
        tool_call = {
            "id": "call_456",
            "type": "function",
            "function": {
                "name": "bash",
                "arguments": '{"command": "pwd"}'
            }
        }
        
        # First response: content + tool calls
        self.mock_client.chat.side_effect = [
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "Let me check the current directory for you.",  # Content present
                        "tool_calls": [tool_call]  # Tool calls also present
                    }
                }]
            },
            # Second response: final answer after tool execution
            {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": "You are in /home/user directory."
                    }
                }]
            }
        ]
        
        # Mock tool execution
        self.mock_tool_executor.execute_tool.return_value = ToolResult(
            success=True,
            output="/home/user",
            error=None
        )
        
        # Process message
        entries = self.processor.process_message(self.messages, self.chat_history)
        
        # Verify we got tool call, tool result, and final response
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0].type, "tool_call")
        self.assertEqual(entries[1].type, "tool_result")
        self.assertEqual(entries[2].type, "assistant")
        
        # CRITICAL: Verify that content was preserved in message history
        assistant_msg = self.messages[1]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertEqual(assistant_msg["content"], "Let me check the current directory for you.")
        self.assertIn("tool_calls", assistant_msg)
        self.assertEqual(len(assistant_msg["tool_calls"]), 1)
    
    @patch('shello_cli.agent.message_processor.get_all_tools')
    def test_streaming_content_only(self, mock_get_tools):
        """Test streaming response with content only."""
        mock_get_tools.return_value = []
        
        # Mock streaming response with content chunks
        self.mock_client.chat_stream.return_value = [
            {"choices": [{"delta": {"content": "Hello "}}]},
            {"choices": [{"delta": {"content": "world"}}]},
            {"choices": [{"delta": {"content": "!"}}]},
            {"choices": [{"delta": {}}]},  # End of stream
        ]
        
        # Collect chunks
        chunks = list(self.processor.process_message_stream(self.messages, self.chat_history))
        
        # Verify chunks
        content_chunks = [c for c in chunks if c.type == "content"]
        self.assertEqual(len(content_chunks), 3)
        self.assertEqual(content_chunks[0].content, "Hello ")
        self.assertEqual(content_chunks[1].content, "world")
        self.assertEqual(content_chunks[2].content, "!")
        
        # Verify done chunk
        done_chunks = [c for c in chunks if c.type == "done"]
        self.assertEqual(len(done_chunks), 1)
        
        # Verify message history
        self.assertEqual(len(self.messages), 2)
        self.assertEqual(self.messages[1]["content"], "Hello world!")
    
    @patch('shello_cli.agent.message_processor.get_all_tools')
    def test_streaming_tool_calls_only(self, mock_get_tools):
        """Test streaming response with tool calls only (no content)."""
        mock_get_tools.return_value = []
        
        # Mock streaming response with tool calls only
        self.mock_client.chat_stream.side_effect = [
            # First stream: tool calls only
            [
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_789", "type": "function"}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "bash"}}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"command"'}}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": ': "echo test"}'}}]}}]},
                {"choices": [{"delta": {}}]},
            ],
            # Second stream: final response
            [
                {"choices": [{"delta": {"content": "Command executed."}}]},
                {"choices": [{"delta": {}}]},
            ]
        ]
        
        # Mock tool execution
        mock_stream = iter(["test\n"])
        self.mock_tool_executor.execute_tool_stream.return_value = mock_stream
        
        # Manually set the return value for StopIteration
        def tool_stream_generator():
            yield "test\n"
            return ToolResult(success=True, output="test", error=None)
        
        self.mock_tool_executor.execute_tool_stream.return_value = tool_stream_generator()
        
        # Collect chunks
        chunks = list(self.processor.process_message_stream(self.messages, self.chat_history))
        
        # Verify we got tool_calls chunk
        tool_calls_chunks = [c for c in chunks if c.type == "tool_calls"]
        self.assertEqual(len(tool_calls_chunks), 1)
        
        # Verify tool_call chunk
        tool_call_chunks = [c for c in chunks if c.type == "tool_call"]
        self.assertEqual(len(tool_call_chunks), 1)
        
        # Verify message history has tool call with no content
        assistant_msg = self.messages[1]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertIn("tool_calls", assistant_msg)
        # Content should be None or empty string
        self.assertIn(assistant_msg["content"], [None, ""])
    
    @patch('shello_cli.agent.message_processor.get_all_tools')
    def test_streaming_content_and_tool_calls(self, mock_get_tools):
        """Test streaming response with BOTH content and tool calls."""
        mock_get_tools.return_value = []
        
        # Mock streaming response with content first, then tool calls
        self.mock_client.chat_stream.side_effect = [
            # First stream: content + tool calls
            [
                {"choices": [{"delta": {"content": "Let me "}}]},
                {"choices": [{"delta": {"content": "help you."}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_999", "type": "function"}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"name": "bash"}}]}}]},
                {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": '{"command": "date"}'}}]}}]},
                {"choices": [{"delta": {}}]},
            ],
            # Second stream: final response
            [
                {"choices": [{"delta": {"content": "Done!"}}]},
                {"choices": [{"delta": {}}]},
            ]
        ]
        
        # Mock tool execution
        def tool_stream_generator():
            yield "Mon Jan 1 12:00:00\n"
            return ToolResult(success=True, output="Mon Jan 1 12:00:00", error=None)
        
        self.mock_tool_executor.execute_tool_stream.return_value = tool_stream_generator()
        
        # Collect chunks
        chunks = list(self.processor.process_message_stream(self.messages, self.chat_history))
        
        # Verify we got content chunks
        content_chunks = [c for c in chunks if c.type == "content"]
        self.assertGreaterEqual(len(content_chunks), 2)
        
        # Verify we got tool_calls chunk
        tool_calls_chunks = [c for c in chunks if c.type == "tool_calls"]
        self.assertEqual(len(tool_calls_chunks), 1)
        
        # CRITICAL: Verify message history preserved BOTH content and tool calls
        assistant_msg = self.messages[1]
        self.assertEqual(assistant_msg["role"], "assistant")
        self.assertEqual(assistant_msg["content"], "Let me help you.")  # Content preserved
        self.assertIn("tool_calls", assistant_msg)  # Tool calls also present
        self.assertEqual(len(assistant_msg["tool_calls"]), 1)
        self.assertEqual(assistant_msg["tool_calls"][0]["function"]["name"], "bash")


if __name__ == "__main__":
    unittest.main()
