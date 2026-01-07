"""
AWS Bedrock API client for Shello CLI.

This module provides a client for interacting with AWS Bedrock using the Converse API,
supporting chat completions with tool calling and streaming responses.
"""

import boto3
from typing import List, Optional, Dict, Any, Generator
from botocore.config import Config
from botocore.exceptions import ClientError


class ShelloBedrockClient:
    """AWS Bedrock client for chat completions with tool support.
    
    This client wraps boto3's bedrock-runtime client to provide a consistent
    interface for chat completions with function calling capabilities using
    the Bedrock Converse API.
    
    Attributes:
        _client: The underlying boto3 bedrock-runtime client instance
        _model: The current model being used for completions
        _region: AWS region for the Bedrock service
        _debug: Enable detailed request/response logging
    """
    
    def __init__(
        self,
        model: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        region: str = "us-east-1",
        aws_access_key: Optional[str] = None,
        aws_secret_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        aws_profile: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        debug: bool = False
    ):
        """Initialize the Bedrock client with AWS credentials.
        
        Args:
            model: Model identifier to use for completions (default: Claude 3 Sonnet)
            region: AWS region for Bedrock service (default: "us-east-1")
            aws_access_key: AWS access key ID for explicit authentication
            aws_secret_key: AWS secret access key for explicit authentication
            aws_session_token: Optional AWS session token for temporary credentials
            aws_profile: AWS profile name from credentials file
            endpoint_url: Optional custom endpoint URL for testing or private endpoints
            debug: Enable detailed request/response logging (default: True)
        
        Raises:
            ValueError: If region is invalid or missing
            ClientError: If AWS authentication fails
        """
        if not region:
            raise ValueError("Region cannot be None or empty")
        
        self._model = model
        self._region = region
        self._debug = debug
        
        # Initialize boto3 client with appropriate authentication method
        self._client = self._create_client(
            region=region,
            access_key=aws_access_key,
            secret_key=aws_secret_key,
            session_token=aws_session_token,
            profile=aws_profile,
            endpoint_url=endpoint_url
        )
    
    def _create_client(
        self,
        region: str,
        access_key: Optional[str],
        secret_key: Optional[str],
        session_token: Optional[str],
        profile: Optional[str],
        endpoint_url: Optional[str]
    ) -> Any:
        """Create boto3 Bedrock Runtime client with appropriate authentication.
        
        This method supports multiple authentication methods in order of precedence:
        1. AWS profile (if provided)
        2. Explicit credentials (access_key + secret_key)
        3. Default AWS credential chain (environment variables, config files, IAM roles)
        
        Args:
            region: AWS region for the service
            access_key: AWS access key ID
            secret_key: AWS secret access key
            session_token: Optional session token for temporary credentials
            profile: AWS profile name from credentials file
            endpoint_url: Optional custom endpoint URL
        
        Returns:
            Configured boto3 bedrock-runtime client
        
        Raises:
            ClientError: If authentication fails or region is invalid
        """
        # Configure boto3 client settings
        config = Config(
            region_name=region,
            user_agent_extra='shello-cli/1.0',
            read_timeout=300  # Important for streaming responses
        )
        
        # Method 1: Use AWS profile
        if profile:
            session = boto3.Session(profile_name=profile)
            return session.client(
                service_name='bedrock-runtime',
                config=config,
                endpoint_url=endpoint_url
            )
        
        # Method 2: Use explicit credentials
        elif access_key and secret_key:
            return boto3.client(
                service_name='bedrock-runtime',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=session_token,
                config=config,
                endpoint_url=endpoint_url
            )
        
        # Method 3: Use default AWS credential chain
        else:
            return boto3.client(
                service_name='bedrock-runtime',
                config=config,
                endpoint_url=endpoint_url
            )
    
    def set_model(self, model: str) -> None:
        """Change the current model used for completions.
        
        Args:
            model: The model identifier to use for future completions
                  (e.g., "anthropic.claude-3-sonnet-20240229-v1:0")
        """
        self._model = model
    
    def get_current_model(self) -> str:
        """Get the current model identifier.
        
        Returns:
            The identifier of the model currently being used
        """
        return self._model
    
    def _format_messages(
        self,
        messages: List[Dict[str, Any]]
    ) -> tuple[List[Dict[str, Any]], Optional[List[Dict[str, Any]]]]:
        """Convert OpenAI format messages to Bedrock Converse API format.
        
        This method transforms messages from the OpenAI format used internally
        to the Bedrock Converse API format. It handles:
        - Extracting system messages into a separate list
        - Mapping user/assistant roles
        - Wrapping string content in text content blocks
        - Converting tool calls and tool results
        
        Args:
            messages: List of messages in OpenAI format with role and content
        
        Returns:
            Tuple of (bedrock_messages, system_prompts) where:
            - bedrock_messages: List of user/assistant messages in Bedrock format
            - system_prompts: List of system message content blocks or None
        
        Example:
            Input: [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ]
            Output: (
                [{"role": "user", "content": [{"text": "Hello"}]}],
                [{"text": "You are helpful"}]
            )
        """
        bedrock_messages = []
        system_prompts = []
        
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            
            # Extract system messages separately
            if role == "system":
                if isinstance(content, str) and content:
                    system_prompts.append({"text": content})
                continue
            
            # Handle user and assistant messages
            if role in ["user", "assistant"]:
                bedrock_msg = self._convert_message(msg)
                if bedrock_msg:
                    bedrock_messages.append(bedrock_msg)
            
            # Handle tool result messages (role="tool" in OpenAI format)
            elif role == "tool":
                tool_result_msg = self._convert_tool_result_message(msg)
                if tool_result_msg:
                    bedrock_messages.append(tool_result_msg)
        
        # Return system prompts as None if empty
        return bedrock_messages, system_prompts if system_prompts else None
    
    def _convert_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a single user or assistant message to Bedrock format.
        
        Args:
            msg: Message dictionary with role and content
        
        Returns:
            Bedrock-formatted message or None if invalid
        """
        role = msg.get("role", "")
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])
        
        # Build content blocks
        content_blocks = []
        
        # Handle string content
        if isinstance(content, str) and content:
            content_blocks.append({"text": content})
        
        # Handle tool calls (assistant messages with tool_calls)
        if tool_calls:
            for tool_call in tool_calls:
                tool_use_block = self._convert_tool_call(tool_call)
                if tool_use_block:
                    content_blocks.append(tool_use_block)
        
        # Return formatted message if we have content
        if content_blocks:
            return {
                "role": role,
                "content": content_blocks
            }
        
        return None
    
    def _convert_tool_result_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert a tool result message to Bedrock format.
        
        In OpenAI format, tool results have role="tool" with tool_call_id and content.
        In Bedrock format, tool results are user messages with toolResult blocks.
        
        Args:
            msg: Tool result message in OpenAI format
        
        Returns:
            Bedrock-formatted user message with toolResult or None if invalid
        """
        tool_call_id = msg.get("tool_call_id", "")
        content = msg.get("content", "")
        
        if not tool_call_id:
            return None
        
        # Create toolResult block
        tool_result_block = {
            "toolResult": {
                "toolUseId": tool_call_id,
                "content": [{"text": content if isinstance(content, str) else str(content)}]
            }
        }
        
        # Tool results are sent as user messages in Bedrock
        return {
            "role": "user",
            "content": [tool_result_block]
        }
    
    def _convert_tool_call(self, tool_call: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Convert an OpenAI tool call to Bedrock toolUse format.
        
        Args:
            tool_call: Tool call dictionary with id, type, and function
        
        Returns:
            Bedrock toolUse content block or None if invalid
        """
        import json
        
        tool_id = tool_call.get("id", "")
        function = tool_call.get("function", {})
        function_name = function.get("name", "")
        arguments_str = function.get("arguments", "{}")
        
        if not tool_id or not function_name:
            return None
        
        # Parse arguments from JSON string to dict
        try:
            arguments = json.loads(arguments_str) if isinstance(arguments_str, str) else arguments_str
        except json.JSONDecodeError:
            arguments = {}
        
        return {
            "toolUse": {
                "toolUseId": tool_id,
                "name": function_name,
                "input": arguments
            }
        }
    
    def _format_tools(self, tools: List[Any]) -> Dict[str, Any]:
        """Convert ShelloTool objects to Bedrock toolConfig format.
        
        This method transforms tool definitions from the ShelloTool format
        (compatible with OpenAI function calling) to the Bedrock Converse API
        toolConfig format. The key differences are:
        - Bedrock uses 'toolSpec' wrapper for each tool
        - Parameters are mapped to 'inputSchema.json' (not 'parameters')
        - toolChoice is set to 'auto' to let the model decide when to use tools
        
        Args:
            tools: List of ShelloTool objects or tool dictionaries with function definitions
        
        Returns:
            Dictionary with 'tools' list and 'toolChoice' configuration in Bedrock format
        
        Example:
            Input: [ShelloTool(
                type="function",
                function={
                    "name": "bash",
                    "description": "Execute a bash command",
                    "parameters": {"type": "object", "properties": {...}}
                }
            )]
            Output: {
                "tools": [{
                    "toolSpec": {
                        "name": "bash",
                        "description": "Execute a bash command",
                        "inputSchema": {"json": {"type": "object", "properties": {...}}}
                    }
                }],
                "toolChoice": {"auto": {}}
            }
        """
        bedrock_tools = []
        
        for tool in tools:
            # Handle both ShelloTool dataclass and dict formats
            if hasattr(tool, 'function'):
                # ShelloTool dataclass
                function = tool.function
            elif isinstance(tool, dict) and 'function' in tool:
                # Dict format
                function = tool['function']
            else:
                # Skip invalid tool definitions
                continue
            
            # Extract function details
            name = function.get('name', '')
            description = function.get('description', '')
            parameters = function.get('parameters', {})
            
            if not name:
                # Skip tools without a name
                continue
            
            # Build Bedrock toolSpec format
            tool_spec = {
                "toolSpec": {
                    "name": name,
                    "description": description,
                    "inputSchema": {
                        "json": parameters
                    }
                }
            }
            
            bedrock_tools.append(tool_spec)
        
        # Return toolConfig with tools and auto toolChoice
        return {
            "tools": bedrock_tools,
            "toolChoice": {"auto": {}}
        }
    
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        """Send a chat completion request and return the response.
        
        This method calls the AWS Bedrock Converse API to generate a chat completion.
        It handles message format conversion, tool configuration, and response parsing
        to provide a consistent interface compatible with the OpenAI client.
        
        Args:
            messages: List of message dictionaries in OpenAI format with role and content.
                     System messages are automatically extracted and passed separately.
            tools: Optional list of ShelloTool objects or tool dictionaries for function calling
        
        Returns:
            Dictionary containing the parsed response with the following keys:
            - content: The text content of the assistant's response (str)
            - role: The role of the responder, always "assistant" (str)
            - stopReason: Why the model stopped generating (str)
                         Values: "end_turn", "max_tokens", "stop_sequence", "tool_use"
            - usage: Token usage statistics (dict) with keys:
                    - inputTokens: Number of input tokens consumed
                    - outputTokens: Number of output tokens generated
                    - totalTokens: Total tokens used
            - toolCalls: List of tool call requests if stopReason is "tool_use" (optional)
        
        Raises:
            Exception: If the Bedrock API call fails, with descriptive error message
        
        Example:
            >>> client = ShelloBedrockClient(model="anthropic.claude-3-sonnet-20240229-v1:0")
            >>> messages = [
            ...     {"role": "system", "content": "You are a helpful assistant."},
            ...     {"role": "user", "content": "What is 2+2?"}
            ... ]
            >>> response = client.chat(messages)
            >>> print(response['content'])
            "2 + 2 equals 4."
        """
        # Format messages for Bedrock (extracts system messages)
        bedrock_messages, system_prompts = self._format_messages(messages)
        
        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            'modelId': self._model,
            'messages': bedrock_messages
        }
        
        # Add system prompts if present
        if system_prompts:
            request_params['system'] = system_prompts
        
        # Add tools if provided
        if tools:
            tool_config = self._format_tools(tools)
            request_params['toolConfig'] = tool_config
        
        # Add default inference configuration
        request_params['inferenceConfig'] = {
            'maxTokens': 4096,
            'temperature': 0.7
        }
        
        # Log request if debug is enabled
        if self._debug:
            self._log_request(self._model, bedrock_messages, tool_config if tools else None)
        
        try:
            # Call the Bedrock Converse API
            response = self._client.converse(**request_params)
            
            # Parse and return the response
            parsed_response = self._parse_response(response)
            
            # Log response if debug is enabled
            if self._debug:
                self._log_response(parsed_response)
            
            return parsed_response
        
        except ClientError as e:
            # Extract error details
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Handle specific AWS Bedrock error types
            if error_code == 'ValidationException':
                # Check if this is a context window error
                if 'too long' in error_message.lower() or 'context' in error_message.lower() or 'token' in error_message.lower():
                    raise Exception(
                        f"Bedrock API error: ValidationException - Context window exceeded. "
                        f"The input is too long for the model's context window. "
                        f"Please reduce the message history or input size. "
                        f"Details: {error_message}"
                    ) from e
                else:
                    raise Exception(
                        f"Bedrock API error: ValidationException - Invalid request parameters. "
                        f"Details: {error_message}"
                    ) from e
            
            elif error_code == 'ThrottlingException':
                raise Exception(
                    f"Bedrock API error: ThrottlingException - Rate limit exceeded. "
                    f"Too many requests have been made. Please wait and retry. "
                    f"Details: {error_message}"
                ) from e
            
            elif error_code == 'AccessDeniedException':
                raise Exception(
                    f"Bedrock API error: AccessDeniedException - Access denied. "
                    f"Check your AWS credentials and IAM permissions for Bedrock. "
                    f"Required permissions: bedrock:InvokeModel. "
                    f"Details: {error_message}"
                ) from e
            
            elif error_code == 'ModelNotReadyException':
                raise Exception(
                    f"Bedrock API error: ModelNotReadyException - Model is not ready. "
                    f"The model is still loading. Please wait a moment and retry. "
                    f"Details: {error_message}"
                ) from e
            
            elif error_code == 'ResourceNotFoundException':
                raise Exception(
                    f"Bedrock API error: ResourceNotFoundException - Model not found. "
                    f"The specified model '{self._model}' does not exist or is not available in region '{self._region}'. "
                    f"Details: {error_message}"
                ) from e
            
            elif error_code == 'ModelTimeoutException':
                raise Exception(
                    f"Bedrock API error: ModelTimeoutException - Model timeout. "
                    f"The model took too long to respond. Try reducing the input size or retry. "
                    f"Details: {error_message}"
                ) from e
            
            else:
                # Unknown error - wrap with descriptive message
                raise Exception(
                    f"Bedrock API error: {error_code} - {error_message}"
                ) from e
        
        except Exception as e:
            # Handle any other unexpected errors
            # Check if it's already a wrapped exception
            if "Bedrock API error:" in str(e):
                raise
            else:
                raise Exception(f"Bedrock API error: Unexpected error - {str(e)}") from e
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Bedrock Converse API response to standard format.
        
        This method transforms the Bedrock response format into a consistent format
        that matches the interface expected by the Shello agent and message processor.
        
        Args:
            response: Raw response dictionary from Bedrock Converse API
        
        Returns:
            Dictionary with standardized response format containing:
            - content: Text content from the assistant (empty string if tool use)
            - role: Always "assistant"
            - stopReason: Reason the model stopped generating
            - usage: Token usage statistics
            - toolCalls: List of tool calls if stopReason is "tool_use" (optional)
        
        Example Bedrock Response:
            {
                'output': {
                    'message': {
                        'role': 'assistant',
                        'content': [{'text': 'Hello!'}]
                    }
                },
                'stopReason': 'end_turn',
                'usage': {
                    'inputTokens': 10,
                    'outputTokens': 5,
                    'totalTokens': 15
                }
            }
        
        Example Parsed Response:
            {
                'content': 'Hello!',
                'role': 'assistant',
                'stopReason': 'end_turn',
                'usage': {
                    'inputTokens': 10,
                    'outputTokens': 5,
                    'totalTokens': 15
                }
            }
        """
        import json
        
        # Extract the message from the response
        output_message = response.get('output', {}).get('message', {})
        content_blocks = output_message.get('content', [])
        role = output_message.get('role', 'assistant')
        stop_reason = response.get('stopReason', 'end_turn')
        usage = response.get('usage', {})
        
        # Initialize result
        result: Dict[str, Any] = {
            'content': '',
            'role': role,
            'stopReason': stop_reason,
            'usage': usage
        }
        
        # Extract content and tool calls from content blocks
        tool_calls = []
        text_parts = []
        
        for block in content_blocks:
            # Handle text content
            if 'text' in block:
                text_parts.append(block['text'])
            
            # Handle tool use
            elif 'toolUse' in block:
                tool_use = block['toolUse']
                tool_call = {
                    'id': tool_use.get('toolUseId', ''),
                    'type': 'function',
                    'function': {
                        'name': tool_use.get('name', ''),
                        'arguments': json.dumps(tool_use.get('input', {}))
                    }
                }
                tool_calls.append(tool_call)
        
        # Combine text parts
        result['content'] = ''.join(text_parts)
        
        # Add tool calls if present
        if tool_calls:
            result['toolCalls'] = tool_calls
        
        return result
    
    def _log_request(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]]
    ) -> None:
        """Log request details for debugging.
        
        This method logs the details of a Bedrock API request when debug mode is enabled.
        The output format is similar to the OpenAI client for consistency.
        
        Args:
            model: The model identifier being used
            messages: List of messages in Bedrock format (after conversion)
            tools: Optional list of tools in Bedrock format (after conversion)
        """
        if not self._debug:
            return
        
        print("\n" + "="*80)
        print("🔵 BEDROCK API REQUEST")
        print("="*80)
        print(f"Model: {model}")
        print(f"Region: {self._region}")
        
        # Show messages summary
        print(f"\n📨 Messages ({len(messages)}):")
        for i, msg in enumerate(messages, 1):
            role = msg.get('role', 'unknown')
            content_blocks = msg.get('content', [])
            
            print(f"\n  [{i}] Role: {role.upper()}")
            print(f"  {'─' * 76}")
            
            # Separate content blocks by type
            text_blocks = []
            tool_use_blocks = []
            tool_result_blocks = []
            
            for block in content_blocks:
                if 'text' in block:
                    text_blocks.append(block)
                elif 'toolUse' in block:
                    tool_use_blocks.append(block)
                elif 'toolResult' in block:
                    tool_result_blocks.append(block)
            
            # Show TEXT CONTENT FIRST (if present)
            has_text = len(text_blocks) > 0
            if has_text:
                for block in text_blocks:
                    text = block['text']
                    # For system messages, show only first line
                    if role.lower() == 'system':
                        first_line = text.split('\n')[0]
                        print(f"  {first_line}")
                        print(f"  ... (system prompt truncated)")
                    else:
                        lines = text.split('\n')
                        for line in lines[:50]:  # Limit to first 50 lines
                            print(f"  {line}")
                        if len(lines) > 50:
                            print(f"  ... ({len(lines) - 50} more lines)")
            
            # Show TOOL USE AFTER content (if present)
            if tool_use_blocks:
                # Add visual separator if there was text before
                if has_text:
                    print(f"\n  {'─' * 76}")
                
                print(f"  🔧 Tool Calls: {len(tool_use_blocks)}")
                for block in tool_use_blocks:
                    tool_use = block['toolUse']
                    print(f"\n    • Function: {tool_use.get('name', 'unknown')}")
                    print(f"      Tool Use ID: {tool_use.get('toolUseId', 'unknown')}")
                    print(f"      Input:")
                    
                    # Pretty print the input
                    import json
                    try:
                        input_obj = tool_use.get('input', {})
                        input_str = json.dumps(input_obj, indent=8)
                        for line in input_str.split('\n'):
                            print(f"      {line}")
                    except:
                        print(f"        {tool_use.get('input', {})}")
            
            # Show TOOL RESULTS (if present)
            if tool_result_blocks:
                for block in tool_result_blocks:
                    tool_result = block['toolResult']
                    print(f"  🔧 Tool Result for ID: {tool_result.get('toolUseId', 'unknown')}")
                    result_content = tool_result.get('content', [])
                    for result_block in result_content:
                        if 'text' in result_block:
                            text = result_block['text']
                            lines = text.split('\n')
                            for line in lines[:20]:  # Limit tool results
                                print(f"  {line}")
                            if len(lines) > 20:
                                print(f"  ... ({len(lines) - 20} more lines)")
            
            # Show status if no content at all
            if not has_text and not tool_use_blocks and not tool_result_blocks:
                print(f"  <no content>")
        
        # Show tools summary
        if tools:
            tool_list = tools.get('tools', [])
            print(f"\n🛠️  Tools ({len(tool_list)}):")
            for tool in tool_list:
                tool_spec = tool.get('toolSpec', {})
                name = tool_spec.get('name', 'unknown')
                desc = tool_spec.get('description', 'No description')
                print(f"  • {name}")
                # Show first line of description
                desc_line = desc.split('\n')[0][:70]
                print(f"    {desc_line}")
        
        print("="*80 + "\n")
    
    def _log_response(
        self,
        response: Dict[str, Any]
    ) -> None:
        """Log response details for debugging.
        
        This method logs the details of a Bedrock API response when debug mode is enabled.
        The output format is similar to the OpenAI client for consistency.
        
        Args:
            response: The parsed response dictionary from Bedrock
        """
        if not self._debug:
            return
        
        print("\n" + "="*80)
        print("🟢 BEDROCK API RESPONSE")
        print("="*80)
        print(f"Status: Success")
        print(f"Model: {self._model}")
        
        # Show usage statistics
        usage = response.get('usage', {})
        if usage:
            print(f"Usage:")
            print(f"  Input tokens: {usage.get('inputTokens', 0)}")
            print(f"  Output tokens: {usage.get('outputTokens', 0)}")
            print(f"  Total tokens: {usage.get('totalTokens', 0)}")
        
        # Show stop reason
        stop_reason = response.get('stopReason', 'unknown')
        print(f"\nStop Reason: {stop_reason}")
        
        # Check if both content and tool_calls are present
        content = response.get('content', '')
        tool_calls = response.get('toolCalls', [])
        has_content = content and isinstance(content, str)
        has_tool_calls = tool_calls and len(tool_calls) > 0
        
        if has_content and has_tool_calls:
            print(f"✨ BOTH content AND tool_calls present!")
        
        # Show content preview
        if has_content:
            preview = content[:100].replace('\n', ' ')
            if len(content) > 100:
                preview += "..."
            print(f"Content: {preview}")
        
        # Show tool calls if present
        if has_tool_calls:
            print(f"\nTool Calls: {len(tool_calls)}")
            for tc in tool_calls:
                func = tc.get('function', {})
                print(f"  - {func.get('name', 'unknown')}")
                print(f"    ID: {tc.get('id', 'unknown')}")
        
        print("="*80 + "\n")
    
    def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Any]] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream chat completion response chunks as they arrive.
        
        This method calls the AWS Bedrock ConverseStream API to generate a streaming
        chat completion. It handles message format conversion, tool configuration,
        and yields response chunks in a format compatible with the OpenAI streaming API.
        
        The method processes various stream events from Bedrock and converts them to
        a consistent chunk format that the message processor expects.
        
        Args:
            messages: List of message dictionaries in OpenAI format with role and content.
                     System messages are automatically extracted and passed separately.
            tools: Optional list of ShelloTool objects or tool dictionaries for function calling
        
        Yields:
            Dictionary chunks in OpenAI-compatible format with the following structure:
            - Text chunks: {"choices": [{"delta": {"content": "text"}}]}
            - Tool use chunks: {"choices": [{"delta": {"tool_calls": [...]}}]}
            - Finish chunks: {"choices": [{"finish_reason": "stop"}]}
            
            Stream event types from Bedrock:
            - contentBlockDelta: Contains text or tool input deltas
            - contentBlockStart: Signals start of a tool use block
            - metadata: Contains token usage statistics
            - messageStop: Signals end of message with stop reason
        
        Raises:
            Exception: If the Bedrock API call fails, yields error chunk and returns
        
        Example:
            >>> client = ShelloBedrockClient(model="anthropic.claude-3-sonnet-20240229-v1:0")
            >>> messages = [{"role": "user", "content": "Count to 3"}]
            >>> for chunk in client.chat_stream(messages):
            ...     if "choices" in chunk:
            ...         delta = chunk["choices"][0].get("delta", {})
            ...         if "content" in delta:
            ...             print(delta["content"], end="", flush=True)
            1, 2, 3
        """
        import json
        
        # Format messages for Bedrock (extracts system messages)
        bedrock_messages, system_prompts = self._format_messages(messages)
        
        # Prepare the request parameters
        request_params: Dict[str, Any] = {
            'modelId': self._model,
            'messages': bedrock_messages
        }
        
        # Add system prompts if present
        if system_prompts:
            request_params['system'] = system_prompts
        
        # Add tools if provided
        if tools:
            tool_config = self._format_tools(tools)
            request_params['toolConfig'] = tool_config
        
        # Add default inference configuration
        request_params['inferenceConfig'] = {
            'maxTokens': 4096,
            'temperature': 0.7
        }
        
        # Log request if debug is enabled
        if self._debug:
            self._log_request(self._model, bedrock_messages, tool_config if tools else None)
            print("🔵 BEDROCK API REQUEST (STREAMING)")
            print("Note: Response chunks will be processed by the stream iterator")
            print("="*80 + "\n")
        
        try:
            # Call the Bedrock ConverseStream API
            response = self._client.converse_stream(**request_params)
            
            # Track tool calls being accumulated
            tool_call_accumulator: Dict[int, Dict[str, Any]] = {}
            current_tool_index = -1
            
            # Process the stream events
            for event in response.get('stream', []):
                # Handle contentBlockStart - signals start of a content block (text or tool use)
                if 'contentBlockStart' in event:
                    block_start = event['contentBlockStart']
                    start_data = block_start.get('start', {})
                    
                    # Check if this is a tool use block
                    if 'toolUse' in start_data:
                        tool_use = start_data['toolUse']
                        current_tool_index += 1
                        
                        # Initialize tool call accumulator
                        tool_call_accumulator[current_tool_index] = {
                            'id': tool_use.get('toolUseId', ''),
                            'type': 'function',
                            'function': {
                                'name': tool_use.get('name', ''),
                                'arguments': ''
                            }
                        }
                        
                        # Yield initial tool call chunk with id and name
                        yield {
                            'choices': [{
                                'delta': {
                                    'tool_calls': [{
                                        'index': current_tool_index,
                                        'id': tool_use.get('toolUseId', ''),
                                        'type': 'function',
                                        'function': {
                                            'name': tool_use.get('name', ''),
                                            'arguments': ''
                                        }
                                    }]
                                }
                            }]
                        }
                
                # Handle contentBlockDelta - contains text or tool input chunks
                elif 'contentBlockDelta' in event:
                    delta = event['contentBlockDelta'].get('delta', {})
                    
                    # Handle text delta
                    if 'text' in delta:
                        text_chunk = delta['text']
                        yield {
                            'choices': [{
                                'delta': {
                                    'content': text_chunk
                                }
                            }]
                        }
                    
                    # Handle tool use input delta
                    elif 'toolUse' in delta:
                        tool_use_delta = delta['toolUse']
                        input_chunk = tool_use_delta.get('input', '')
                        
                        # Accumulate the input
                        if current_tool_index >= 0 and current_tool_index in tool_call_accumulator:
                            tool_call_accumulator[current_tool_index]['function']['arguments'] += input_chunk
                            
                            # Yield tool call delta with arguments
                            yield {
                                'choices': [{
                                    'delta': {
                                        'tool_calls': [{
                                            'index': current_tool_index,
                                            'function': {
                                                'arguments': input_chunk
                                            }
                                        }]
                                    }
                                }]
                            }
                
                # Handle metadata - contains token usage
                elif 'metadata' in event:
                    usage = event['metadata'].get('usage', {})
                    # Store usage for potential later use, but don't yield yet
                    # The message processor doesn't expect usage in streaming chunks
                    pass
                
                # Handle messageStop - signals end of message
                elif 'messageStop' in event:
                    stop_reason = event['messageStop'].get('stopReason', 'end_turn')
                    
                    # Map Bedrock stop reasons to OpenAI finish reasons
                    finish_reason_map = {
                        'end_turn': 'stop',
                        'max_tokens': 'length',
                        'stop_sequence': 'stop',
                        'tool_use': 'tool_calls',
                        'content_filtered': 'content_filter'
                    }
                    
                    finish_reason = finish_reason_map.get(stop_reason, 'stop')
                    
                    # Yield finish chunk
                    yield {
                        'choices': [{
                            'finish_reason': finish_reason,
                            'delta': {}
                        }]
                    }
        
        except ClientError as e:
            # Extract error details
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Handle specific AWS Bedrock error types
            error_text = ""
            
            if error_code == 'ValidationException':
                # Check if this is a context window error
                if 'too long' in error_message.lower() or 'context' in error_message.lower() or 'token' in error_message.lower():
                    error_text = (
                        f"ValidationException - Context window exceeded. "
                        f"The input is too long for the model's context window. "
                        f"Please reduce the message history or input size. "
                        f"Details: {error_message}"
                    )
                else:
                    error_text = (
                        f"ValidationException - Invalid request parameters. "
                        f"Details: {error_message}"
                    )
            
            elif error_code == 'ThrottlingException':
                error_text = (
                    f"ThrottlingException - Rate limit exceeded. "
                    f"Too many requests have been made. Please wait and retry. "
                    f"Details: {error_message}"
                )
            
            elif error_code == 'AccessDeniedException':
                error_text = (
                    f"AccessDeniedException - Access denied. "
                    f"Check your AWS credentials and IAM permissions for Bedrock. "
                    f"Required permissions: bedrock:InvokeModel. "
                    f"Details: {error_message}"
                )
            
            elif error_code == 'ModelNotReadyException':
                error_text = (
                    f"ModelNotReadyException - Model is not ready. "
                    f"The model is still loading. Please wait a moment and retry. "
                    f"Details: {error_message}"
                )
            
            elif error_code == 'ResourceNotFoundException':
                error_text = (
                    f"ResourceNotFoundException - Model not found. "
                    f"The specified model '{self._model}' does not exist or is not available in region '{self._region}'. "
                    f"Details: {error_message}"
                )
            
            elif error_code == 'ModelTimeoutException':
                error_text = (
                    f"ModelTimeoutException - Model timeout. "
                    f"The model took too long to respond. Try reducing the input size or retry. "
                    f"Details: {error_message}"
                )
            
            else:
                # Unknown error - wrap with descriptive message
                error_text = f"{error_code} - {error_message}"
            
            # Yield error chunk in a format the message processor can handle
            yield {
                'choices': [{
                    'delta': {
                        'content': f"\n\nError: Bedrock API error: {error_text}\n"
                    }
                }]
            }
            return
        
        except Exception as e:
            # Handle any other unexpected errors
            error_text = str(e)
            
            # Check if it's already a wrapped exception
            if "Bedrock API error:" not in error_text:
                error_text = f"Unexpected error - {error_text}"
            
            yield {
                'choices': [{
                    'delta': {
                        'content': f"\n\nError: {error_text}\n"
                    }
                }]
            }
            return
