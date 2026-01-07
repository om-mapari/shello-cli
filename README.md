# 🐚 Shello CLI

[![Build and Release](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml/badge.svg)](https://github.com/om-mapari/shello-cli/actions/workflows/release.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

> **Not yet another AI CLI.** Built for failures, not for code.

Most AI CLIs generate code. Shello debugs production systems: Cloud ☁️, Kubernetes ☸️, Docker 🐳, and log failures.

**The Problem:** Other AI CLIs fail when logs explode. They either refuse to run commands, flood your terminal with 50K lines, or burn thousands of tokens trying to process everything.

**Shello's Solution:** Execute real shell commands, cache full output (100MB), and show you what matters—errors, warnings, and critical context—using semantic truncation that keeps failures visible.

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

The interactive wizard will guide you through API key and model configuration.

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

Unlike code-generation AI CLIs, Shello is engineered for production debugging:

- **⚡ Executes Real Commands** - Runs shell commands instantly, no refusal, no suggestions—actual execution
- **🧠 Smart Output Management** - Semantic truncation keeps errors visible even in 50K-line logs without token waste
- **💾 Persistent Output Cache** - 100MB cache stores full command output—retrieve any section anytime during debugging
- **📊 JSON Intelligence** - Auto-analyzes massive JSON with jq paths instead of flooding your terminal
- **🎯 Failure-First Truncation** - Logs show end (where errors are), builds show both ends, lists show start
- **🔍 Semantic Error Detection** - Critical errors always visible regardless of position in output
- **⚙️ Progress Bar Compression** - npm install with 500 progress lines? Compressed to final state
- **☁️ Production-Ready** - Built for Cloud, Kubernetes, Docker debugging with comprehensive test coverage

## Key Features

### Production Debugging
- **Executes real commands** - No refusal, no suggestions—runs kubectl, docker, aws, gcloud commands instantly
- **Failure-first output** - Semantic truncation ensures errors are always visible, even in massive logs
- **100MB output cache** - Full command output stored—retrieve any section during debugging session
- **JSON analysis** - Large JSON responses auto-analyzed with jq paths instead of terminal flooding
- **Multi-platform** - Windows, Linux, macOS with automatic shell detection (bash/PowerShell/cmd)

### Smart Output Management
- **Character-based limits** - 5K-20K chars depending on command type (not arbitrary line counts)
- **Context-aware truncation** - Logs show end (where errors are), builds show both ends, lists show start
- **Semantic error detection** - Errors, warnings, stack traces always visible regardless of position
- **Progress bar compression** - npm install with 500 progress lines? Compressed to final state
- **Token optimization** - 2-3x reduction in token usage compared to naive log processing

### Debugging Workflow
- **Real-time streaming** - See output as it happens, AI gets processed summary
- **Zero data loss** - Full output always cached, retrieve any section on demand
- **Context preservation** - Working directory persists across commands
- **Flexible AI providers** - OpenAI, AWS Bedrock, OpenRouter, or local models (LM Studio, Ollama)
- **Project configs** - Team-specific settings via `.shello/settings.json`
- **Custom instructions** - Add project context in `.shello/SHELLO.md`

### Safety Features
- **Smart allowlist/denylist** - Configure which commands execute automatically vs require approval
- **AI safety integration** - AI can flag dangerous commands for review
- **YOLO mode** - Bypass approval checks for automation and CI/CD debugging
- **Critical warnings** - Denylist commands show prominent warnings before execution
- **Flexible approval modes** - Choose between AI-driven or user-driven approval workflows

## Configuration

### Quick Setup (Recommended)

Run the interactive setup wizard:

```bash
shello setup
```

This will guide you through:
- AI provider selection (OpenAI-compatible API or AWS Bedrock)
- Provider-specific configuration (API keys or AWS credentials)
- Default model selection

The setup wizard generates a well-documented `~/.shello_cli/user-settings.yml` file with all available options as comments, making it easy to customize later.

**Using AWS Bedrock?** See the [AWS Bedrock Setup Guide](doc/BEDROCK_SETUP_GUIDE.md) for detailed instructions on configuring AWS credentials and accessing Claude, Nova, and other foundation models.

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
- OpenAI (GPT-4o, GPT-4 Turbo, GPT-3.5)
- OpenRouter (access to Claude, Gemini, and 200+ models)
- Custom endpoints (LM Studio, Ollama, vLLM, etc.)

**AWS Bedrock:**
- Anthropic Claude (3.5 Sonnet, 3 Opus, 3 Sonnet)
- Amazon Nova (Pro, Lite, Micro)
- Other Bedrock foundation models

### Provider Selection

Choose your provider during setup or switch between providers at runtime:

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

Switch between configured providers without losing your conversation:

- Use `/switch` command during any chat session
- Conversation history is preserved across providers
- Compare responses from different models
- Seamlessly switch if one provider is unavailable

**Example workflow:**
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

Environment variables take precedence over configuration files, making it easy to switch credentials per session or use different credentials in CI/CD.

### Manual Configuration

**Global settings:** `~/.shello_cli/user-settings.yml`

The settings file uses YAML format with helpful comments and documentation. After running `shello setup`, you'll have a file like this:

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
```json
{
  "model": "gpt-4o-mini"
}
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

Shello includes a comprehensive trust and safety system to protect you from accidentally executing dangerous commands while maintaining a smooth workflow for safe operations.

### How It Works

The trust system evaluates every command before execution using this flow:

1. **Denylist Check** - Critical warnings for dangerous commands (highest priority)
2. **YOLO Mode** - Bypass checks for automation (if enabled)
3. **Allowlist Check** - Auto-execute safe commands without approval
4. **AI Safety Flag** - AI can indicate if a command is safe (in ai_driven mode)
5. **Approval Dialog** - Interactive prompt for commands requiring review

### Configuration

Add a `command_trust` section to your `~/.shello_cli/user-settings.json`:

```json
{
  "api_key": "your-api-key",
  "default_model": "gpt-4o",
  "command_trust": {
    "enabled": true,
    "yolo_mode": false,
    "approval_mode": "user_driven",
    "allowlist": [
      "ls",
      "ls *",
      "pwd",
      "cd *",
      "git status",
      "git log*",
      "git diff*",
      "npm test"
    ],
    "denylist": [
      "sudo rm -rf *",
      "git push --force",
      "docker system prune -a"
    ]
  }
}
```

### Configuration Options

**`enabled`** (boolean, default: `true`)
- Enable or disable the trust system entirely
- When disabled, all commands execute without checks

**`yolo_mode`** (boolean, default: `false`)
- Bypass approval checks for automation and CI/CD
- Still shows critical warnings for denylist commands
- Can also be enabled per-session with `--yolo` flag

**`approval_mode`** (string, default: `"user_driven"`)
- `"user_driven"` - Always prompt for non-allowlist commands
- `"ai_driven"` - Trust AI safety flags; only prompt when AI flags as unsafe

**`allowlist`** (array of strings)
- Commands that execute without approval
- User-defined allowlist replaces defaults
- Supports exact match, wildcards (`git *`), and regex (`^git (status|log)$`)

**`denylist`** (array of strings)
- Commands that show critical warnings before execution
- User patterns are added to default denylist (additive for safety)
- Default denylist includes: `rm -rf /`, `dd if=/dev/zero*`, `mkfs*`, etc.
- Supports exact match, wildcards, and regex

### Pattern Matching Examples

**Exact match:**
```json
"allowlist": ["git status", "npm test"]
```

**Wildcard patterns:**
```json
"allowlist": [
  "git *",           // Matches: git status, git log, git diff, etc.
  "npm run *",       // Matches: npm run test, npm run build, etc.
  "ls *"             // Matches: ls -la, ls -lh, etc.
]
```

**Regex patterns:**
```json
"allowlist": [
  "^git (status|log|diff)$",     // Matches only: git status, git log, git diff
  "^npm (test|run test)$"        // Matches only: npm test, npm run test
]
```

### YOLO Mode

For automation and CI/CD environments where you trust all commands:

**Enable via config:**
```json
{
  "command_trust": {
    "yolo_mode": true
  }
}
```

**Enable per-session:**
```bash
shello --yolo
```

**Important:** YOLO mode still respects the denylist and shows critical warnings for dangerous commands.

### AI Safety Integration

When `approval_mode` is set to `"ai_driven"`, the AI can indicate whether commands are safe:

- **AI says safe** (`is_safe: true`) → Execute without approval (after allowlist check)
- **AI says unsafe** (`is_safe: false`) → Show approval dialog with warning
- **AI doesn't specify** → Show approval dialog

The AI can also override the allowlist in `ai_driven` mode if it detects danger.

### Approval Dialog

When a command requires approval, you'll see an interactive dialog:

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

1. **Start with defaults** - The default allowlist covers most safe operations
2. **Add project-specific commands** - Extend allowlist for your workflow (e.g., `npm run dev`)
3. **Use wildcards carefully** - `git *` is safe, but `rm *` is not
4. **Never remove denylist defaults** - User denylist patterns are additive for safety
5. **Use YOLO mode sparingly** - Only in trusted automation environments
6. **Review AI warnings** - When AI flags a command as unsafe, take it seriously

### Disabling Trust System

If you prefer to disable all safety checks:

```json
{
  "command_trust": {
    "enabled": false
  }
}
```

**Warning:** This removes all protections. Use with caution.

## Technical Deep Dive

### Architecture Highlights

**For developers debugging production systems:**

- **Hybrid execution model** - Direct shell execution for instant commands, AI routing for analysis and complex queries
- **Formal correctness properties** - 8 properties validated via property-based testing (Hypothesis)
- **Intelligent truncation** - Type detector, semantic classifier, progress bar compressor—errors never hidden
- **Persistent LRU cache** - Sequential cache IDs (cmd_001, cmd_002...), 100MB limit, conversation-scoped
- **Streaming architecture** - Real-time output for you, processed summary for AI—no token waste
- **Zero data loss** - Full output always cached, retrieve any section on demand for deeper debugging
- **Modular design** - Clean separation: cache → detect → compress → truncate → analyze
- **Token optimization** - Strips column padding, compresses progress bars—2-3x reduction in token usage

See [design.md](docs/design.md) for architecture details.

## Install from Source

```bash
git clone https://github.com/om-mapari/shello-cli.git
cd shello-cli
pip install -r requirements.txt
python main.py
```

**Optional: AWS Bedrock Support**

If you plan to use AWS Bedrock as your AI provider, boto3 is included in requirements.txt. If you only need OpenAI-compatible APIs, you can skip boto3:

```bash
# Install without boto3 (OpenAI-compatible APIs only)
pip install python-dotenv pydantic rich requests urllib3 click prompt_toolkit keyring pyperclip openai hypothesis pytest

# Or install boto3 separately when needed
pip install boto3
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
- ☁️ [AWS Bedrock Setup Guide](doc/BEDROCK_SETUP_GUIDE.md)
- 📝 [Changelog](CHANGELOG.md)
- 🐛 [Report Issues](https://github.com/om-mapari/shello-cli/issues)
- 🚀 [Latest Release](https://github.com/om-mapari/shello-cli/releases/latest)

## License

MIT License - see [LICENSE](LICENSE)

---

Built with [Click](https://click.palletsprojects.com/), [Rich](https://rich.readthedocs.io/), and ☕
