"""
Integration tests for ShelloClient with real API calls.

These tests make actual API calls to verify the client works correctly.
They are marked as integration tests and can be skipped in CI/CD.
"""

import pytest
from shello_cli.api.openai_client import ShelloClient
from shello_cli.settings import SettingsManager
from shello_cli.types import ShelloTool


@pytest.mark.integration
class TestShelloClientIntegration:
    """Integration tests that make real API calls."""
    
    def test_simple_chat_completion(self):
        """Test a simple chat completion with the configured model."""
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
        
        # Initialize client
        client = ShelloClient(api_key=api_key, model=model, base_url=base_url)
        
        # Simple test message
        messages = [
            {"role": "user", "content": "Say 'Hello, World!' and nothing else."}
        ]
        
        # Make API call
        try:
            response = client.chat(messages)
        except Exception as e:
            if "401" in str(e) or "AuthenticationError" in str(e) or "User not found" in str(e):
                pytest.skip(f"OpenAI API key is invalid or unauthorized: {e}")
            raise
        
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
        try:
            openai_config = settings_manager.get_provider_config("openai")
        except ValueError:
            pytest.skip("OpenAI provider not configured")
            
        api_key = openai_config.get("api_key")
        base_url = openai_config.get("base_url")
        model = openai_config.get("model") or "gpt-4o"
        
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
        try:
            response = client.chat(messages, tools=tools)
        except Exception as e:
            if "401" in str(e) or "AuthenticationError" in str(e) or "User not found" in str(e):
                pytest.skip(f"OpenAI API key is invalid or unauthorized: {e}")
            raise
        
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
        try:
            openai_config = settings_manager.get_provider_config("openai")
        except ValueError:
            pytest.skip("OpenAI provider not configured")
            
        api_key = openai_config.get("api_key")
        base_url = openai_config.get("base_url")
        model = openai_config.get("model") or "gpt-4o"
        
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
        try:
            for chunk in client.chat_stream(messages):
                chunks.append(chunk)
                # Verify chunk structure
                assert chunk is not None
                assert "choices" in chunk
        except Exception as e:
            if "401" in str(e) or "AuthenticationError" in str(e) or "User not found" in str(e):
                pytest.skip(f"OpenAI API key is invalid or unauthorized: {e}")
            raise
        
        # Verify we got multiple chunks
        assert len(chunks) > 0
        
        print(f"\n✓ Model: {model}")
        print(f"✓ Received {len(chunks)} streaming chunks")
    
    def test_model_switching(self):
        """Test switching between different models."""
        # Load settings
        settings_manager = SettingsManager.get_instance()
        try:
            openai_config = settings_manager.get_provider_config("openai")
        except ValueError:
            pytest.skip("OpenAI provider not configured")

        api_key = openai_config.get("api_key")
        base_url = openai_config.get("base_url")

        if not api_key:
            pytest.skip("No API key configured")

        # Use the configured default model and pick a second from the models list
        default_model = openai_config.get("default_model") or openai_config.get("model")
        models_list = openai_config.get("models", [])
        second_model = next((m for m in models_list if m != default_model), None)

        if not default_model:
            pytest.skip("No default model configured")

        # Initialize client with the default model
        client = ShelloClient(api_key=api_key, model=default_model, base_url=base_url)

        # Verify initial model
        assert client.get_current_model() == default_model

        # Make a simple call
        messages = [{"role": "user", "content": "Say 'test1'"}]
        try:
            response1 = client.chat(messages)
        except Exception as e:
            if "401" in str(e) or "AuthenticationError" in str(e) or "User not found" in str(e):
                pytest.skip(f"OpenAI API key is invalid or unauthorized: {e}")
            raise
        assert response1 is not None

        # Switch model (to second configured model if available, otherwise same model)
        target_model = second_model if second_model else default_model
        client.set_model(target_model)
        assert client.get_current_model() == target_model

        print(f"\n✓ Successfully switched models")
        print(f"✓ Current model: {client.get_current_model()}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
