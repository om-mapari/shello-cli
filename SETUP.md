# Shello CLI Development Setup Guide

This guide is for developers who want to contribute to or modify Shello CLI.

## Quick Start for Users

If you just want to use Shello CLI, run:

```bash
shello setup
```

This interactive wizard will configure everything you need.

## CLI Commands

### User Commands
- `shello` or `shello chat` - Start interactive chat session
- `shello setup` - Interactive configuration wizard
- `shello config` - Display current configuration
- `shello --version` - Show version information
- `shello --help` - Show help message

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
    ],
    "output_management": {
        "enabled": true,
        "show_warnings": true,
        "limits": {
            "list": 50,
            "search": 100,
            "log": 200,
            "json": 500,
            "default": 100
        },
        "safety_limit": 1000
    }
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

## Configuration Hierarchy

Settings are loaded in this order (later overrides earlier):
1. Default values (hardcoded)
2. User settings (`~/.shello_cli/user-settings.json`)
3. Environment variables (`OPENAI_API_KEY`)
4. Project settings (`.shello/settings.json`)

## Testing

### Run all tests (excluding integration tests):
```bash
pytest tests/ -v
```

### Run only property-based tests:
```bash
pytest tests/ -v -k "property"
```

### Run integration tests (requires API key):
```bash
pytest tests/ -v -m integration
```

### Run specific test file:
```bash
pytest tests/test_openai_client.py -v
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
1. Run `shello setup` to configure interactively
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
shello config
```

## Development

### Project Structure
```
shello_cli/
├── agent/
│   └── shello_agent.py          # Main agent logic
├── api/
│   └── openai_client.py         # OpenAI-compatible API client
├── chat/
│   └── chat_session.py          # Chat session management
├── commands/
│   └── command_executor.py      # Command execution
├── tools/
│   ├── bash_tool.py             # Bash command execution
│   └── tools.py                 # Tool definitions
├── ui/
│   ├── ui_renderer.py           # Terminal UI rendering
│   └── user_input.py            # User input handling
├── utils/
│   └── settings_manager.py      # Configuration management
├── cli.py                       # CLI entry point
├── constants.py                 # Application constants
└── types.py                     # Type definitions

tests/
├── test_openai_client.py              # Unit & property tests
└── test_openai_client_integration.py  # Integration tests
```

### Running the Application

**From source:**
```bash
python main.py
```

**With specific command:**
```bash
python main.py setup
python main.py config
python main.py chat
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

Or use `shello setup` to reconfigure interactively.

### Running Property-Based Tests

Property-based tests use Hypothesis to generate test cases:

```bash
# Run with verbose output
pytest tests/test_openai_client.py::TestShelloClientProperties -v -s

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

- [CONTRIBUTING.md](CONTRIBUTING.md) - Contribution guidelines
- [CHANGELOG.md](CHANGELOG.md) - Version history
- [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) - Build process details
