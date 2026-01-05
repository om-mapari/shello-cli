"""
Unit tests for ShelloBedrockClient.

Feature: bedrock-client
Tests AWS Bedrock client functionality including chat completions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from shello_cli.api.bedrock_client import ShelloBedrockClient
from shello_cli.types import ShelloTool


class TestBedrockClientChat:
    """Unit tests for the chat method."""
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_basic_text_response(self, mock_boto3):
        """Test basic chat call with text response."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse response
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [
                        {'text': 'Hello! How can I help you today?'}
                    ]
                }
            },
            'stopReason': 'end_turn',
            'usage': {
                'inputTokens': 10,
                'outputTokens': 8,
                'totalTokens': 18
            }
        }
        mock_client.converse.return_value = mock_response
        
        # Create client and make chat call
        client = ShelloBedrockClient(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1"
        )
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        response = client.chat(messages)
        
        # Verify response format
        assert response['content'] == 'Hello! How can I help you today?'
        assert response['role'] == 'assistant'
        assert response['stopReason'] == 'end_turn'
        assert response['usage']['inputTokens'] == 10
        assert response['usage']['outputTokens'] == 8
        assert response['usage']['totalTokens'] == 18
        
        # Verify converse was called with correct parameters
        mock_client.converse.assert_called_once()
        call_args = mock_client.converse.call_args[1]
        assert call_args['modelId'] == "anthropic.claude-3-sonnet-20240229-v1:0"
        assert len(call_args['messages']) == 1
        assert call_args['messages'][0]['role'] == 'user'
        assert call_args['messages'][0]['content'][0]['text'] == 'Hello'
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_with_system_message(self, mock_boto3):
        """Test chat with system message extraction."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse response
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [{'text': 'I am a helpful assistant.'}]
                }
            },
            'stopReason': 'end_turn',
            'usage': {'inputTokens': 20, 'outputTokens': 10, 'totalTokens': 30}
        }
        mock_client.converse.return_value = mock_response
        
        # Create client
        client = ShelloBedrockClient(region="us-east-1")
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Who are you?"}
        ]
        
        response = client.chat(messages)
        
        # Verify system message was extracted
        call_args = mock_client.converse.call_args[1]
        assert 'system' in call_args
        assert call_args['system'][0]['text'] == "You are a helpful assistant."
        
        # Verify messages don't contain system role
        assert len(call_args['messages']) == 1
        assert call_args['messages'][0]['role'] == 'user'
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_with_tools(self, mock_boto3):
        """Test chat with tool definitions."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse response
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [{'text': 'I can help with that.'}]
                }
            },
            'stopReason': 'end_turn',
            'usage': {'inputTokens': 50, 'outputTokens': 10, 'totalTokens': 60}
        }
        mock_client.converse.return_value = mock_response
        
        # Create client
        client = ShelloBedrockClient(region="us-east-1")
        
        # Define tools
        tools = [
            ShelloTool(
                type="function",
                function={
                    "name": "get_weather",
                    "description": "Get weather for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {"type": "string"}
                        },
                        "required": ["location"]
                    }
                }
            )
        ]
        
        messages = [{"role": "user", "content": "What's the weather?"}]
        
        response = client.chat(messages, tools=tools)
        
        # Verify toolConfig was passed
        call_args = mock_client.converse.call_args[1]
        assert 'toolConfig' in call_args
        assert 'tools' in call_args['toolConfig']
        assert len(call_args['toolConfig']['tools']) == 1
        
        tool_spec = call_args['toolConfig']['tools'][0]['toolSpec']
        assert tool_spec['name'] == 'get_weather'
        assert tool_spec['description'] == 'Get weather for a location'
        assert 'inputSchema' in tool_spec
        assert 'json' in tool_spec['inputSchema']
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_with_tool_use_response(self, mock_boto3):
        """Test chat response with tool use."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock response with tool use
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [
                        {
                            'toolUse': {
                                'toolUseId': 'tool_123',
                                'name': 'get_weather',
                                'input': {'location': 'San Francisco'}
                            }
                        }
                    ]
                }
            },
            'stopReason': 'tool_use',
            'usage': {'inputTokens': 30, 'outputTokens': 15, 'totalTokens': 45}
        }
        mock_client.converse.return_value = mock_response
        
        # Create client
        client = ShelloBedrockClient(region="us-east-1")
        
        messages = [{"role": "user", "content": "What's the weather in SF?"}]
        
        response = client.chat(messages)
        
        # Verify tool call in response
        assert response['stopReason'] == 'tool_use'
        assert 'toolCalls' in response
        assert len(response['toolCalls']) == 1
        
        tool_call = response['toolCalls'][0]
        assert tool_call['id'] == 'tool_123'
        assert tool_call['type'] == 'function'
        assert tool_call['function']['name'] == 'get_weather'
        
        # Verify arguments are JSON string
        import json
        args = json.loads(tool_call['function']['arguments'])
        assert args['location'] == 'San Francisco'
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_error_handling(self, mock_boto3):
        """Test error handling in chat method."""
        from botocore.exceptions import ClientError
        
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock a ClientError
        error_response = {
            'Error': {
                'Code': 'ValidationException',
                'Message': 'Invalid request parameters'
            }
        }
        mock_client.converse.side_effect = ClientError(error_response, 'converse')
        
        # Create client
        client = ShelloBedrockClient(region="us-east-1")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # Verify exception is raised with descriptive message
        with pytest.raises(Exception) as exc_info:
            client.chat(messages)
        
        assert "Bedrock API error" in str(exc_info.value)
        assert "ValidationException" in str(exc_info.value)
        assert "Invalid request parameters" in str(exc_info.value)


class TestBedrockClientInitialization:
    """Unit tests for client initialization."""
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_initialization_with_default_credentials(self, mock_boto3):
        """Test initialization with default AWS credential chain."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        client = ShelloBedrockClient(region="us-west-2")
        
        # Verify boto3.client was called with correct parameters
        mock_boto3.client.assert_called_once()
        call_args = mock_boto3.client.call_args
        
        assert call_args[1]['service_name'] == 'bedrock-runtime'
        assert client.get_current_model() == "anthropic.claude-3-sonnet-20240229-v1:0"
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_initialization_with_explicit_credentials(self, mock_boto3):
        """Test initialization with explicit AWS credentials."""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        client = ShelloBedrockClient(
            region="us-east-1",
            aws_access_key="AKIAIOSFODNN7EXAMPLE",
            aws_secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )
        
        # Verify boto3.client was called with credentials
        mock_boto3.client.assert_called_once()
        call_args = mock_boto3.client.call_args[1]
        
        assert call_args['aws_access_key_id'] == "AKIAIOSFODNN7EXAMPLE"
        assert call_args['aws_secret_access_key'] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_initialization_with_profile(self, mock_boto3):
        """Test initialization with AWS profile."""
        mock_session = MagicMock()
        mock_client = MagicMock()
        mock_boto3.Session.return_value = mock_session
        mock_session.client.return_value = mock_client
        
        client = ShelloBedrockClient(
            region="us-east-1",
            aws_profile="my-profile"
        )
        
        # Verify Session was created with profile
        mock_boto3.Session.assert_called_once_with(profile_name="my-profile")
        mock_session.client.assert_called_once()
    
    def test_initialization_without_region_raises_error(self):
        """Test that initializing without region raises ValueError."""
        with pytest.raises(ValueError, match="Region cannot be None or empty"):
            ShelloBedrockClient(region="")
        
        with pytest.raises(ValueError, match="Region cannot be None or empty"):
            ShelloBedrockClient(region=None)


