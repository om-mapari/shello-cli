# Shello CLI Development Setup Guide

This guide is for developers who want to contribute to or modify Shello CLI.

## Quick Start for Users

If you just want to use Shello CLI, see [README.md](README.md) for installation instructions.

## CLI Commands

### User Commands
- `shello` or `shello chat` - Start interactive chat session
- `shello setup` - Interactive configuration wizard
- `shello config` - Display current configuration
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

**Option B: Manual Configuration**

Create `~/.shello_cli/user-settings.json`:
```json
{
    "api_key": "your-api-key-here",
    "base_url": "https://openrouter.ai/api/v1",
    "default_model": "mistralai/devstral-2512:free",
    "models": [
        "mistralai/devstral-2512:free",
        "gpt-4o",
        "gpt-4o-mini"
    ]
}
```

**Option C: Environment Variable**
```bash
export OPENAI_API_KEY="your-api-key"
```

### 3. Test Your Setup

```bash
python main.py config
```

## Configuration Files

### 1. User Settings (Global)

**Location:** `~/.shello_cli/user-settings.json`

Contains API credentials and default preferences:

```json
{
    "api_key": "your-api-key-here",
    "base_url": "https://openrouter.ai/api/v1",
    "default_model": "mistralai/devstral-2512:free",
    "models": [
        "mistralai/devstral-2512:free",
        "gpt-4o",
        "gpt-4o-mini"
    ]
}
```

**Note:** API key can also be set via `OPENAI_API_KEY` environment variable.

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

Output management settings are defined in `shello_cli/constants.py`:

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

To customize these settings, modify `shello_cli/constants.py` directly.

## Configuration Hierarchy

Settings are loaded in this order (later overrides earlier):
1. Default values (in `shello_cli/constants.py`)
2. User settings (`~/.shello_cli/user-settings.json`)
3. Environment variables (`OPENAI_API_KEY`)
4. Project settings (`.shello/settings.json`)

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

The client supports any OpenAI-compatible API endpoint.

## API Providers

### OpenAI
```json
{
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-...",
    "default_model": "gpt-4o"
}
```

### OpenRouter (Recommended for Free Models)
```json
{
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-v1-...",
    "default_model": "mistralai/devstral-2512:free"
}
```

### Local Models (LM Studio, Ollama)
```json
{
    "base_url": "http://localhost:1234/v1",
    "api_key": "not-needed",
    "default_model": "local-model-name"
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
2. Or check that `~/.shello_cli/user-settings.json` exists and contains `api_key`
3. Or set the `OPENAI_API_KEY` environment variable

### "Failed to initialize agent" error
- Verify your API key is valid
- Check that the `base_url` is correct for your provider
- Ensure you have internet connectivity
- Verify the model name is supported by your provider

### Import errors
- Make sure you've installed all dependencies: `pip install -r requirements.txt`
- Verify you're in the correct Python environment (check with `which python` or `where python`)

### Configuration not loading
- Check file locations:
  - User: `~/.shello_cli/user-settings.json`
  - Project: `.shello/settings.json`
- Verify JSON syntax is valid (use a JSON validator)
- Check file permissions (should be readable)

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
│   └── openai_client.py         # OpenAI-compatible API client
├── chat/
│   └── chat_session.py          # Chat session management
├── commands/
│   ├── command_detector.py      # Direct command detection
│   ├── context_manager.py       # Command history tracking
│   └── direct_executor.py       # Direct command execution
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
│   └── settings_manager.py      # Configuration management
├── cli.py                       # CLI entry point
├── constants.py                 # Application constants
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

Edit your user settings file to add new models:

```json
{
    "models": [
        "mistralai/devstral-2512:free",
        "gpt-4o",
        "your-new-model"
    ],
    "default_model": "your-new-model"
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
