# 🐚 Shello CLI

[![Build and Release](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml/badge.svg)](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Not just another AI CLI tool.** Built with intelligent output management, semantic analysis, and production-ready features.

An AI-powered terminal assistant that doesn't just suggest commands—it executes them intelligently. Chat naturally, get real-time results with smart truncation, and access cached output when you need more context.

## Why Shello is Different

Unlike basic AI CLI tools that just wrap ChatGPT, Shello is engineered for real-world terminal usage:

- **⚡ Direct Command Execution** - Common commands (ls, cd, pwd, grep) execute instantly without AI overhead
- **🧠 Smart Output Management** - Character-based truncation with semantic analysis keeps errors visible even in massive outputs
- **💾 Persistent Output Cache** - Retrieve any previous command output throughout the conversation (100MB cache, no expiration)
- **📊 JSON Intelligence** - Auto-analyzes large JSON with jq paths instead of flooding your terminal
- **🎯 Context-Aware Truncation** - Different strategies for different commands (logs show end, lists show start, builds show both)
- **🔍 Semantic Line Detection** - Critical errors always visible regardless of position in output
- **⚙️ Progress Bar Compression** - Collapses repetitive progress output to final state
- **🛠️ Production-Ready** - Comprehensive test suite with property-based testing for correctness guarantees

## Technical Highlights

**For developers who care about the details:**

- **Hybrid execution model** - Direct shell execution for simple commands, AI routing for complex queries
- **Formal correctness properties** - 8 properties validated via property-based testing (Hypothesis)
- **Intelligent truncation** - Type detector, semantic classifier, progress bar compressor working in concert
- **Persistent LRU cache** - Sequential cache IDs (cmd_001, cmd_002...), 100MB limit, conversation-scoped
- **Streaming architecture** - User sees real-time output, AI gets processed summary
- **Zero data loss** - Full output always cached, retrieve any section on demand
- **Modular design** - Clean separation: cache → detect → compress → truncate → analyze
- **Shell optimization** - Strips column padding to reduce character count by 2-3x

See [design.md](docs/design.md) for architecture details.

## Quick Start

**One-line installation:**

```powershell
# Windows (PowerShell - Recommended, no admin needed)
Invoke-WebRequest -Uri "https://github.com/om-mapari/shello-cli/releases/latest/download/shello.exe" -OutFile "$env:LOCALAPPDATA\Microsoft\WindowsApps\shello.exe"
```

```bash
# Linux
curl -L https://github.com/om-mapari/shello-cli/releases/latest/download/shello -o /tmp/shello && sudo mv /tmp/shello /usr/local/bin/shello && sudo chmod +x /usr/local/bin/shello

# macOS
curl -L https://github.com/om-mapari/shello-cli/releases/latest/download/shello-macos -o /tmp/shello && sudo mv /tmp/shello /usr/local/bin/shello && sudo chmod +x /usr/local/bin/shello
```

**Verify installation:**

```bash
shello --version
```

**Configure (first time):**

```bash
shello setup
```

The interactive wizard will guide you through API key and model configuration.

**Start chatting:**

```bash
shello
```

## What Can It Do?

### Real-World Examples

```
💡 Start by describing what you'd like to do...

── Starting new conversation ──

# Direct commands execute instantly (no AI call)
🌊 user [~/projects]
──└─⟩ ls -la
# Executes immediately, output cached as cmd_001

🌊 user [~/projects]
──└─⟩ cd myapp

🌊 user [~/projects/myapp]
──└─⟩ pwd
/home/user/projects/myapp

# Natural language queries route to AI
🌊 user [~/projects/myapp]
──└─⟩ find all python files with TODO comments

🐚 Shello
┌─[💻 user@hostname]─[~/projects/myapp]
└─$ grep -r "TODO" --include="*.py" .

./main.py:# TODO: Add error handling
./utils.py:# TODO: Optimize this function
./tests/test_main.py:# TODO: Add more test cases

Found 3 TODO comments in your Python files.

# AI understands context and can chain commands
🌊 user [~/projects/myapp]
──└─⟩ now check if there are any FIXME comments too

🐚 Shello
┌─[💻 user@hostname]─[~/projects/myapp]
└─$ grep -r "FIXME" --include="*.py" .

./api/client.py:# FIXME: Handle timeout errors

Found 1 FIXME comment.

# Large output gets smart truncation
🌊 user [~/projects/myapp]
──└─⟩ npm install
# Direct execution, output streams in real-time

added 1247 packages, and audited 1248 packages in 45s
... (installation output) ...

───────────────────────────────────────────────────────────
📊 OUTPUT SUMMARY
───────────────────────────────────────────────────────────
Total: 45,000 chars (850 lines) | Shown: 8,000 chars (150 lines)
Strategy: FIRST_LAST (20% first + 80% last)
Optimizations: Progress bars compressed (saved 200 lines)

💾 Cache ID: cmd_002
💡 Use get_cached_output(cache_id="cmd_002", lines="-100") to see last 100 lines
───────────────────────────────────────────────────────────

# Retrieve cached output anytime
🌊 user [~/projects/myapp]
──└─⟩ show me the last 50 lines from that install

🐚 Shello
Using get_cached_output to retrieve lines from cmd_002...

[Last 50 lines of npm install output]

# AI can analyze and help with errors
🌊 user [~/projects/myapp]
──└─⟩ run the tests

🐚 Shello
┌─[💻 user@hostname]─[~/projects/myapp]
└─$ npm test

FAIL tests/api.test.js
  ✗ should handle API errors (15ms)
    Expected status 200, received 500

Tests: 1 failed, 12 passed, 13 total

I see one test is failing. The API error handling test is receiving a 500 
status code instead of the expected 200. Would you like me to check the 
API client code to see what might be causing this?
```

## Key Features

### Direct Command Execution
- **Zero-latency commands** - Common shell commands (ls, cd, pwd, cat, grep, etc.) execute instantly
- **Automatic routing** - Detects direct commands vs natural language queries
- **Directory persistence** - cd changes persist across commands
- **Context awareness** - AI sees history of direct commands when needed
- **Shared caching** - Direct and AI-executed commands use same cache

### Intelligent Output Management
- **Character-based limits** - 5K-20K chars depending on command type (not arbitrary line counts)
- **Smart truncation strategies** - Logs show end, lists show start, builds show both ends
- **Semantic analysis** - Errors, warnings, and critical info always visible
- **Progress bar compression** - npm install with 500 progress lines? Compressed to final state
- **Persistent caching** - Retrieve any command output throughout conversation (100MB cache, no expiration)

### Advanced Features
- **JSON intelligence** - Large JSON auto-analyzed with jq paths, raw data cached
- **Multi-platform** - Windows, Linux, macOS with automatic shell detection (bash/PowerShell/cmd)
- **Flexible AI** - OpenAI, OpenRouter, or local models (LM Studio, Ollama)
- **Project configs** - Team-specific settings via `.shello/settings.json`
- **Custom instructions** - Add project context in `.shello/SHELLO.md`

### Developer Experience
- **Real-time streaming** - See output as it happens, AI gets smart summary
- **Context preservation** - Working directory persists across commands
- **Directory-aware prompt** - Shows current directory with abbreviated paths
- **Property-based testing** - 1,400+ tests with formal correctness properties
- **Type-safe** - Full type hints and dataclass models

## Commands

While chatting:
- `/new` - Start fresh conversation
- `/help` - Show available commands
- `/quit` - Exit

CLI commands:
- `shello setup` - Interactive configuration wizard
- `shello config` - Show current settings
- `shello --version` - Display version

## Configuration

### Quick Setup (Recommended)

Run the interactive setup wizard:

```bash
shello setup
```

This will guide you through:
- API provider selection (OpenAI, OpenRouter, or custom)
- API key configuration
- Default model selection

### Manual Configuration

**Global settings:** `~/.shello_cli/user-settings.json`
```json
{
  "api_key": "your-api-key",
  "base_url": "https://openrouter.ai/api/v1",
  "default_model": "mistralai/devstral-2512:free",
  "models": ["mistralai/devstral-2512:free", "gpt-4o", "gpt-4o-mini"]
}
```

**Project settings:** `.shello/settings.json` (overrides global)
```json
{
  "model": "gpt-4o-mini"
}
```

**Environment variable:**
```bash
export OPENAI_API_KEY="your-api-key"
```

See [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for detailed configuration options.

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

- 🔧 [Development Setup](DEVELOPMENT_SETUP.md)
- 📝 [Changelog](CHANGELOG.md)
- 🐛 [Report Issues](https://github.com/om-mapari/shello-cli/issues)
- 🚀 [Latest Release](https://github.com/om-mapari/shello-cli/releases/latest)

## License

MIT License - see [LICENSE](LICENSE)

---

Built with [Click](https://click.palletsprojects.com/), [Rich](https://rich.readthedocs.io/), and ☕
