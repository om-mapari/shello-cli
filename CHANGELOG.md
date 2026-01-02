# Changelog

All notable changes to Shello CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-02

### Added

#### Core Features
- **AI-Powered Chat Interface**: Interactive conversational AI assistant with streaming responses
- **Command Execution**: Execute shell commands directly through AI with real-time output streaming
- **Multi-Platform Support**: Native support for Windows (cmd, PowerShell, Git Bash), Linux, and macOS
- **OpenAI-Compatible API Integration**: Works with OpenAI, OpenRouter, LM Studio, Ollama, and any OpenAI-compatible endpoint

#### Tools & Capabilities
- **Bash Tool**: Execute shell commands with automatic shell detection (bash, PowerShell, cmd)
  - Real-time command output streaming
  - Working directory persistence across commands
  - Support for cd command with state management
  - Cross-platform command execution
- **JSON Analyzer Tool**: Analyze JSON output structure from commands
  - Automatic jq path generation
  - Prevents terminal flooding from large JSON responses
  - Helps discover data structure before filtering
- **Output Management**: Smart output truncation to prevent terminal flooding
  - Configurable output size limits
  - Automatic truncation warnings
  - Streaming output support

#### User Interface
- **Rich Terminal UI**: Beautiful terminal interface powered by Rich library
  - Syntax highlighting for code blocks
  - Custom markdown rendering
  - Colored output and formatting
  - Welcome banner with system information
- **Interactive Commands**:
  - `/quit` or `/exit` - Exit the application
  - `/new` - Start a new conversation
  - `/help` - Display help and shortcuts
  - `/about` - Display about information
- **CLI Commands**:
  - `shello` or `shello chat` - Start chat session
  - `shello config` - Show current configuration
  - `shello --version` - Display version information

#### Configuration & Settings
- **Flexible Configuration System**:
  - Global user settings: `~/.shello_cli/user-settings.json`
  - Project-specific settings: `.shello/settings.json`
  - Environment variable support
- **Custom Instructions**: Support for custom AI instructions via `.shello/SHELLO.md`
- **Multi-Model Support**: Configure and switch between different AI models
- **API Configuration**: Customizable API endpoints and authentication

#### Session Management
- **Conversation History**: Persistent chat history within sessions
- **Context Awareness**: AI maintains context across multiple interactions
- **Tool Call Tracking**: Complete tracking of tool executions and results
- **System Information Integration**: Automatic detection of OS, shell, working directory, and timestamp

#### Developer Features
- **Modular Architecture**:
  - Separate modules for agent, API, chat, commands, tools, UI, and utilities
  - Clean separation of concerns
  - Extensible tool system
- **Comprehensive Testing**: Test suite with pytest
- **Build System**: Automated build scripts for creating standalone executables
  - PyInstaller integration
  - Platform-specific build scripts (build.bat, build.sh)
  - Automated GitHub Actions workflow for releases

#### Distribution
- **Standalone Executables**: Pre-built binaries for Windows, Linux, and macOS
- **Easy Installation**: Multiple installation methods
  - Download pre-built executables
  - Install from source
  - Add to system PATH
- **GitHub Releases**: Automated release workflow with CI/CD

#### Documentation
- Comprehensive README with quick start guide
- Detailed setup instructions (SETUP.md)
- Build instructions (BUILD_INSTRUCTIONS.md)
- Contributing guidelines (CONTRIBUTING.md)
- Multiple technical documentation files in doc/ directory

### Technical Details
- **Python 3.11+** required
- **Dependencies**: Click (CLI), Rich (UI), OpenAI client library
- **Shell Detection**: Automatic detection of bash, PowerShell, cmd, and Git Bash
- **Streaming Architecture**: Real-time streaming for both AI responses and command output
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Cross-Platform Paths**: Proper path handling for Windows and Unix-like systems

### Note
This is the initial release of Shello CLI. While fully functional, expect improvements and potential breaking changes before v1.0.0. Feedback and contributions are welcome!

[0.1.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.1.0
