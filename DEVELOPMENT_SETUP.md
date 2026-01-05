# Shello CLI Development Setup Guide

This guide is for developers who want to contribute to or modify Shello CLI.

## Quick Start for Users

If you just want to use Shello CLI, see [README.md](README.md) for installation instructions.

## CLI Commands

### User Commands
- `shello` or `shello chat` - Start interactive chat session
- `shello setup` - Interactive configuration wizard
- `shello config` - Display current configuration
- `shello config --edit` - Open settings in default editor
- `shello config get <key>` - Get specific setting value
- `shello config set <key> <value>` - Set specific setting value
- `shello config reset` - Reset settings to defaults
- `shello --version` - Show version information
- `shello --help` - Show help message

### Development Commands
```bash
python main.py setup   # Interactive configuration wizard
python main.py chat    # Start chat session
python main.py config  # Show current configuration
```

### In-Chat Commands
- `/new` - Start a new conversation
- `/switch` - Switch between AI providers (OpenAI, Bedrock, etc.)
- `/help` - Show available commands
- `/about` - Show about information
- `/quit` or `/exit` - Exit the application

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/om-mapari/shello-cli.git
cd shello-cli
pip install -r requirements.txt
```

### 2. Configure for Development

**Option A: Interactive Setup (Recommended)**
```bash
python main.py setup
```

The setup wizard will guide you through:
- AI provider selection (OpenAI-compatible API or AWS Bedrock)
- Provider-specific configuration (API keys or AWS credentials)
- Default model selection

**Option B: Manual Configuration**

**For OpenAI-compatible APIs:**

Create `~/.shello_cli/user-settings.yml`:
```yaml
# =============================================================================
# SHELLO CLI USER SETTINGS
# =============================================================================
provider: openai

openai_config:
  provider_type: openai
  api_key: your-api-key-here
  base_url: https://api.openai.com/v1
  default_model: gpt-4o
  models:
    - gpt-4o
    - gpt-4o-mini
    - gpt-4-turbo
```

**For AWS Bedrock:**

Create `~/.shello_cli/user-settings.yml`:
```yaml
provider: bedrock

bedrock_config:
  provider_type: bedrock
  aws_region: us-east-1
  aws_profile: default
  default_model: anthropic.claude-3-5-sonnet-20241022-v2:0
  models:
    - anthropic.claude-3-5-sonnet-20241022-v2:0
    - anthropic.claude-3-opus-20240229-v1:0
    - amazon.nova-pro-v1:0
```

**For multiple providers:**

```yaml
provider: openai

openai_config:
  provider_type: openai
  api_key: your-openai-key
  base_url: https://api.openai.com/v1
  default_model: gpt-4o
  models:
    - gpt-4o
    - gpt-4o-mini

bedrock_config:
  provider_type: bedrock
  aws_region: us-east-1
  aws_profile: default
  default_model: anthropic.claude-3-5-sonnet-20241022-v2:0
  models:
    - anthropic.claude-3-5-sonnet-20241022-v2:0
```

**Option C: Environment Variables**

**OpenAI-compatible:**
```bash
export OPENAI_API_KEY="your-api-key"
```

**AWS Bedrock:**
```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="default"
# Or use explicit credentials:
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

### 3. Test Your Setup

```bash
python main.py config
```

## Configuration Files

### 1. User Settings (Global)

**Location:** `~/.shello_cli/user-settings.yml`

Contains AI provider configuration, credentials, and default preferences. The file uses YAML format with helpful comments and documentation.

**OpenAI-compatible API configuration:**

