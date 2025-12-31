# Shello CLI Setup Guide

## Configuration

The Shello CLI uses two configuration files for settings:

### 1. User Settings (Global)

Location: `~/.shello_cli/user-settings.json`

This file contains your API credentials and default preferences:

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

**Note:** You can also set the API key via the `OPENAI_API_KEY` environment variable.

### 2. Project Settings (Local)

Location: `.shello/settings.json` (in your project directory)

This file contains project-specific settings:

```json
{
    "model": "mistralai/devstral-2512:free"
}
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure your API key:**
   
   Option A: Create user settings file
   ```bash
   mkdir -p ~/.shello_cli
   echo '{"api_key": "your-key", "base_url": "https://openrouter.ai/api/v1"}' > ~/.shello_cli/user-settings.json
   ```
   
   Option B: Set environment variable
   ```bash
   export OPENAI_API_KEY="your-api-key"
   ```

3. **Test the configuration:**
   ```bash
   python test_model.py
   ```

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

The client supports any OpenAI-compatible API endpoint. Popular options include:

- **OpenAI:** `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-3.5-turbo`
- **OpenRouter:** `mistralai/devstral-2512:free`, `anthropic/claude-3-opus`, etc.
- **Local models:** Any model served via OpenAI-compatible API

## API Providers

### OpenAI
```json
{
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-..."
}
```

### OpenRouter
```json
{
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-or-v1-..."
}
```

### Local (e.g., LM Studio, Ollama with OpenAI compatibility)
```json
{
    "base_url": "http://localhost:1234/v1",
    "api_key": "not-needed"
}
```

## File Permissions

The settings manager automatically sets secure file permissions (600) on user settings files to protect your API keys.

## Troubleshooting

### "No API key configured" error
- Check that `~/.shello_cli/user-settings.json` exists and contains `api_key`
- Or set the `OPENAI_API_KEY` environment variable

### "API error" messages
- Verify your API key is valid
- Check that the `base_url` is correct for your provider
- Ensure the model name is supported by your provider

### Import errors
- Make sure you've installed all dependencies: `pip install -r requirements.txt`
- Verify you're in the correct Python environment

## Development

### Project Structure
```
shello_cli/
├── api/
│   └── openai_client.py    # OpenAI-compatible API client
├── tools/
│   ├── bash_tool.py         # Bash command execution
│   └── tools.py             # Tool definitions
├── utils/
│   └── settings_manager.py  # Configuration management
└── types.py                 # Type definitions

tests/
├── test_openai_client.py              # Unit & property tests
└── test_openai_client_integration.py  # Integration tests
```

### Adding New Models

Edit your user settings file to add new models to the list:

```json
{
    "models": [
        "mistralai/devstral-2512:free",
        "gpt-4o",
        "your-new-model"
    ]
}
```

### Running Property-Based Tests

Property-based tests use Hypothesis to generate test cases:

```bash
# Run with verbose output
pytest tests/test_openai_client.py::TestShelloClientProperties -v -s

# Increase number of examples
pytest tests/ --hypothesis-show-statistics
```
