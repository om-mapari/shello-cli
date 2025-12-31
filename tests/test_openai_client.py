"""
Property-based tests for ShelloClient (OpenAI client).

Feature: openai-cli-refactor
Tests OpenAI client functionality including model selection consistency.
"""

import pytest
from hypothesis import given, strategies as st, settings
from shello_cli.api.openai_client import ShelloClient


class TestShelloClientProperties:
    """Property-based tests for ShelloClient."""
    
    @given(model=st.sampled_from([
        'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 'gpt-3.5-turbo',
        'claude-3-opus', 'claude-3-sonnet', 'llama-3-70b', 'mistral-large'
    ]))
    @settings(max_examples=100, deadline=None)
    def test_property_5_model_selection_consistency(self, model):
        """
        Feature: openai-cli-refactor, Property 5: Model Selection Consistency
        
        For any valid model string, calling set_model(model) followed by 
        get_current_model() SHALL return the same model string.
        
        Validates: Requirements 1.5
        """
        # Initialize client with a dummy API key (we won't make actual API calls)
        client = ShelloClient(api_key="test-key-12345")
        
        # Set the model
        client.set_model(model)
        
        # Get the current model
        current_model = client.get_current_model()
        
        # Verify consistency
        assert current_model == model, \
            f"Expected model '{model}' but got '{current_model}'"


class TestShelloClientUnitTests:
    """Unit tests for specific ShelloClient scenarios."""
    
    def test_initialization_with_default_model(self):
        """Test that client initializes with default model."""
        client = ShelloClient(api_key="test-key")
        
        assert client.get_current_model() == "gpt-4o"
    
    def test_initialization_with_custom_model(self):
        """Test that client initializes with custom model."""
        client = ShelloClient(api_key="test-key", model="gpt-4-turbo")
        
        assert client.get_current_model() == "gpt-4-turbo"
    
    def test_initialization_with_base_url(self):
        """Test that client initializes with custom base URL."""
        client = ShelloClient(
            api_key="test-key",
            base_url="https://custom-api.example.com/v1"
        )
        
        # Should not raise an error
        assert client is not None
        assert client.get_current_model() == "gpt-4o"
    
    def test_initialization_without_api_key_raises_error(self):
        """Test that initializing without API key raises ValueError."""
        with pytest.raises(ValueError, match="API key cannot be None or empty"):
            ShelloClient(api_key="")
        
        with pytest.raises(ValueError, match="API key cannot be None or empty"):
            ShelloClient(api_key=None)
    
    def test_set_model_changes_current_model(self):
        """Test that set_model changes the current model."""
        client = ShelloClient(api_key="test-key", model="gpt-4o")
        
        assert client.get_current_model() == "gpt-4o"
        
        client.set_model("gpt-4-turbo")
        assert client.get_current_model() == "gpt-4-turbo"
        
        client.set_model("gpt-3.5-turbo")
        assert client.get_current_model() == "gpt-3.5-turbo"
    
    def test_multiple_model_changes(self):
        """Test multiple consecutive model changes."""
        client = ShelloClient(api_key="test-key")
        
        models = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o-mini"]
        
        for model in models:
            client.set_model(model)
            assert client.get_current_model() == model
