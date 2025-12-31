"""
Integration tests for ShelloClient with real API calls.

These tests make actual API calls to verify the client works correctly.
They are marked as integration tests and can be skipped in CI/CD.
"""

import pytest
from shello_cli.api.openai_client import ShelloClient
from shello_cli.utils.settings_manager import SettingsManager
from shello_cli.types import ShelloTool


@pytest.mark.integration
class TestShelloClientIntegration:
    """Integration tests that make real API calls."""
    
    def test_simple_chat_completion(self):
        """Test a simple chat completion with the configured model."""
        # Load settings
        settings_manager = SettingsManager.get_instance()
        api_key = settings_manager.get_api_key()
        base_url = settings_manager.get_base_url()
        model = settings_manager.get_current_model()
        
        if not api_key:
            pytest.skip("No API key configured")
        
        # Initialize client
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        
        # Simple test message
        messages = [
            {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
        ]
        
        # Make API call
        response = client.chat(messages)
        
        # Verify response structure
        assert response is not None
        assert "choices" in response
        assert len(response["choices"]) > 0
        assert "message" in response["choices"][0]
        assert "content" in response["choices"][0]["message"]
        
        # Verify we got a response
        content = response["choices"][0]["message"]["content"]
        assert content is not None
        assert len(content) > 0
        
        print(f"\n✓ Model: {model}")
        print(f"✓ Response: {content}")
    
    def test_chat_with_tools(self):
        """Test chat completion with tool definitions."""
        # Load settings
        settings_manager = SettingsManager.get_instance()
        api_key = settings_manager.get_api_key()
        base_url = settings_manager.get_base_url()
        model = settings_manager.get_current_model()
        
        if not api_key:
            pytest.skip("No API key configured")
        
        # Initialize client
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        
        # Define a simple tool
        tools = [
            ShelloTool(
                type="function",
                function={
                    "name": "get_weather",
                    "description": "Get the weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "The city name"
                            }
                        },
                        "required": ["location"]
                    }
                }
            )
        ]
        
        # Message that should trigger tool use
        messages = [
            {"role": "user", "content": "What's the weather in Paris?"}
        ]
        
        # Make API call with tools
        response = client.chat(messages, tools=tools)
        
        # Verify response structure
        assert response is not None
        assert "choices" in response
        assert len(response["choices"]) > 0
        
        print(f"\n✓ Model: {model}")
        print(f"✓ Response with tools: {response['choices'][0]['message']}")
    
    def test_streaming_chat(self):
        """Test streaming chat completion."""
        # Load settings
        settings_manager = SettingsManager.get_instance()
        api_key = settings_manager.get_api_key()
        base_url = settings_manager.get_base_url()
        model = settings_manager.get_current_model()
        
        if not api_key:
            pytest.skip("No API key configured")
        
        # Initialize client
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        
        # Simple test message
        messages = [
            {"role": "user", "content": "Count from 1 to 5, one number per line."}
        ]
        
        # Make streaming API call
        chunks = []
        for chunk in client.chat_stream(messages):
            chunks.append(chunk)
            # Verify chunk structure
            assert chunk is not None
            assert "choices" in chunk
        
        # Verify we got multiple chunks
        assert len(chunks) > 0
        
        print(f"\n✓ Model: {model}")
        print(f"✓ Received {len(chunks)} streaming chunks")
    
    def test_model_switching(self):
        """Test switching between different models."""
        # Load settings
        settings_manager = SettingsManager.get_instance()
        api_key = settings_manager.get_api_key()
        base_url = settings_manager.get_base_url()
        
        if not api_key:
            pytest.skip("No API key configured")
        
        # Initialize client with first model
        client = ShelloClient(api_key=api_key, model="mistralai/devstral-2512:free", base_url=base_url)
        
        # Verify initial model
        assert client.get_current_model() == "mistralai/devstral-2512:free"
        
        # Make a simple call
        messages = [{"role": "user", "content": "Say 'test1'"}]
        response1 = client.chat(messages)
        assert response1 is not None
        
        # Switch model
        client.set_model("gpt-4o-mini")
        assert client.get_current_model() == "gpt-4o-mini"
        
        print(f"\n✓ Successfully switched models")
        print(f"✓ Current model: {client.get_current_model()}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