```yaml
# =============================================================================
# SHELLO CLI USER SETTINGS
# =============================================================================
# Edit this file to customize your settings.
# Only specify values you want to override - defaults are used for the rest.

# =============================================================================
# PROVIDER CONFIGURATION
# =============================================================================
provider: openai

openai_config:
  provider_type: openai
  api_key: your-api-key-here  # Or use OPENAI_API_KEY env var
  base_url: https://api.openai.com/v1
  default_model: gpt-4o
  models:
    - gpt-4o
    - gpt-4o-mini
    - gpt-4-turbo

# =============================================================================
# OUTPUT MANAGEMENT (optional - uses defaults if not specified)
# =============================================================================
# Controls how command output is truncated and displayed.
# Uncomment and modify to customize:
#
# output_management:
#   enabled: true
#   show_summary: true
#   limits:
#     list: 5000
#     search: 10000
#     log: 15000
#     json: 20000
#     default: 8000
#   strategies:
#     list: first_only
#     search: first_only
#     log: last_only
#     default: first_last

# =============================================================================
# COMMAND TRUST (optional - uses defaults if not specified)
# =============================================================================
# Controls which commands require approval before execution.
# Uncomment and modify to customize:
#
# command_trust:
#   enabled: true
#   yolo_mode: false
#   approval_mode: user_driven
#   allowlist:
#     - ls
#     - pwd
#     - git status
```

**AWS Bedrock configuration:**

```yaml
provider: bedrock

bedrock_config:
  provider_type: bedrock
  aws_region: us-east-1
  aws_profile: default
  default_model: anthropic.claude-3-5-sonnet-20241022-v2:0
  models:
    - anthropic.claude-3-5-sonnet-20241022-v2:0
    - anthropic.claude-3-opus-20240229-v1:0
    - amazon.nova-pro-v1:0
```

**Multiple providers configured:**

```yaml
provider: openai

openai_config:
  provider_type: openai
  api_key: your-openai-key
  base_url: https://api.openai.com/v1
  default_model: gpt-4o
  models:
    - gpt-4o
    - gpt-4o-mini

bedrock_config:
  provider_type: bedrock
  aws_region: us-east-1
  aws_profile: default
  default_model: anthropic.claude-3-5-sonnet-20241022-v2:0
  models:
    - anthropic.claude-3-5-sonnet-20241022-v2:0
```

**Key features:**
- YAML format with inline documentation
- Only configured values are saved (everything else uses defaults)
- All optional settings shown as comments with examples
- Environment variables can override any credential

**Note:** Credentials can also be set via environment variables:
- OpenAI: `OPENAI_API_KEY`
- Bedrock: `AWS_REGION`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

### 2. Project Settings (Local)

**Location:** `.shello/settings.json` (in your project directory)

Contains project-specific overrides:

```json
{
    "model": "gpt-4o-mini"
}
```

### 3. Custom Instructions

**Location:** `.shello/SHELLO.md` (in your project directory)

Add project-specific context for the AI:

```markdown
# Custom Instructions for My Project

When working in this project:
- This is a Python project using pytest for testing
- Always run tests after making changes
- Use type hints in all code
- Follow PEP 8 style guidelines
```

### 4. Output Management Configuration

Output management settings can be customized in your user settings file. Default values are defined in `shello_cli/defaults.py`:

```python
# Character limits per output type
DEFAULT_CHAR_LIMITS = {
    "list": 5_000,       # ~1.2K tokens
    "search": 10_000,    # ~2.5K tokens
    "log": 15_000,       # ~3.7K tokens
    "json": 20_000,      # ~5K tokens
    "install": 8_000,    # ~2K tokens
    "build": 8_000,      # ~2K tokens
    "test": 15_000,      # ~3.7K tokens
    "default": 8_000,    # ~2K tokens
    "safety": 50_000,    # ~12.5K tokens (hard max)
}

# Truncation strategies
DEFAULT_STRATEGIES = {
    "list": "first_only",
    "search": "first_only",
    "log": "last_only",
    "json": "first_only",
    "install": "first_last",
    "build": "first_last",
    "test": "first_last",
    "default": "first_last",
}

# Cache settings
DEFAULT_CACHE_MAX_SIZE_MB = 100  # 100MB, no TTL
```

