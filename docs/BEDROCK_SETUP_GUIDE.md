# AWS Bedrock Setup Guide for Shello CLI

This guide walks you through setting up AWS Bedrock to use with Shello CLI, enabling you to use Claude, Nova, and other foundation models available on AWS Bedrock.

## Table of Contents

- [Prerequisites](#prerequisites)
- [AWS Account Setup](#aws-account-setup)
- [Model Access](#model-access)
- [Authentication Methods](#authentication-methods)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)
- [Available Models](#available-models)

---

## Prerequisites

Before you begin, ensure you have:

1. **AWS Account** - An active AWS account with billing enabled
2. **Shello CLI** - Installed and working (see main [README.md](../README.md))
3. **AWS CLI** (optional but recommended) - For easier credential management

---

## AWS Account Setup

### Step 1: Create an AWS Account

If you don't have an AWS account:

1. Go to [aws.amazon.com](https://aws.amazon.com)
2. Click "Create an AWS Account"
3. Follow the registration process
4. Add a payment method (required for Bedrock access)

### Step 2: Enable AWS Bedrock

AWS Bedrock is available in specific regions. Recommended regions:

- **us-east-1** (US East - N. Virginia) - Most models available
- **us-west-2** (US West - Oregon) - Good alternative
- **eu-west-1** (Europe - Ireland) - For EU users
- **ap-southeast-1** (Asia Pacific - Singapore) - For APAC users

**Note:** Not all models are available in all regions. Check the [AWS Bedrock documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html) for model availability by region.

### Step 3: Request Model Access

1. Sign in to the [AWS Console](https://console.aws.amazon.com)
2. Navigate to **Amazon Bedrock** service
3. In the left sidebar, click **Model access**
4. Click **Manage model access** (or **Request model access**)
5. Select the models you want to use:
   - **Anthropic Claude 3.5 Sonnet** (recommended for general use)
   - **Anthropic Claude 3 Sonnet** (good balance of speed and quality)
   - **Anthropic Claude 3 Haiku** (fastest, most cost-effective)
   - **Amazon Nova Pro** (AWS's own model)
   - **Amazon Nova Lite** (lightweight option)
6. Click **Request model access** or **Save changes**

**Access approval:**
- Most models are approved instantly
- Some models may require a few minutes or business review
- You'll receive an email when access is granted

---

## Authentication Methods

Shello CLI supports multiple AWS authentication methods. Choose the one that fits your workflow.

### Method 1: AWS Profile (Recommended)

This is the most secure and convenient method for local development.

#### Setup AWS Profile

1. **Install AWS CLI** (if not already installed):
   ```bash
   # macOS
   brew install awscli
   
   # Linux
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Windows
   # Download and run: https://awscli.amazonaws.com/AWSCLIV2.msi
   ```

2. **Configure AWS credentials**:
   ```bash
   aws configure
   ```
   
   You'll be prompted for:
   - **AWS Access Key ID**: Get from IAM console
   - **AWS Secret Access Key**: Get from IAM console
   - **Default region**: e.g., `us-east-1`
   - **Default output format**: `json` (recommended)

3. **Verify configuration**:
   ```bash
   aws bedrock list-foundation-models --region us-east-1
   ```

#### Create IAM User for Bedrock

For security, create a dedicated IAM user:

1. Go to **IAM** in AWS Console
2. Click **Users** → **Add users**
3. Enter username (e.g., `shello-bedrock-user`)
4. Select **Access key - Programmatic access**
5. Click **Next: Permissions**
6. Attach policy: **AmazonBedrockFullAccess** (or create custom policy)
7. Click through to **Create user**
8. **Save the Access Key ID and Secret Access Key** (shown only once!)

**Custom IAM Policy (Minimal Permissions):**

If you want to follow the principle of least privilege:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

### Method 2: Environment Variables

Set AWS credentials as environment variables:

**Linux/macOS:**
```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"
```

**Windows (PowerShell):**
```powershell
$env:AWS_ACCESS_KEY_ID="your-access-key-id"
$env:AWS_SECRET_ACCESS_KEY="your-secret-access-key"
$env:AWS_DEFAULT_REGION="us-east-1"
```

**Windows (CMD):**
```cmd
set AWS_ACCESS_KEY_ID=your-access-key-id
set AWS_SECRET_ACCESS_KEY=your-secret-access-key
set AWS_DEFAULT_REGION=us-east-1
```

### Method 3: Explicit Credentials in Code

You can pass credentials directly when initializing the client (not recommended for production):

```python
from shello_cli.api import ShelloBedrockClient

client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1",
    aws_access_key="your-access-key-id",
    aws_secret_key="your-secret-access-key"
)
```

### Method 4: IAM Roles (For EC2/ECS/Lambda)

If running Shello CLI on AWS infrastructure, use IAM roles:

1. Attach an IAM role with Bedrock permissions to your EC2 instance, ECS task, or Lambda function
2. No credentials needed - boto3 will automatically use the instance role
3. Initialize client without credentials:

```python
from shello_cli.api import ShelloBedrockClient

client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"
)
```

---

## Configuration

### Using Bedrock with Shello CLI

Currently, Shello CLI is designed for OpenAI-compatible APIs. To use Bedrock, you'll need to integrate it programmatically or wait for CLI support.

### Programmatic Usage

Here's how to use the Bedrock client in your Python code:

```python
from shello_cli.api import ShelloBedrockClient
from shello_cli.types import ShelloTool

# Initialize client
client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1",
    aws_profile="default",  # Use AWS profile
    debug=True  # Enable debug logging
)

# Simple chat
messages = [
    {"role": "user", "content": "Hello! What can you help me with?"}
]

response = client.chat(messages)
print(response["content"])

# Chat with streaming
for chunk in client.chat_stream(messages):
    if chunk["type"] == "text":
        print(chunk["text"], end="", flush=True)
    elif chunk["type"] == "stop":
        print(f"\n\nStop reason: {chunk['stopReason']}")
    elif chunk["type"] == "usage":
        print(f"Tokens used: {chunk['totalTokens']}")

# Chat with tools (function calling)
tools = [
    ShelloTool(
        type="function",
        function={
            "name": "get_weather",
            "description": "Get current weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name"
                    }
                },
                "required": ["location"]
            }
        }
    )
]

messages = [
    {"role": "user", "content": "What's the weather in San Francisco?"}
]

response = client.chat(messages, tools=tools)

if response.get("toolCalls"):
    for tool_call in response["toolCalls"]:
        print(f"Tool: {tool_call['function']['name']}")
        print(f"Arguments: {tool_call['function']['arguments']}")
```

### Configuration File (Future CLI Support)

When CLI support is added, configuration will look like:

**`~/.shello_cli/user-settings.json`:**
```json
{
  "provider": "bedrock",
  "bedrock": {
    "region": "us-east-1",
    "profile": "default",
    "default_model": "anthropic.claude-3-sonnet-20240229-v1:0",
    "models": [
      "anthropic.claude-3-5-sonnet-20241022-v2:0",
      "anthropic.claude-3-sonnet-20240229-v1:0",
      "anthropic.claude-3-haiku-20240307-v1:0",
      "amazon.nova-pro-v1:0",
      "amazon.nova-lite-v1:0"
    ]
  }
}
```

---

## Usage Examples

### Example 1: Basic Chat

```python
from shello_cli.api import ShelloBedrockClient

client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"
)

messages = [
    {"role": "user", "content": "Explain AWS Bedrock in one sentence."}
]

response = client.chat(messages)
print(response["content"])
# Output: "AWS Bedrock is a fully managed service that provides access to 
# foundation models from leading AI companies through a unified API."
```

### Example 2: Multi-turn Conversation

```python
from shello_cli.api import ShelloBedrockClient

client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"
)

messages = [
    {"role": "user", "content": "What is Python?"},
]

# First response
response = client.chat(messages)
print(f"Assistant: {response['content']}\n")

# Add assistant response to history
messages.append({
    "role": "assistant",
    "content": response["content"]
})

# Continue conversation
messages.append({
    "role": "user",
    "content": "What are its main use cases?"
})

response = client.chat(messages)
print(f"Assistant: {response['content']}")
```

### Example 3: Streaming Response

```python
from shello_cli.api import ShelloBedrockClient

client = ShelloBedrockClient(
    model="anthropic.claude-3-haiku-20240307-v1:0",  # Fast model
    region="us-east-1"
)

messages = [
    {"role": "user", "content": "Write a haiku about coding."}
]

print("Assistant: ", end="", flush=True)

for chunk in client.chat_stream(messages):
    if chunk["type"] == "text":
        print(chunk["text"], end="", flush=True)
    elif chunk["type"] == "stop":
        print(f"\n\n[Stop reason: {chunk['stopReason']}]")
    elif chunk["type"] == "usage":
        print(f"[Tokens: {chunk['totalTokens']}]")
```

### Example 4: Function Calling

```python
from shello_cli.api import ShelloBedrockClient
from shello_cli.types import ShelloTool
import json

client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"
)

# Define a tool
tools = [
    ShelloTool(
        type="function",
        function={
            "name": "execute_bash",
            "description": "Execute a bash command and return the output",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The bash command to execute"
                    }
                },
                "required": ["command"]
            }
        }
    )
]

messages = [
    {"role": "user", "content": "List all Python files in the current directory"}
]

# First request - model will request tool use
response = client.chat(messages, tools=tools)

if response.get("toolCalls"):
    tool_call = response["toolCalls"][0]
    function_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    print(f"Model wants to call: {function_name}")
    print(f"With arguments: {arguments}")
    
    # Simulate tool execution
    tool_result = "main.py\ntest.py\nutils.py"
    
    # Add assistant message with tool call
    messages.append({
        "role": "assistant",
        "content": None,
        "tool_calls": [tool_call]
    })
    
    # Add tool result
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call["id"],
        "content": tool_result
    })
    
    # Get final response
    final_response = client.chat(messages, tools=tools)
    print(f"\nFinal response: {final_response['content']}")
```

### Example 5: Different Models

```python
from shello_cli.api import ShelloBedrockClient

# Claude 3.5 Sonnet - Most capable
client_sonnet = ShelloBedrockClient(
    model="anthropic.claude-3-5-sonnet-20241022-v2:0",
    region="us-east-1"
)

# Claude 3 Haiku - Fastest and cheapest
client_haiku = ShelloBedrockClient(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    region="us-east-1"
)

# Amazon Nova Pro - AWS's model
client_nova = ShelloBedrockClient(
    model="amazon.nova-pro-v1:0",
    region="us-east-1"
)

messages = [{"role": "user", "content": "Hello!"}]

# Use different models for different tasks
response = client_haiku.chat(messages)  # Quick responses
response = client_sonnet.chat(messages)  # Complex reasoning
response = client_nova.chat(messages)  # AWS-optimized
```

---

## Troubleshooting

### Error: "Could not connect to the endpoint URL"

**Cause:** Invalid region or Bedrock not available in that region.

**Solution:**
- Verify the region supports Bedrock: [AWS Bedrock Regions](https://docs.aws.amazon.com/bedrock/latest/userguide/models-regions.html)
- Use a supported region like `us-east-1` or `us-west-2`

```python
client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"  # Use supported region
)
```

### Error: "AccessDeniedException"

**Cause:** Your AWS credentials don't have permission to access Bedrock.

**Solution:**
1. Verify IAM permissions include `bedrock:InvokeModel`
2. Check if you've requested model access in the Bedrock console
3. Ensure your AWS credentials are correctly configured

```bash
# Test AWS credentials
aws sts get-caller-identity

# Test Bedrock access
aws bedrock list-foundation-models --region us-east-1
```

### Error: "ValidationException: Model not found"

**Cause:** Model ID is incorrect or you haven't requested access to that model.

**Solution:**
1. Check model ID format (must include version)
2. Request model access in Bedrock console
3. Verify model is available in your region

**Correct model ID format:**
```python
# ✅ Correct - includes version
model="anthropic.claude-3-sonnet-20240229-v1:0"

# ❌ Wrong - missing version
model="anthropic.claude-3-sonnet"
```

### Error: "ThrottlingException"

**Cause:** You've exceeded the rate limit for API calls.

**Solution:**
- Implement exponential backoff and retry logic
- Request a quota increase in AWS Service Quotas console
- Use a different model with higher limits

### Error: "Context window exceeded"

**Cause:** Your messages are too long for the model's context window.

**Solution:**
- Reduce message history
- Use a model with a larger context window
- Implement message truncation or summarization

```python
# Limit conversation history
messages = messages[-10:]  # Keep only last 10 messages
```

### Debug Mode

Enable debug mode to see detailed request/response logs:

```python
client = ShelloBedrockClient(
    model="anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1",
    debug=True  # Enable debug logging
)
```

---

## Available Models

### Anthropic Claude Models

| Model ID | Description | Context Window | Best For |
|----------|-------------|----------------|----------|
| `anthropic.claude-3-5-sonnet-20241022-v2:0` | Most capable Claude model | 200K tokens | Complex reasoning, coding |
| `anthropic.claude-3-sonnet-20240229-v1:0` | Balanced performance | 200K tokens | General purpose |
| `anthropic.claude-3-haiku-20240307-v1:0` | Fastest, most affordable | 200K tokens | Quick responses, high volume |

### Amazon Nova Models

| Model ID | Description | Context Window | Best For |
|----------|-------------|----------------|----------|
| `amazon.nova-pro-v1:0` | AWS's flagship model | 300K tokens | General purpose, AWS-optimized |
| `amazon.nova-lite-v1:0` | Lightweight model | 300K tokens | Fast responses, cost-effective |

### Other Models

Check the [AWS Bedrock Model Catalog](https://docs.aws.amazon.com/bedrock/latest/userguide/models-supported.html) for:
- Meta Llama models
- Cohere Command models
- AI21 Jurassic models
- Stability AI models (image generation)

### Model Pricing

Pricing varies by model and region. Check current pricing:
- [AWS Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)

**Example pricing (us-east-1, as of 2024):**
- Claude 3.5 Sonnet: $3.00 per 1M input tokens, $15.00 per 1M output tokens
- Claude 3 Haiku: $0.25 per 1M input tokens, $1.25 per 1M output tokens
- Nova Pro: $0.80 per 1M input tokens, $3.20 per 1M output tokens

---

## Best Practices

### 1. Use IAM Roles When Possible

For production deployments on AWS infrastructure, use IAM roles instead of access keys:
- More secure (no credentials to manage)
- Automatic credential rotation
- Fine-grained permissions

### 2. Implement Retry Logic

AWS services can experience transient errors. Implement exponential backoff:

```python
import time
from botocore.exceptions import ClientError

def chat_with_retry(client, messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.chat(messages)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    time.sleep(wait_time)
                    continue
            raise
```

### 3. Monitor Costs

- Set up AWS Budgets to track Bedrock spending
- Use CloudWatch to monitor API usage
- Choose appropriate models for your use case (Haiku for simple tasks, Sonnet for complex ones)

### 4. Handle Streaming Errors

Always handle errors in streaming responses:

```python
try:
    for chunk in client.chat_stream(messages):
        if chunk["type"] == "error":
            print(f"Error: {chunk['error']}")
            break
        elif chunk["type"] == "text":
            print(chunk["text"], end="", flush=True)
except Exception as e:
    print(f"Streaming error: {e}")
```

### 5. Use Appropriate Regions

- Choose regions close to your users for lower latency
- Check model availability in your chosen region
- Consider data residency requirements

---

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [AWS Bedrock API Reference](https://docs.aws.amazon.com/bedrock/latest/APIReference/)
- [Boto3 Bedrock Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html)
- [AWS CLI Configuration](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

---

## Support

If you encounter issues:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review AWS Bedrock service health: [AWS Status](https://status.aws.amazon.com/)
3. Open an issue on [GitHub](https://github.com/om-mapari/shello-cli/issues)
4. Check AWS Support (if you have a support plan)

---

**Happy coding with AWS Bedrock! 🚀**
