"""
Integration tests for MessageProcessor with real API calls.

Tests three key scenarios with real AI:
1. Content only (no tool calls)
2. Tool calls only (no content)
3. Content + tool calls (both present)
"""

import pytest
from shello_cli.agent.message_processor import MessageProcessor
from shello_cli.agent.tool_executor import ToolExecutor
from shello_cli.api.openai_client import ShelloClient
from shello_cli.settings import SettingsManager
from shello_cli.agent.models import ChatEntry


@pytest.mark.integration
class TestMessageProcessorIntegration:
    """Integration tests with real API calls."""
    
    @pytest.fixture
    def setup(self):
        """Set up test fixtures with real client."""
        # Load settings
        settings_manager = SettingsManager.get_instance()
        try:
            openai_config = settings_manager.get_provider_config("openai")
        except ValueError:
            pytest.skip("OpenAI provider not configured")
            
        api_key = openai_config.get("api_key")
        base_url = openai_config.get("base_url")
        model = openai_config.get("model") or "gpt-4o"
        
        if not api_key:
            pytest.skip("No API key configured")
        
        # Initialize real components
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        tool_executor = ToolExecutor()
        processor = MessageProcessor(
            client=client,
            tool_executor=tool_executor,
            max_tool_rounds=5
        )
        
        return {
            "processor": processor,
            "client": client,
            "model": model
        }
    
    def test_content_only_response(self, setup):
        """Test real API response with content only (no tool calls)."""
        processor = setup["processor"]
        model = setup["model"]
        
        # Create a message that should NOT trigger tool use
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Do NOT use any tools. Just respond with text."},
            {"role": "user", "content": "What is 2+2? Just tell me the answer, don't use any tools."}
        ]
        chat_history = []
        
        print(f"\n🧪 Testing content-only response with {model}")
        
        # Process message
        entries = processor.process_message(messages, chat_history)
        
        # Check if the response was an auth error
        if entries and entries[-1].content and ("401" in entries[-1].content or "AuthenticationError" in entries[-1].content or "User not found" in entries[-1].content):
            pytest.skip(f"OpenAI API key is invalid or unauthorized: {entries[-1].content}")
        
        # Verify we got only assistant response (no tool calls)
        print(f"✓ Received {len(entries)} entries")
        
        # Should have exactly 1 entry (assistant response)
        assert len(entries) >= 1, "Should have at least one entry"
        
        # Last entry should be assistant response
        last_entry = entries[-1]
        assert last_entry.type == "assistant", f"Last entry should be assistant, got {last_entry.type}"
        assert last_entry.content, "Should have content"
        assert last_entry.tool_calls is None, "Should NOT have tool calls"
        
        print(f"✓ Content: {last_entry.content[:100]}...")
        print(f"✓ No tool calls present")
        
        # Verify message history
        assert len(messages) == 3, "Should have system + user + assistant"
        assert messages[-1]["role"] == "assistant"
        assert messages[-1]["content"]
        assert "tool_calls" not in messages[-1]
        
        print("✅ Content-only test PASSED")
    
    def test_tool_calls_only_response(self, setup):
        """Test real API response with tool calls only (minimal/no content)."""
        processor = setup["processor"]
        model = setup["model"]
        
        # Create a message that SHOULD trigger tool use
        messages = [
            {"role": "system", "content": "You are a helpful assistant with access to shell commands."},
            {"role": "user", "content": "Run the command 'echo hello' using the run_shell_command tool. Don't explain, just do it."}
        ]
        chat_history = []
        
        print(f"\n🧪 Testing tool-calls-only response with {model}")
        
        # Process message (this will execute the tool)
        entries = processor.process_message(messages, chat_history)
        
        # Check if the response was an auth error
        if entries and entries[-1].content and ("401" in entries[-1].content or "AuthenticationError" in entries[-1].content or "User not found" in entries[-1].content):
            pytest.skip(f"OpenAI API key is invalid or unauthorized: {entries[-1].content}")
        
        print(f"✓ Received {len(entries)} entries")
        
        # Should have: tool_call entry, tool_result entry, and final assistant response
        assert len(entries) >= 2, "Should have at least tool_call and tool_result"
        
        # First entry should be tool_call
        tool_call_entry = entries[0]
        assert tool_call_entry.type == "tool_call", f"First entry should be tool_call, got {tool_call_entry.type}"
        assert tool_call_entry.tool_calls is not None, "Should have tool_calls"
        assert len(tool_call_entry.tool_calls) > 0, "Should have at least one tool call"
        
        print(f"✓ Tool called: {tool_call_entry.tool_calls[0]['function']['name']}")
        
        # Check if content was present or not in the tool call message
        # Find the assistant message with tool_calls in message history
        tool_call_msg = None
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_call_msg = msg
                break
        
        assert tool_call_msg is not None, "Should have assistant message with tool_calls"
        
        # Content might be None or empty string for tool-calls-only
        content = tool_call_msg.get("content")
        print(f"✓ Content in tool call message: {repr(content)}")
        
        if content:
            print(f"  (Model included explanation: '{content[:50]}...')")
        else:
            print(f"  (No content - tool calls only)")
        
        # Second entry should be tool_result
        tool_result_entry = entries[1]
        assert tool_result_entry.type == "tool_result", f"Second entry should be tool_result, got {tool_result_entry.type}"
        assert tool_result_entry.tool_result is not None, "Should have tool_result"
        
        print(f"✓ Tool result: {tool_result_entry.tool_result.success}")
        print(f"✓ Tool output: {tool_result_entry.content[:50] if tool_result_entry.content else 'None'}...")
        
        print("✅ Tool-calls test PASSED")
    
    def test_content_and_tool_calls_response(self, setup):
        """Test real API response with BOTH content and tool calls."""
        processor = setup["processor"]
        model = setup["model"]
        
        # Create a message that should trigger BOTH explanation and tool use
        messages = [
            {"role": "system", "content": "You are a helpful assistant. When using tools, explain what you're doing."},
            {"role": "user", "content": "Check what directory I'm in by running 'pwd' command. Explain what you're doing."}
        ]
        chat_history = []
        
        print(f"\n🧪 Testing content + tool-calls response with {model}")
        
        # Process message
        entries = processor.process_message(messages, chat_history)
        
        # Check if the response was an auth error
        if entries and entries[-1].content and ("401" in entries[-1].content or "AuthenticationError" in entries[-1].content or "User not found" in entries[-1].content):
            pytest.skip(f"OpenAI API key is invalid or unauthorized: {entries[-1].content}")
        
        print(f"✓ Received {len(entries)} entries")
        
        # Should have: tool_call entry, tool_result entry, and final assistant response
        assert len(entries) >= 2, "Should have at least tool_call and tool_result"
        
        # First entry should be tool_call
        tool_call_entry = entries[0]
        assert tool_call_entry.type == "tool_call", f"First entry should be tool_call, got {tool_call_entry.type}"
        assert tool_call_entry.tool_calls is not None, "Should have tool_calls"
        
        # Find the assistant message with tool_calls in message history
        tool_call_msg = None
        for msg in messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tool_call_msg = msg
                break
        
        assert tool_call_msg is not None, "Should have assistant message with tool_calls"
        
        # CRITICAL: Check if content is present along with tool_calls
        content = tool_call_msg.get("content")
        has_content = content is not None and content != ""
        has_tool_calls = "tool_calls" in tool_call_msg and len(tool_call_msg["tool_calls"]) > 0
        
        print(f"✓ Has content: {has_content}")
        print(f"✓ Has tool_calls: {has_tool_calls}")
        
        if has_content:
            print(f"✓ Content: '{content[:100]}...'")
            print(f"✓ Tool: {tool_call_msg['tool_calls'][0]['function']['name']}")
            print("✅ BOTH content and tool_calls present!")
        else:
            print(f"⚠️  Model chose not to include content with tool call")
            print(f"✓ Tool: {tool_call_msg['tool_calls'][0]['function']['name']}")
        
        # Verify tool was executed
        tool_result_entry = entries[1]
        assert tool_result_entry.type == "tool_result", "Should have tool_result"
        print(f"✓ Tool executed successfully")
        
        print("✅ Content + tool-calls test PASSED")
    
    def test_streaming_content_only(self, setup):
        """Test streaming with content only."""
        processor = setup["processor"]
        model = setup["model"]
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Do NOT use any tools."},
            {"role": "user", "content": "Count from 1 to 3. Just respond with text, no tools."}
        ]
        chat_history = []
        
        print(f"\n🧪 Testing streaming content-only with {model}")
        
        # Collect all chunks
        try:
            chunks = list(processor.process_message_stream(messages, chat_history))
        except Exception as e:
            if "401" in str(e) or "AuthenticationError" in str(e) or "User not found" in str(e):
                pytest.skip(f"OpenAI API key is invalid or unauthorized: {e}")
            raise
        
        # Check if the response was an auth error
        full_content = "".join(c.content for c in chunks if c.content)
        if "401" in full_content or "AuthenticationError" in full_content or "User not found" in full_content:
            pytest.skip(f"OpenAI API key is invalid or unauthorized: {full_content}")
        
        print(f"✓ Received {len(chunks)} chunks")
        
        # Should have content chunks and done chunk
        content_chunks = [c for c in chunks if c.type == "content"]
        done_chunks = [c for c in chunks if c.type == "done"]
        tool_chunks = [c for c in chunks if c.type in ["tool_calls", "tool_call"]]
        
        print(f"✓ Content chunks: {len(content_chunks)}")
        print(f"✓ Tool chunks: {len(tool_chunks)}")
        print(f"✓ Done chunks: {len(done_chunks)}")
        
        assert len(content_chunks) > 0, "Should have content chunks"
        assert len(tool_chunks) == 0, "Should NOT have tool chunks"
        assert len(done_chunks) == 1, "Should have one done chunk"
        
        # Reconstruct content
        full_content = "".join(c.content for c in content_chunks if c.content)
        print(f"✓ Full content: {full_content[:100]}...")
        
        print("✅ Streaming content-only test PASSED")
    
    def test_streaming_with_tool_calls(self, setup):
        """Test streaming with tool calls."""
        # Use fresh setup to avoid contamination
        settings_manager = SettingsManager.get_instance()
        try:
            openai_config = settings_manager.get_provider_config("openai")
        except ValueError:
            pytest.skip("OpenAI provider not configured")
            
        api_key = openai_config.get("api_key")
        base_url = openai_config.get("base_url")
        model = openai_config.get("model") or "gpt-4o"
        
        if not api_key:
            pytest.skip("No API key configured")
        
        # Create completely fresh instances
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        tool_executor = ToolExecutor()
        processor = MessageProcessor(
            client=client,
            tool_executor=tool_executor,
            max_tool_rounds=5
        )
        
        # Fresh message list
        messages = [
            {"role": "system", "content": "You are a helpful assistant with shell access."},
            {"role": "user", "content": "Run 'date' command using run_shell_command."}
        ]
        chat_history = []
        
        print(f"\n🧪 Testing streaming with tool calls with {model}")
        
        try:
            # Collect all chunks
            chunks = list(processor.process_message_stream(messages, chat_history))
        except Exception as e:
            if "401" in str(e) or "AuthenticationError" in str(e) or "User not found" in str(e):
                pytest.skip(f"OpenAI API key is invalid or unauthorized: {e}")
            # If there's another error, print debug info
            print(f"\n❌ Error occurred: {str(e)[:200]}")
            print(f"Messages in history: {len(messages)}")
            for i, msg in enumerate(messages):
                print(f"  [{i}] {msg.get('role')}: {str(msg)[:100]}")
            raise
        
        # Check if the response was an auth error
        full_content = "".join(c.content for c in chunks if c.content)
        if "401" in full_content or "AuthenticationError" in full_content or "User not found" in full_content:
            pytest.skip(f"OpenAI API key is invalid or unauthorized: {full_content}")
        
        print(f"✓ Received {len(chunks)} chunks")
        
        # Categorize chunks
        content_chunks = [c for c in chunks if c.type == "content"]
        tool_calls_chunks = [c for c in chunks if c.type == "tool_calls"]
        tool_call_chunks = [c for c in chunks if c.type == "tool_call"]
        tool_output_chunks = [c for c in chunks if c.type == "tool_output"]
        tool_result_chunks = [c for c in chunks if c.type == "tool_result"]
        
        print(f"✓ Content chunks: {len(content_chunks)}")
        print(f"✓ Tool calls chunks: {len(tool_calls_chunks)}")
        print(f"✓ Tool call chunks: {len(tool_call_chunks)}")
        print(f"✓ Tool output chunks: {len(tool_output_chunks)}")
        print(f"✓ Tool result chunks: {len(tool_result_chunks)}")
        
        # Should have tool-related chunks
        assert len(tool_calls_chunks) > 0, "Should have tool_calls chunk"
        assert len(tool_call_chunks) > 0, "Should have tool_call chunk"
        
        # Check if content was present before tool calls
        if content_chunks:
            content = "".join(c.content for c in content_chunks if c.content)
            print(f"✓ Content before tools: '{content[:100]}...'")
            print("✅ BOTH content and tool_calls in streaming!")
        else:
            print(f"✓ No content before tools (tool-calls only)")
        
        print("✅ Streaming with tool calls test PASSED")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