To customize these settings, add an `output_management` section to your `~/.shello_cli/user-settings.yml`:

```yaml
output_management:
  enabled: true
  show_summary: true
  limits:
    list: 5000
    search: 10000
    default: 8000
  strategies:
    list: first_only
    log: last_only
    default: first_last
```

## Configuration Hierarchy

Settings are loaded in this order (later overrides earlier):
1. Default values (in `shello_cli/defaults.py`)
2. User settings (`~/.shello_cli/user-settings.yml`)
3. Environment variables (`OPENAI_API_KEY`, `AWS_REGION`, `AWS_PROFILE`, etc.)
4. Project settings (`.shello/settings.json`)

**Note:** The settings system uses a merge strategy where:
- Only values you explicitly set in `user-settings.yml` override defaults
- Unspecified values automatically use defaults from `defaults.py`
- The denylist is always additive (your patterns are added to defaults for safety)

## Testing

### Run all tests:
```bash
pytest tests/ -v
```

### Run only property-based tests:
```bash
pytest tests/ -v -k "property"
```

### Run specific test file:
```bash
pytest tests/test_openai_client.py -v
```

### Run with coverage:
```bash
pytest tests/ --cov=shello_cli --cov-report=html
```

## Supported Models

The client supports any OpenAI-compatible API endpoint and AWS Bedrock foundation models.

## AI Providers

### OpenAI
```json
{
    "provider": "openai",
    "openai_config": {
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-...",
        "default_model": "gpt-4o",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"]
    }
}
```

### OpenRouter (Recommended for Free Models)
```json
{
    "provider": "openai",
    "openai_config": {
        "provider_type": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": "sk-or-v1-...",
        "default_model": "mistralai/devstral-2512:free",
        "models": ["mistralai/devstral-2512:free", "anthropic/claude-3.5-sonnet"]
    }
}
```

### AWS Bedrock
```json
{
    "provider": "bedrock",
    "bedrock_config": {
        "provider_type": "bedrock",
        "aws_region": "us-east-1",
        "aws_profile": "default",
        "default_model": "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "models": [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "anthropic.claude-3-opus-20240229-v1:0",
            "amazon.nova-pro-v1:0"
        ]
    }
}
```

See [doc/BEDROCK_SETUP_GUIDE.md](doc/BEDROCK_SETUP_GUIDE.md) for detailed AWS Bedrock setup instructions.

### Local Models (LM Studio, Ollama)
```json
{
    "provider": "openai",
    "openai_config": {
        "provider_type": "openai",
        "base_url": "http://localhost:1234/v1",
        "api_key": "not-needed",
        "default_model": "local-model-name",
        "models": ["local-model-name"]
    }
}
```

## Security

### File Permissions

The settings manager automatically sets secure file permissions (0600) on user settings files to protect your API keys.

**On Unix-like systems:**
```bash
chmod 600 ~/.shello_cli/user-settings.json
```

**On Windows:**
File permissions are handled automatically by the application.

## Troubleshooting

### "No API key found" error
1. Run `python main.py setup` to configure interactively
2. Or check that `~/.shello_cli/user-settings.yml` exists and contains provider configuration
3. Or set environment variables:
   - OpenAI: `OPENAI_API_KEY`
   - Bedrock: `AWS_REGION`, `AWS_PROFILE`, or `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY`

### "Failed to initialize agent" error
- Verify your credentials are valid
- For OpenAI: Check that the `api_key` and `base_url` are correct
- For Bedrock: Verify AWS credentials and region are configured
- Ensure you have internet connectivity
- Verify the model name is supported by your provider

### "boto3 not installed" error (Bedrock only)
If you're using AWS Bedrock and see this error:
```bash
pip install boto3
```

Or reinstall all dependencies:
```bash
pip install -r requirements.txt
```

