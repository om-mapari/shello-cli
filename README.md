# 🐚 Shello CLI

[![Build and Release](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml/badge.svg)](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Not just another AI CLI tool.** Built with intelligent output management, semantic analysis, and production-ready features.

An AI-powered terminal assistant that doesn't just suggest commands—it executes them intelligently. Chat naturally, get real-time results with smart truncation, and access cached output when you need more context.

## Why Shello is Different

Unlike basic AI CLI tools that just wrap ChatGPT, Shello is engineered for real-world terminal usage:

- **🧠 Smart Output Management** - Character-based truncation with semantic analysis keeps errors visible even in massive outputs
- **💾 Output Caching** - Retrieve specific sections from previous commands without re-execution (5-min cache)
- **📊 JSON Intelligence** - Auto-analyzes large JSON with jq paths instead of flooding your terminal
- **🎯 Context-Aware Truncation** - Different strategies for different commands (logs show end, lists show start, builds show both)
- **⚡ Progress Bar Compression** - Collapses repetitive progress output to final state
- **🔍 Semantic Line Detection** - Critical errors always visible regardless of position in output
- **🛠️ Production-Ready** - Comprehensive test suite with property-based testing for correctness guarantees

## Technical Highlights

**For developers who care about the details:**

- **Formal correctness properties** - 8 properties validated via property-based testing (Hypothesis)
- **Intelligent truncation** - Type detector, semantic classifier, progress bar compressor working in concert
- **LRU cache with TTL** - Sequential cache IDs (cmd_001, cmd_002...) with 5-minute expiration
- **Streaming architecture** - User sees real-time output, AI gets processed summary
- **Zero data loss** - Full output always cached, retrieve any section on demand
- **Modular design** - Clean separation: cache → detect → compress → truncate → analyze

See [design.md](.kiro/specs/output-management/design.md) for architecture details.

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
"Check disk usage and show me the largest directories"
→ Executes, truncates intelligently, shows you what matters

"List all Docker containers and their status"
→ Smart truncation keeps headers and critical info visible

"Find all TODO comments in my Python files"
→ Semantic analysis ensures you see all matches, not just first 100 lines

"Analyze the structure of my AWS Lambda functions"
→ Large JSON? Auto-analyzed with jq paths, raw cached for retrieval

"Show me what's using port 3000"
→ Errors always visible even in verbose output
```

### Smart Output Management in Action

When you run a command that produces large output:

```bash
🐚 Shello> npm install
# ... installation output streams in real-time ...
# ... AI sees truncated version with summary ...

───────────────────────────────────────────────────────────
📊 OUTPUT SUMMARY
───────────────────────────────────────────────────────────
Total: 45,000 chars (850 lines) | Shown: 8,000 chars (150 lines)
Strategy: FIRST_LAST (20% first + 80% last)
Optimizations: Progress bars compressed (saved 200 lines)
Semantic: 3 critical, 5 high, 142 low importance lines shown

💾 Cache ID: cmd_001 (expires in 5 min)
💡 Use get_cached_output(cache_id="cmd_001", lines="-100") to see last 100 lines
───────────────────────────────────────────────────────────

🐚 Shello> get me the last 50 lines from that install
# AI automatically uses: get_cached_output(cache_id="cmd_001", lines="-50")
# Shows you exactly what you need
```

Shello understands context, executes commands in real-time, and works with bash, PowerShell, cmd, or Git Bash.

## Key Features

### Intelligent Output Management
- **Character-based limits** - 5K-20K chars depending on command type (not arbitrary line counts)
- **Smart truncation strategies** - Logs show end, lists show start, builds show both ends
- **Semantic analysis** - Errors, warnings, and critical info always visible
- **Progress bar compression** - npm install with 500 progress lines? Compressed to final state
- **Output caching** - Retrieve any section from last 5 minutes without re-running commands

### Advanced Features
- **JSON intelligence** - Large JSON auto-analyzed with jq paths, raw data cached
- **Multi-platform** - Windows, Linux, macOS with automatic shell detection (bash/PowerShell/cmd)
- **Flexible AI** - OpenAI, OpenRouter, or local models (LM Studio, Ollama)
- **Project configs** - Team-specific settings via `.shello/settings.json`
- **Custom instructions** - Add project context in `.shello/SHELLO.md`

### Developer Experience
- **Real-time streaming** - See output as it happens, AI gets smart summary
- **Context preservation** - Working directory persists across commands
- **Property-based testing** - 105+ tests with formal correctness properties
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

See [FIRST_TIME_SETUP.md](FIRST_TIME_SETUP.md) for detailed configuration options.

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

- 📖 [First-Time Setup Guide](FIRST_TIME_SETUP.md)
- 🔧 [Development Setup](SETUP.md)
- 📝 [Changelog](CHANGELOG.md)
- 🐛 [Report Issues](https://github.com/om-mapari/shello-cli/issues)
- 🚀 [Latest Release](https://github.com/om-mapari/shello-cli/releases/latest)

## License

MIT License - see [LICENSE](LICENSE)

---

Built with [Click](https://click.palletsprojects.com/), [Rich](https://rich.readthedocs.io/), and ☕
