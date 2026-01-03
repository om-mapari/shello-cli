# Changelog

All notable changes to Shello CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-03

### Added

#### Smart Output Management v2
- **Character-Based Truncation**: Intelligent output limits based on character count (5K-20K) instead of arbitrary line counts
  - List commands: 5,000 chars (~1.2K tokens)
  - Search results: 10,000 chars (~2.5K tokens)
  - Log files: 15,000 chars (~3.7K tokens)
  - JSON output: 20,000 chars (~5K tokens)
  - Install/Build commands: 8,000 chars (~2K tokens)
  - Test commands: 15,000 chars (~3.7K tokens)
  - Safety limit: 50,000 chars (hard maximum)

- **Smart Truncation Strategies**: Different strategies for different command types
  - FIRST_ONLY: List and search commands (show beginning where results start)
  - LAST_ONLY: Log commands (show end with most recent entries)
  - FIRST_LAST: Install/build/test commands (20% first + 80% last to see both setup and results)
  - Automatic JSON analysis for large JSON outputs

- **Output Caching System**: 
  - Sequential cache IDs (cmd_001, cmd_002, cmd_003...)
  - 5-minute TTL with LRU eviction
  - 10MB maximum cache size
  - Full output always cached for later retrieval

- **Get Cached Output Tool**: New AI tool for retrieving specific sections from cached output
  - `lines="+N"` - First N lines
  - `lines="-N"` - Last N lines
  - `lines="+N,-M"` - First N + last M lines
  - `lines="N-M"` - Lines N through M (1-indexed)
  - Full output retrieval with safety limit

- **Semantic Truncation**: Intelligent line importance classification
  - CRITICAL: Errors, failures, exceptions, fatal messages
  - HIGH: Warnings, success messages, summaries
  - MEDIUM: Test results, status indicators
  - Critical lines always visible regardless of position in output
  - Adjusts truncation budget to preserve important information

- **Progress Bar Compression**: Automatic detection and compression of repetitive progress output
  - Detects percentage indicators, progress bars, spinner characters
  - Keeps only final state of each progress sequence
  - Saves hundreds of lines in install/build commands
  - Compression happens before character counting

- **Enhanced JSON Handling**: 
  - Automatic json_analyzer_tool invocation for JSON >20K chars
  - Returns jq paths showing structure instead of raw JSON
  - Raw JSON cached for retrieval via get_cached_output
  - Graceful fallback to text truncation if JSON parsing fails

- **Truncation Summary**: Comprehensive summary appended to truncated output
  - Total vs shown characters and lines
  - Strategy used (FIRST_ONLY, LAST_ONLY, FIRST_LAST)
  - Optimizations applied (compression, semantic)
  - Cache ID with expiration time
  - Suggestion for get_cached_output with appropriate line range

#### Core Improvements
- **Type Detection System**: Automatic detection of output type from command and content
  - Command pattern matching (npm install, pytest, docker logs, etc.)
  - Content pattern matching (JSON structure, test results, build output)
  - Content detection takes precedence over command detection

- **Streaming Output Enhancement**: 
  - User sees output streaming normally in real-time
  - AI receives truncated result with summary at end
  - Full output accumulated and cached in background
  - No interruption to user experience

- **Settings Manager Update**: Enhanced configuration support for output management
  - Configurable character limits per output type
  - Configurable truncation strategies
  - Semantic analysis toggle
  - Progress bar compression toggle
  - Cache settings (TTL, max size)

### Changed
- **Output Manager Architecture**: Complete rewrite with modular design
  - Replaced monolithic output_manager.py with output/ submodule
  - Separate modules: cache.py, type_detector.py, truncator.py, semantic.py, compressor.py, manager.py
  - Clean separation of concerns and testability
  - Type-safe with comprehensive dataclasses

- **Bash Tool Integration**: Updated to use new output management system
  - Shared OutputCache instance across tools
  - Automatic caching of all command output
  - Integration with truncation and summary generation

- **Tool Executor**: Enhanced to share output cache across all tools
  - Single cache instance for entire session
  - Consistent cache IDs across tool invocations

- **System Prompt**: Updated with concise output management guidance
  - Character limits and strategies
  - Cache retrieval examples
  - JSON handling behavior
  - Best practices for filtering at source

### Removed
- **Deprecated Output Manager**: Removed old line-based output_manager.py
- **Old Tests**: Removed test_output_manager.py (replaced with comprehensive new test suite)

### Testing
- **Comprehensive Test Suite**: 105+ tests for output management
  - Unit tests for all components (cache, detector, truncator, semantic, compressor)
  - Property-based tests using Hypothesis library (100+ iterations per property)
  - Integration tests for end-to-end workflows
  - 8 formal correctness properties validated:
    1. Character Limit Enforcement
    2. Line Boundary Preservation
    3. Cache Round-Trip
    4. Semantic Critical Preservation
    5. Progress Bar Compression Idempotence
    6. Type Detection Consistency
    7. JSON Analyzer Fallback
    8. Summary Completeness

### Technical Details
- **Modular Architecture**: Clean separation with output/ submodule
- **Type Safety**: Full type hints and dataclass models throughout
- **Property-Based Testing**: Formal correctness guarantees via Hypothesis
- **Zero Data Loss**: Full output always cached, retrieve any section on demand
- **Performance**: LRU cache with efficient eviction, minimal overhead on streaming

### Documentation
- Updated README with unique features and technical highlights
- Comprehensive design document (.kiro/specs/output-management/design.md)
- Detailed requirements document with EARS patterns
- Implementation tasks with property-based testing strategy

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

[0.2.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.2.0
[0.1.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.1.0