### Import errors
- Make sure you've installed all dependencies: `pip install -r requirements.txt`
- Verify you're in the correct Python environment (check with `which python` or `where python`)

### Configuration not loading
- Check file locations:
  - User: `~/.shello_cli/user-settings.yml`
  - Project: `.shello/settings.json`
- Verify YAML syntax is valid (use a YAML validator)
- Check file permissions (should be readable, automatically set to 0600 for security)

### View current configuration
```bash
python main.py config
```

## Development

### Project Structure
```
shello_cli/
├── agent/
│   ├── message_processor.py     # Message processing logic
│   ├── shello_agent.py          # Main agent logic
│   ├── template.py              # System prompt template
│   └── tool_executor.py         # Tool execution
├── api/
│   ├── bedrock_client.py        # AWS Bedrock API client
│   ├── client_factory.py        # Client factory (creates appropriate client)
│   └── openai_client.py         # OpenAI-compatible API client
├── chat/
│   └── chat_session.py          # Chat session management
├── commands/
│   ├── command_detector.py      # Direct command detection
│   ├── context_manager.py       # Command history tracking
│   ├── direct_executor.py       # Direct command execution
│   └── settings_commands.py     # Settings management commands
├── settings/
│   ├── __init__.py              # Public API
│   ├── manager.py               # SettingsManager class
│   ├── models.py                # Settings dataclasses
│   └── serializers.py           # YAML generation with comments
├── tools/
│   ├── bash_tool.py             # Bash command execution
│   ├── get_cached_output_tool.py # Cache retrieval tool
│   └── output/                  # Output management system
│       ├── cache.py             # Output caching
│       ├── compressor.py        # Progress bar compression
│       ├── manager.py           # Output manager
│       ├── semantic.py          # Semantic line analysis
│       ├── truncator.py         # Smart truncation
│       └── type_detector.py     # Output type detection
├── ui/
│   ├── ui_renderer.py           # Terminal UI rendering
│   └── user_input.py            # User input handling
├── utils/
│   ├── output_utils.py          # Output utility functions
│   └── settings_manager.py      # Configuration management (re-exports from settings/)
├── cli.py                       # CLI entry point
├── defaults.py                  # Default values for user-changeable settings
├── patterns.py                  # Internal patterns and templates (NOT user-changeable)
└── types.py                     # Type definitions

tests/
├── test_*.py                    # Unit tests
└── ...                          # 1,400+ tests total
```

### Running the Application

**From source:**
```bash
python main.py
```

**With specific command:**
```bash
python main.py setup   # Run setup wizard
python main.py config  # Show configuration
python main.py chat    # Start chat session
```

### Adding New Models

Edit your user settings file to add new models to your configured provider:

**For OpenAI-compatible APIs:**
```json
{
    "provider": "openai",
    "openai_config": {
        "models": [
            "gpt-4o",
            "gpt-4o-mini",
            "your-new-model"
        ],
        "default_model": "your-new-model"
    }
}
```

**For AWS Bedrock:**
```json
{
    "provider": "bedrock",
    "bedrock_config": {
        "models": [
            "anthropic.claude-3-5-sonnet-20241022-v2:0",
            "your-new-bedrock-model-id"
        ],
        "default_model": "your-new-bedrock-model-id"
    }
}
```

Or use `python main.py setup` to reconfigure interactively.

### Running Property-Based Tests

Property-based tests use Hypothesis to generate test cases:

```bash
# Run with verbose output
pytest tests/test_output_cache.py -v -s

# Increase number of examples
pytest tests/ --hypothesis-show-statistics
```

## Building Executables

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for creating standalone executables.

**Quick build:**
```bash
# Windows
build.bat

# Linux/macOS
chmod +x build.sh && ./build.sh
```

## Additional Resources

- [README.md](README.md) - Main documentation
- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [docs/HOW_TO_RELEASE.md](docs/HOW_TO_RELEASE.md) - Release process
- [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) - Build process details