class TestBedrockClientModelManagement:
    """Unit tests for model management."""
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_get_current_model(self, mock_boto3):
        """Test getting current model."""
        mock_boto3.client.return_value = MagicMock()
        
        client = ShelloBedrockClient(
            model="anthropic.claude-3-opus-20240229-v1:0",
            region="us-east-1"
        )
        
        assert client.get_current_model() == "anthropic.claude-3-opus-20240229-v1:0"
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_set_model(self, mock_boto3):
        """Test setting a new model."""
        mock_boto3.client.return_value = MagicMock()
        
        client = ShelloBedrockClient(region="us-east-1")
        
        assert client.get_current_model() == "anthropic.claude-3-sonnet-20240229-v1:0"
        
        client.set_model("amazon.nova-pro-v1:0")
        assert client.get_current_model() == "amazon.nova-pro-v1:0"


class TestBedrockClientStreaming:
    """Unit tests for the chat_stream method."""
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_stream_basic_text(self, mock_boto3):
        """Test streaming chat with text response."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse_stream response
        mock_stream_events = [
            {
                'contentBlockDelta': {
                    'delta': {'text': 'Hello'}
                }
            },
            {
                'contentBlockDelta': {
                    'delta': {'text': ' there!'}
                }
            },
            {
                'metadata': {
                    'usage': {
                        'inputTokens': 10,
                        'outputTokens': 5,
                        'totalTokens': 15
                    }
                }
            },
            {
                'messageStop': {
                    'stopReason': 'end_turn'
                }
            }
        ]
        
        mock_client.converse_stream.return_value = {'stream': mock_stream_events}
        
        # Create client and stream
        client = ShelloBedrockClient(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1"
        )
        
        messages = [{"role": "user", "content": "Hello"}]
        
        chunks = list(client.chat_stream(messages))
        
        # Verify we got text chunks and finish chunk
        assert len(chunks) >= 3
        
        # First chunk should have text "Hello"
        assert 'choices' in chunks[0]
        assert 'delta' in chunks[0]['choices'][0]
        assert chunks[0]['choices'][0]['delta'].get('content') == 'Hello'
        
        # Second chunk should have text " there!"
        assert chunks[1]['choices'][0]['delta'].get('content') == ' there!'
        
        # Last chunk should have finish_reason
        assert 'finish_reason' in chunks[-1]['choices'][0]
        assert chunks[-1]['choices'][0]['finish_reason'] == 'stop'
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_stream_with_tool_use(self, mock_boto3):
        """Test streaming chat with tool use."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock stream events with tool use
        mock_stream_events = [
            {
                'contentBlockStart': {
                    'start': {
                        'toolUse': {
                            'toolUseId': 'tool_abc123',
                            'name': 'get_weather'
                        }
                    }
                }
            },
            {
                'contentBlockDelta': {
                    'delta': {
                        'toolUse': {
                            'input': '{"location":'
                        }
                    }
                }
            },
            {
                'contentBlockDelta': {
                    'delta': {
                        'toolUse': {
                            'input': ' "San Francisco"}'
                        }
                    }
                }
            },
            {
                'messageStop': {
                    'stopReason': 'tool_use'
                }
            }
        ]
        
        mock_client.converse_stream.return_value = {'stream': mock_stream_events}
        
        # Create client
        client = ShelloBedrockClient(region="us-east-1")
        
        messages = [{"role": "user", "content": "What's the weather?"}]
        
        chunks = list(client.chat_stream(messages))
        
        # Verify we got tool call chunks
        assert len(chunks) >= 3
        
        # First chunk should have tool call with id and name
        assert 'choices' in chunks[0]
        delta = chunks[0]['choices'][0]['delta']
        assert 'tool_calls' in delta
        assert delta['tool_calls'][0]['id'] == 'tool_abc123'
        assert delta['tool_calls'][0]['function']['name'] == 'get_weather'
        
        # Subsequent chunks should have arguments
        assert 'tool_calls' in chunks[1]['choices'][0]['delta']
        
        # Last chunk should have finish_reason tool_calls
        assert chunks[-1]['choices'][0]['finish_reason'] == 'tool_calls'
    
    @patch('shello_cli.api.bedrock_client.boto3')
    def test_chat_stream_error_handling(self, mock_boto3):
        """Test error handling in streaming."""
        from botocore.exceptions import ClientError
        
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock a ClientError
        error_response = {
            'Error': {
                'Code': 'ThrottlingException',
                'Message': 'Rate limit exceeded'
            }
        }
        mock_client.converse_stream.side_effect = ClientError(error_response, 'converse_stream')
        
        # Create client
        client = ShelloBedrockClient(region="us-east-1")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        # Collect chunks
        chunks = list(client.chat_stream(messages))
        
        # Should yield error chunk
        assert len(chunks) > 0
        assert 'choices' in chunks[0]
        delta = chunks[0]['choices'][0]['delta']
        assert 'content' in delta
        assert 'Error' in delta['content']
        assert 'ThrottlingException' in delta['content']



