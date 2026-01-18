# 🐚 Shello CLI

[![Latest Release](https://img.shields.io/github/release/om-mapari/shello-cli.svg)](https://github.com/om-mapari/shello-cli/releases)
[![Build and Release](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml/badge.svg)](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Downloads](https://img.shields.io/github/downloads/om-mapari/shello-cli/total.svg)](https://github.com/om-mapari/shello-cli/releases)
[![Stars](https://img.shields.io/github/stars/om-mapari/shello-cli.svg)](https://github.com/om-mapari/shello-cli/stargazers)

> **Not yet another AI CLI.** Built for failures, not for code.

Most AI CLIs generate code. Shello debugs production systems: Cloud ☁️, Kubernetes ☸️, Docker 🐳, and log failures.

**The Problem:** Other AI CLIs fail when logs explode. They either refuse to run commands, flood your terminal with 50K lines, or burn thousands of tokens trying to process everything.

**Shello's Solution:** Execute real shell commands, cache full output (100MB), and show you what matters: errors, warnings, and critical context using semantic truncation that keeps failures visible.

**Logs too big? Errors hidden? Shello handles it pretty well.**

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

The interactive wizard walks you through API key and model setup.

**Start chatting:**

```bash
shello
```

## See It In Action

### Real-World Debugging Examples

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

# AI analyzes failures and helps debug
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
status code instead of the expected 200. This looks like the error handler 
isn't catching the exception properly. Want me to check the API client code?

# Production debugging example
🌊 user [~/k8s-cluster]
──└─⟩ why is my pod crashing?

🐚 Shello
┌─[💻 user@hostname]─[~/k8s-cluster]
└─$ kubectl get pods

NAME                    READY   STATUS             RESTARTS   AGE
api-deployment-abc123   0/1     CrashLoopBackOff   5          3m

Let me check the logs...

┌─[💻 user@hostname]─[~/k8s-cluster]
└─$ kubectl logs api-deployment-abc123

[... 2000 lines of startup logs ...]
Error: ECONNREFUSED connect to database:5432
    at TCPConnectWrap.afterConnect [as oncomplete]

Found it. Your pod can't connect to the database. The connection is being 
refused on port 5432. Check if your database service is running and if the 
connection string in your deployment config is correct.
```

## Why Shello is Different

Most AI CLIs are built for code generation. Shello is built for debugging production systems.

- **⚡ Executes Real Commands** - Actually runs shell commands. No refusal, no suggestions, just execution
- **🧠 Smart Output Management** - Keeps errors visible even in 50K-line logs without wasting tokens
- **💾 Persistent Output Cache** - Stores 100MB of full command output. Retrieve any section anytime
- **📊 JSON Intelligence** - Analyzes massive JSON with jq paths instead of dumping everything to your terminal
- **🎯 Failure-First Truncation** - Shows the end of logs (where errors live), both ends of builds, start of lists
- **🔍 Semantic Error Detection** - Errors and warnings stay visible no matter where they appear
- **⚙️ Progress Bar Compression** - 500 lines of npm install progress? Gets compressed to the final state
- **☁️ Production-Ready** - Built for Cloud, Kubernetes, and Docker debugging

## Key Features

### Production Debugging
- **Executes real commands** - Runs kubectl, docker, aws, gcloud commands. No refusal, no suggestions
- **Failure-first output** - Errors stay visible even in massive logs
- **100MB output cache** - Full command output stored. Grab any section during your debugging session
- **JSON analysis** - Large JSON gets analyzed with jq paths instead of flooding your terminal
- **Multi-platform** - Works on Windows, Linux, macOS (bash/PowerShell/cmd auto-detected)

### Smart Output Management
- **Character-based limits** - 5K-20K chars depending on command type (no arbitrary line counts)
- **Context-aware truncation** - Logs show the end (where errors are), builds show both ends, lists show the start
- **Semantic error detection** - Errors, warnings, and stack traces stay visible wherever they appear
- **Progress bar compression** - 500 lines of npm install progress? Gets compressed to the final state
- **Token optimization** - Uses 2-3x fewer tokens than naive log processing

### Debugging Workflow
- **Real-time streaming** - You see output as it happens, AI gets a processed summary
- **Zero data loss** - Full output is always cached. Retrieve any section whenever you need it
- **Context preservation** - Your working directory persists across commands
- **Flexible AI providers** - Works with OpenAI, AWS Bedrock, OpenRouter, or local models (LM Studio, Ollama)
- **Project configs** - Team settings via `.shello/settings.json`
- **Custom instructions** - Project context in `.shello/SHELLO.md`

### Safety Features
- **Smart allowlist/denylist** - Control which commands run automatically vs need approval
- **AI safety integration** - AI flags dangerous commands for review
- **YOLO mode** - Skip approval checks for automation and CI/CD debugging
- **Critical warnings** - Denylist commands show big warnings before execution
- **Flexible approval modes** - Pick between AI-driven or user-driven approval

## Configuration

### Quick Setup (Recommended)

Run the interactive setup wizard:

```bash
shello setup
```

It walks you through:
- Picking your AI provider (OpenAI-compatible API or AWS Bedrock)
- Setting up credentials (API keys or AWS credentials)
- Choosing your default model

The wizard creates a `~/.shello_cli/user-settings.yml` file with all options documented as comments, so you can tweak things later.

**Using AWS Bedrock?** Check out the [AWS Bedrock Setup Guide](doc/BEDROCK_SETUP_GUIDE.md) for help with AWS credentials and accessing Claude, Nova, and other models.

### Configuration Management

**View current settings:**
```bash
shello config
```

**Edit settings in your default editor:**
```bash
shello config --edit
```

**Get/set specific values:**
```bash
shello config get provider
shello config set provider bedrock
shello config set openai_config.default_model gpt-4o-mini
```

**Reset to defaults:**
```bash
shello config reset
```

See [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for detailed configuration options.

## Commands

While chatting:
- `/new` - Start fresh conversation
- `/switch` - Switch between AI providers (OpenAI, Bedrock, etc.)
- `/help` - Show available commands
- `/quit` - Exit

CLI commands:
- `shello setup` - Interactive configuration wizard
- `shello config` - Show current settings
- `shello --version` - Display version

## Advanced Features

### AI Provider Support

Shello supports multiple AI providers for debugging flexibility:

### Supported Providers

**OpenAI-compatible APIs:**
- OpenAI (GPT-5.2, GPT-5 mini, GPT-4o)
- OpenRouter (access to Claude 4.x, Gemini 2.5, and other popular models)
- Custom endpoints (LM Studio, Ollama, vLLM, etc.)

**AWS Bedrock:**
- Anthropic Claude (Claude Haiku 4.5, Sonnet 4.5, Opus 4.5)
- Amazon Nova (Nova Micro, Nova Lite, Nova Pro, Nova Premier, Nova Canvas, Nova Reel)
- Other Bedrock foundation models

### Provider Selection

Pick your provider during setup or switch between them at runtime:

```bash
# Initial setup - choose your provider
shello setup

# Switch providers during a chat session
🌊 user [~/projects]
──└─⟩ /switch

🔄 Switch Provider:
  1. [✓] OpenAI-compatible API
  2. [ ] AWS Bedrock

Select provider (or 'c' to cancel): 2

✓ Switched to bedrock
  Model: anthropic.claude-3-5-sonnet-20241022-v2:0
  Conversation history preserved
```

### Runtime Provider Switching

You can switch between providers without losing your conversation:

- Use `/switch` during any chat
- Your conversation history stays intact
- Compare responses from different models
- Switch if one provider goes down

**Example:**
```bash
# Start with OpenAI
shello

🌊 user [~/projects]
──└─⟩ analyze this codebase structure

🐚 Shello (gpt-4o)
[Analysis from GPT-4o...]

# Switch to Claude via Bedrock
🌊 user [~/projects]
──└─⟩ /switch
[Select AWS Bedrock]

🌊 user [~/projects]
──└─⟩ now give me a second opinion on the architecture

🐚 Shello (claude-3-5-sonnet)
[Analysis from Claude...]
```

### Environment Variables

All provider credentials support environment variable overrides:

**OpenAI-compatible APIs:**
```bash
export OPENAI_API_KEY="your-api-key"
```

**AWS Bedrock:**
```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="default"
# Or explicit credentials:
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

Environment variables override config files, so you can easily switch credentials per session or use different ones in CI/CD.

### Manual Configuration

**Global settings:** `~/.shello_cli/user-settings.yml`

The settings file is YAML with helpful comments. After running `shello setup`, you'll have something like this:

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
  api_key: sk-proj-abc123...  # Or use OPENAI_API_KEY env var
  base_url: https://api.openai.com/v1
  default_model: gpt-4o
  models:
    - gpt-4o
    - gpt-4o-mini
    - gpt-4-turbo

# =============================================================================
# OUTPUT MANAGEMENT (optional - uses defaults if not specified)
# =============================================================================
# Uncomment and modify to customize:
# output_management:
#   enabled: true
#   limits:
#     list: 5000
#     search: 10000
#     default: 8000

# =============================================================================
# COMMAND TRUST (optional - uses defaults if not specified)
# =============================================================================
# Uncomment and modify to customize:
# command_trust:
#   enabled: true
#   yolo_mode: false
#   allowlist:
#     - ls
#     - pwd
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
```

**Key features:**
- Only configured values are saved (everything else uses defaults)
- All optional settings are shown as comments with examples
- Inline documentation explains each setting
- Environment variables can override any credential

**Project settings:** `.shello/settings.json` (overrides global)
```yaml
model: gpt-4o-mini
```

**Environment variables:**

OpenAI-compatible:
```bash
export OPENAI_API_KEY="your-api-key"
```

AWS Bedrock:
```bash
export AWS_REGION="us-east-1"
export AWS_PROFILE="default"
# Or use explicit credentials:
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
```

### Command Trust and Safety

Shello has a trust system to stop you from accidentally running dangerous commands while keeping safe operations smooth.

### How It Works

Every command gets checked before execution:

1. **Denylist Check** - Warns about dangerous commands (highest priority)
2. **YOLO Mode** - Skip checks for automation (if enabled)
3. **Allowlist Check** - Run safe commands without asking
4. **AI Safety Flag** - AI can mark commands as safe (in ai_driven mode)
5. **Approval Dialog** - Ask before running anything else

### Configuration

Add a `command_trust` section to your `~/.shello_cli/user-settings.yml`:

```yaml
provider: openai

openai_config:
  api_key: your-api-key
  default_model: gpt-4o

command_trust:
  enabled: true
  yolo_mode: false
  approval_mode: user_driven
  allowlist:
    - ls
    - ls *
    - pwd
    - cd *
    - git status
    - git log*
    - git diff*
    - npm test
  denylist:
    - sudo rm -rf *
    - git push --force
    - docker system prune -a
```

### Configuration Options

**`enabled`** (boolean, default: `true`)
- Turn the trust system on or off
- When off, all commands run without checks

**`yolo_mode`** (boolean, default: `false`)
- Skip approval checks for automation and CI/CD
- Still warns about denylist commands
- Can also use `--yolo` flag per session

**`approval_mode`** (string, default: `"user_driven"`)
- `"user_driven"` - Always ask before running non-allowlist commands
- `"ai_driven"` - Trust AI safety flags, only ask when AI says it's unsafe

**`allowlist`** (array of strings)
- Commands that run without asking
- Your allowlist replaces the defaults
- Supports exact match, wildcards (`git *`), and regex (`^git (status|log)$`)

**`denylist`** (array of strings)
- Commands that show warnings before running
- Your patterns get added to the default denylist (for safety)
- Defaults include: `rm -rf /`, `dd if=/dev/zero*`, `mkfs*`, etc.
- Supports exact match, wildcards, and regex

### Pattern Matching Examples

**Exact match:**
```yaml
allowlist:
  - git status
  - npm test
```

**Wildcard patterns:**
```yaml
allowlist:
  - git *           # Matches: git status, git log, git diff, etc.
  - npm run *       # Matches: npm run test, npm run build, etc.
  - ls *            # Matches: ls -la, ls -lh, etc.
```

**Regex patterns:**
```yaml
allowlist:
  - ^git (status|log|diff)$     # Matches only: git status, git log, git diff
  - ^npm (test|run test)$       # Matches only: npm test, npm run test
```

### YOLO Mode

For automation and CI/CD where you trust everything:

**Turn on in config:**
```yaml
command_trust:
  yolo_mode: true
```

**Turn on per session:**
```bash
shello --yolo
```

**Note:** YOLO mode still warns about denylist commands.

### AI Safety Integration

When `approval_mode` is `"ai_driven"`, the AI can mark commands as safe or unsafe:

- **AI says safe** (`is_safe: true`) → Runs without asking (after allowlist check)
- **AI says unsafe** (`is_safe: false`) → Shows approval dialog with warning
- **AI doesn't say** → Shows approval dialog

The AI can override the allowlist in `ai_driven` mode if it spots danger.

### Approval Dialog

When a command needs approval, you'll see this:

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️  COMMAND APPROVAL REQUIRED                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ⚠️ CRITICAL: This command is in DENYLIST!              │
│                                                          │
│  Command: rm -rf node_modules                           │
│  Directory: /home/user/project                          │
│                                                          │
│  [A] Approve    [D] Deny                                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

Press **A** to approve or **D** to deny execution.

### Default Patterns

**Default Allowlist** (safe commands that execute automatically):
- Navigation: `ls`, `pwd`, `cd`
- Git read-only: `git status`, `git log`, `git diff`, `git show`, `git branch`
- File viewing: `cat`, `less`, `more`, `head`, `tail`
- Search: `grep`, `find`, `rg`, `ag`
- Process inspection: `ps`, `top`, `htop`
- Network inspection: `ping`, `curl -I`, `wget --spider`
- Package inspection: `npm list`, `pip list`, `pip show`

**Default Denylist** (dangerous commands that always show warnings):
- Destructive filesystem: `rm -rf /`, `rm -rf /*`, `rm -rf ~`
- Disk operations: `dd if=/dev/zero*`, `mkfs*`, `format*`
- System modifications: `chmod -R 777 /`, `chown -R * /`
- Dangerous redirects: `> /dev/sda`

### Best Practices

1. **Start with defaults** - Default allowlist covers most safe stuff
2. **Add project commands** - Extend allowlist for your workflow (like `npm run dev`)
3. **Be careful with wildcards** - `git *` is fine, `rm *` is not
4. **Don't remove denylist defaults** - Your patterns get added to them, not replace them
5. **Use YOLO mode sparingly** - Only in trusted automation
6. **Listen to AI warnings** - When AI flags something as unsafe, pay attention

### Disabling Trust System

To turn off all safety checks:

```yaml
command_trust:
  enabled: false
```

**Warning:** This removes all protections.

## Technical Deep Dive

### Architecture Highlights

**For developers who want the details:**

- **Hybrid execution model** - Direct shell for instant commands, AI routing for analysis
- **Formal correctness properties** - 8 properties tested via property-based testing (Hypothesis)
- **Intelligent truncation** - Type detector, semantic classifier, progress bar compressor keep errors visible
- **Persistent LRU cache** - Sequential IDs (cmd_001, cmd_002...), 100MB limit, per-conversation
- **Streaming architecture** - Real-time output for you, processed summary for AI (no token waste)
- **Zero data loss** - Full output always cached, grab any section for deeper debugging
- **Modular design** - Clean separation: cache → detect → compress → truncate → analyze
- **Token optimization** - Strips column padding, compresses progress bars (2-3x fewer tokens)

Check out [design.md](docs/design.md) for architecture details.

## Install from Source

### Using UV (Recommended - 10-100x faster)

```bash
# Install uv if you haven't already
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/om-mapari/shello-cli.git
cd shello-cli
uv venv
# Activate: .venv\Scripts\Activate.ps1 (Windows) or source .venv/bin/activate (Linux/macOS)
uv pip install -e .
python main.py
```

### Alternative: Using pip (if you don't have uv)

```bash
git clone https://github.com/om-mapari/shello-cli.git
cd shello-cli
python -m venv venv
# Activate: venv\Scripts\Activate.ps1 (Windows) or source venv/bin/activate (Linux/macOS)
pip install -e .
python main.py
```

**Note:** All dependencies including boto3 (AWS Bedrock support) are defined in `pyproject.toml` and installed automatically.

## Build Executable

```bash
# Windows
build.bat

# Linux/macOS
chmod +x build.sh && ./build.sh
```

Output goes in the `dist/` folder. Check [BUILD_INSTRUCTIONS.md](doc/BUILD_INSTRUCTIONS.md) for details.

## Contributing

Contributions welcome! Fork the repo, make a feature branch, and send a PR.

Check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Links

- 🔧 [Development Setup](DEVELOPMENT_SETUP.md)
- ☁️ [AWS Bedrock Setup Guide](doc/BEDROCK_SETUP_GUIDE.md)
- 📝 [Changelog](CHANGELOG.md)
- 🐛 [Report Issues](https://github.com/om-mapari/shello-cli/issues)
- 🚀 [Latest Release](https://github.com/om-mapari/shello-cli/releases/latest)

## Author

**Om Mapari**

- GitHub: [@om-mapari](https://github.com/om-mapari)
- Project: [Shello CLI](https://github.com/om-mapari/shello-cli)

## License

MIT License - see [LICENSE](LICENSE)

## Acknowledgments

Built with:
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal UI
- [OpenAI](https://openai.com/) - AI capabilities
- [AWS Bedrock](https://aws.amazon.com/bedrock/) - Multi-model support

---

**Made with ☕ and 🐚 by Om Mapari**
