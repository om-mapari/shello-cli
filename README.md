# 🐚 Shello CLI

[![Build and Release](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml/badge.svg)](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> Yet another AI CLI tool - but built with practical usecase in mind.

An AI-powered terminal assistant that doesn't just suggest commands—it executes them for you. Chat naturally, get real-time results, and stop copy-pasting from ChatGPT.

## Quick Start

**Download and run** (no installation needed):

```bash
# Windows
curl -L https://github.com/om-mapari/shello-cli/releases/latest/download/shello-windows.zip -o shello.zip
tar -xf shello.zip
move shello.exe C:\Windows\System32\

# Linux
wget https://github.com/om-mapari/shello-cli/releases/latest/download/shello-linux.tar.gz
tar -xzf shello-linux.tar.gz
sudo mv shello /usr/local/bin/ && sudo chmod +x /usr/local/bin/shello

# macOS
wget https://github.com/om-mapari/shello-cli/releases/latest/download/shello-macos.tar.gz
tar -xzf shello-macos.tar.gz
sudo mv shello /usr/local/bin/ && sudo chmod +x /usr/local/bin/shello
```

**Set your API key:**

```bash
mkdir -p ~/.shello_cli
echo '{"api_key": "your-key", "base_url": "https://openrouter.ai/api/v1"}' > ~/.shello_cli/user-settings.json
```

**Start chatting:**

```bash
shello
```

## What Can It Do?

```
"Check disk usage and show me the largest directories"
"List all Docker containers and their status"
"Find all TODO comments in my Python files"
"Analyze the structure of my AWS Lambda functions"
"Show me what's using port 3000"
```

Shello understands context, executes commands in real-time, and works with bash, PowerShell, cmd, or Git Bash.

## Key Features

- **Execute commands** - AI runs them for you with streaming output
- **Smart JSON handling** - Analyzes structure before flooding your terminal
- **Multi-platform** - Windows, Linux, macOS with automatic shell detection
- **Flexible AI** - Works with OpenAI, OpenRouter, or local models (LM Studio, Ollama)
- **Project configs** - Team-specific settings via `.shello/settings.json`
- **Custom instructions** - Add project context in `.shello/SHELLO.md`

## Commands

While chatting:
- `/new` - Start fresh conversation
- `/help` - Show available commands
- `/quit` - Exit

CLI commands:
- `shello config` - Show current settings
- `shello --version` - Display version

## Configuration

**Global settings:** `~/.shello_cli/user-settings.json`
```json
{
  "api_key": "your-api-key",
  "base_url": "https://openrouter.ai/api/v1",
  "models": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet"],
  "model": "openai/gpt-4o"
}
```

**Project settings:** `.shello/settings.json` (overrides global)
```json
{
  "model": "anthropic/claude-3.5-sonnet"
}
```

**Environment variable:**
```bash
export OPENAI_API_KEY="your-api-key"
```

See [SETUP.md](SETUP.md) for detailed configuration options.

## Install from Source

```bash
git clone https://github.com/om-mapari/shello-cli.git
cd shello-cli
pip install -r requirements.txt
python main.py
```

## Build Executable

```bash
# Windows
build.bat

# Linux/macOS
chmod +x build.sh && ./build.sh
```

Output in `dist/` folder. See [BUILD_INSTRUCTIONS.md](doc/BUILD_INSTRUCTIONS.md) for details.

## Contributing

Contributions welcome! Fork, create a feature branch, and submit a PR.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Links

- 📖 [Setup Guide](SETUP.md)
- 📝 [Changelog](CHANGELOG.md)
- 🐛 [Report Issues](https://github.com/om-mapari/shello-cli/issues)
- 🚀 [Latest Release](https://github.com/om-mapari/shello-cli/releases/latest)

## License

MIT License - see [LICENSE](LICENSE)

---

Built with [Click](https://click.palletsprojects.com/), [Rich](https://rich.readthedocs.io/), and ☕