class TestBedrockClientDebugLogging:
    """Unit tests for debug logging functionality."""
    
    @patch('shello_cli.api.bedrock_client.boto3')
    @patch('builtins.print')
    def test_debug_logging_enabled(self, mock_print, mock_boto3):
        """Test debug output when debug is enabled."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse response
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [{'text': 'Test response'}]
                }
            },
            'stopReason': 'end_turn',
            'usage': {
                'inputTokens': 10,
                'outputTokens': 5,
                'totalTokens': 15
            }
        }
        mock_client.converse.return_value = mock_response
        
        # Create client with debug enabled
        client = ShelloBedrockClient(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
            debug=True
        )
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        response = client.chat(messages)
        
        # Verify print was called (debug output)
        assert mock_print.call_count > 0
        
        # Check that debug output contains expected strings
        print_calls = [str(call) for call in mock_print.call_args_list]
        debug_output = ' '.join(print_calls)
        
        assert 'BEDROCK API REQUEST' in debug_output
        assert 'BEDROCK API RESPONSE' in debug_output
        assert 'anthropic.claude-3-sonnet-20240229-v1:0' in debug_output
        assert 'us-east-1' in debug_output
    
    @patch('shello_cli.api.bedrock_client.boto3')
    @patch('builtins.print')
    def test_debug_logging_disabled(self, mock_print, mock_boto3):
        """Test no debug output when debug is disabled."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse response
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [{'text': 'Test response'}]
                }
            },
            'stopReason': 'end_turn',
            'usage': {
                'inputTokens': 10,
                'outputTokens': 5,
                'totalTokens': 15
            }
        }
        mock_client.converse.return_value = mock_response
        
        # Create client with debug disabled (default)
        client = ShelloBedrockClient(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
            debug=False
        )
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        response = client.chat(messages)
        
        # Verify print was NOT called (no debug output)
        assert mock_print.call_count == 0
    
    @patch('shello_cli.api.bedrock_client.boto3')
    @patch('builtins.print')
    def test_debug_logging_with_tools(self, mock_print, mock_boto3):
        """Test debug output includes tool information."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse response with tool use
        mock_response = {
            'output': {
                'message': {
                    'role': 'assistant',
                    'content': [
                        {
                            'toolUse': {
                                'toolUseId': 'tool_123',
                                'name': 'bash',
                                'input': {'command': 'ls -la'}
                            }
                        }
                    ]
                }
            },
            'stopReason': 'tool_use',
            'usage': {
                'inputTokens': 20,
                'outputTokens': 10,
                'totalTokens': 30
            }
        }
        mock_client.converse.return_value = mock_response
        
        # Create client with debug enabled
        client = ShelloBedrockClient(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
            debug=True
        )
        
        messages = [
            {"role": "user", "content": "List files"}
        ]
        
        tools = [
            ShelloTool(
                type="function",
                function={
                    "name": "bash",
                    "description": "Execute bash command",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"}
                        }
                    }
                }
            )
        ]
        
        response = client.chat(messages, tools)
        
        # Verify print was called
        assert mock_print.call_count > 0
        
        # Check that debug output contains tool information
        print_calls = [str(call) for call in mock_print.call_args_list]
        debug_output = ' '.join(print_calls)
        
        assert 'Tools' in debug_output or 'bash' in debug_output
        assert 'Tool Calls' in debug_output or 'tool_123' in debug_output
    
    @patch('shello_cli.api.bedrock_client.boto3')
    @patch('builtins.print')
    def test_debug_logging_streaming(self, mock_print, mock_boto3):
        """Test debug output for streaming requests."""
        # Setup mock client
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        
        # Mock the converse_stream response
        mock_stream = {
            'stream': [
                {
                    'contentBlockDelta': {
                        'delta': {'text': 'Hello'}
                    }
                },
                {
                    'messageStop': {
                        'stopReason': 'end_turn'
                    }
                }
            ]
        }
        mock_client.converse_stream.return_value = mock_stream
        
        # Create client with debug enabled
        client = ShelloBedrockClient(
            model="anthropic.claude-3-sonnet-20240229-v1:0",
            region="us-east-1",
            debug=True
        )
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        # Consume the stream
        chunks = list(client.chat_stream(messages))
        
        # Verify print was called for request logging
        assert mock_print.call_count > 0
        
        # Check that debug output contains streaming indicator
        print_calls = [str(call) for call in mock_print.call_args_list]
        debug_output = ' '.join(print_calls)
        
        assert 'BEDROCK API REQUEST' in debug_output
        assert 'STREAMING' in debug_output or 'stream' in debug_output.lower()
