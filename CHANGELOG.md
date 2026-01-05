# Changelog

All notable changes to Shello CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-01-06

### Added

#### Settings Management System
- **Modular Settings Architecture**: Separated internal patterns from user-changeable settings
  - `patterns.py` - Internal regex patterns and templates (NOT user-changeable)
  - `defaults.py` - Default values for user-changeable settings
  - `settings/` module - Organized settings management with public API
  - Clean separation between code constants and user configuration

- **Settings Module Structure**: New `shello_cli/settings/` package
  - `__init__.py` - Public API exports (SettingsManager, get_settings, get_api_key, etc.)
  - `models.py` - Dataclasses for settings (ProviderConfig, OutputManagementConfig, CommandTrustConfig, UserSettings)
  - `serializers.py` - YAML generation with helpful comments and documentation
  - `manager.py` - SettingsManager class with load/save/merge logic

- **YAML Configuration Format**: User-friendly YAML with inline documentation
  - Replaced JSON with YAML for better readability
  - Inline comments explaining each setting
  - Section headers for organization
  - Examples for all optional settings
  - Only configured values saved (rest use defaults)

- **Enhanced Setup Wizard**: Generates well-documented settings file
  - Creates `~/.shello_cli/user-settings.yml` with all options as comments
  - Only saves values user explicitly configured
  - Shows examples for optional settings (output_management, command_trust)
  - Includes helpful documentation in generated file

- **Configuration Management Commands**: New CLI commands for settings
  - `shello config` - Display current configuration
  - `shello config --edit` - Open settings in default editor ($EDITOR)
  - `shello config get <key>` - Get specific setting value (supports dot notation)
  - `shello config set <key> <value>` - Set specific setting value (supports dot notation)
  - `shello config reset` - Reset settings to defaults with confirmation

- **Default Merging Strategy**: Smart merging of user settings with defaults
  - User only specifies values they want to override
  - Missing values automatically filled from `defaults.py`
  - Denylist is always additive (user patterns added to defaults for safety)
  - Environment variables override file settings

- **Settings Validation**: Graceful handling of invalid values
  - Validates provider values (openai, bedrock)
  - Validates approval_mode (user_driven, ai_driven)
  - Falls back to defaults on invalid values
  - Logs warnings for invalid configuration

- **File Security**: Automatic secure file permissions
  - Sets 0o600 (user-only read/write) on settings files
  - Protects API keys and credentials
  - Creates parent directories if needed

#### Multi-Provider Support
- **AWS Bedrock Integration**: Full support for AWS Bedrock as an AI provider
  - Anthropic Claude models (3.5 Sonnet, 3 Opus, 3 Sonnet)
  - Amazon Nova models (Pro, Lite, Micro)
  - Other Bedrock foundation models
  - Multiple AWS credential methods (profile, explicit credentials, default chain)
  - Environment variable support (AWS_REGION, AWS_PROFILE, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)

- **Provider Configuration System**: Modern provider configuration using ProviderConfig dataclass

### Fixed

#### Direct Command Execution
- **Natural Language Detection**: Fixed issue where natural language questions starting with command words (e.g., "which model are you using") were incorrectly executed as shell commands
  - Added intelligent heuristics to distinguish between shell commands and natural language
  - Commands like "which python" still execute directly as shell commands
  - Questions like "which model are you using" now correctly route to AI
  - Handles question patterns: "are you", "do you", "can you", "what is", etc.
  - Special handling for ambiguous commands like "which" and "find"
  - Question marks at the end with natural language context route to AI
  - Validates Requirement 1.3: Natural language context routes to AI processing
  - Separate configurations for OpenAI-compatible APIs and AWS Bedrock
  - Support for multiple configured providers simultaneously
  - Provider-specific settings (API keys, base URLs, AWS credentials, regions)
  - Per-provider model lists and default models

- **Client Factory Pattern**: Factory function for creating appropriate client based on provider
  - `create_client()` function in `shello_cli/api/client_factory.py`
  - Automatic client selection based on provider configuration
  - Graceful error handling with helpful troubleshooting messages
  - Support for boto3 import error detection

- **Runtime Provider Switching**: Switch between providers during chat sessions
  - New `/switch` command in chat interface
  - Interactive provider selection menu
  - Conversation history preservation across provider switches
  - Automatic cache clearing and agent recreation
  - Display confirmation with new provider and model

- **Enhanced Setup Wizard**: Interactive provider selection and configuration
  - Provider selection menu (OpenAI-compatible API vs AWS Bedrock)
  - OpenAI-compatible setup flow with API provider presets (OpenAI, OpenRouter, Custom)
  - AWS Bedrock setup flow with credential method selection
  - Support for configuring multiple providers
  - Model suggestions based on selected provider

- **Environment Variable Support**: All credentials support environment variable overrides
  - OpenAI: `OPENAI_API_KEY`
  - Bedrock: `AWS_REGION`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - Environment variables take precedence over configuration files

#### Command Trust and Safety System
- **Trust Manager**: Evaluates commands before execution through 5-step flow (Denylist → YOLO → Allowlist → AI Safety → Approval)
- **Pattern Matcher**: Supports exact match, wildcards (`git *`), and regex (`^git (status|log)$`)
- **Approval Dialog**: Interactive UI for command approval with keyboard controls (A/D)
- **Default Allowlist**: Safe commands execute automatically (ls, pwd, git status, cat, grep, etc.)
- **Default Denylist**: Dangerous commands require approval (rm -rf /, dd, mkfs, format, etc.)
- **YOLO Mode**: Bypass approval checks via config or `--yolo` flag (still respects denylist)
- **AI Safety Integration**: Required `is_safe` parameter in bash tool for AI command evaluation
- **Configuration**: Flexible trust settings in `~/.shello_cli/user-settings.json`
  - `approval_mode`: "user_driven" (default) or "ai_driven"
  - `allowlist`: User patterns replace defaults
  - `denylist`: User patterns added to defaults (additive for safety)

### Changed

#### Settings Management Changes
- **Settings File Format**: Migrated from JSON to YAML
  - `~/.shello_cli/user-settings.json` → `~/.shello_cli/user-settings.yml`
  - Backward compatibility maintained (old JSON files still work)
  - Automatic migration on first run with new version

- **Constants Organization**: Split `constants.py` into focused modules
  - `patterns.py` - Internal patterns (COMMAND_PATTERNS, CONTENT_PATTERNS, etc.)
  - `defaults.py` - User-changeable defaults (DEFAULT_CHAR_LIMITS, DEFAULT_STRATEGIES, etc.)
  - Updated all imports across codebase

- **Settings Manager Location**: Moved to dedicated module
  - `utils/settings_manager.py` → `settings/manager.py`
  - Backward compatibility via re-exports from `utils/settings_manager.py`
  - No breaking changes for existing code

#### Multi-Provider Support Changes
- **Settings Manager**: Extended with provider configuration support
  - New `ProviderConfig` dataclass for provider-specific settings
  - `openai_config` and `bedrock_config` fields in UserSettings
  - Helper methods: `get_provider()`, `set_provider()`, `get_provider_config()`, `is_provider_configured()`, `get_available_providers()`
  - Backward compatibility maintained for existing `get_api_key()` and `get_base_url()` methods

- **ShelloAgent**: Refactored to use dependency injection
  - Constructor now accepts `client` parameter instead of creating its own
  - Removed `api_key`, `base_url`, `model` parameters from constructor
  - Supports both ShelloClient and ShelloBedrockClient via Union type
  - Cleaner separation of concerns

- **CLI Integration**: Updated to use factory pattern and support provider switching
  - `create_new_session()` uses client factory
  - New `switch_provider()` function for runtime switching
  - Enhanced error handling with provider-specific messages
  - `/switch` command added to chat loop

- **UI Renderer**: Added `/switch` command to help display

#### Command Trust and Safety Changes
- **Bash Tool**: Added required `is_safe` parameter, trust evaluation before execution
- **Direct Executor**: Integrated with trust system for direct commands
- **Settings Manager**: New CommandTrustConfig with validation and safe defaults
- **Tool Definitions**: Updated bash tool description with SAFETY section

### Testing

#### Settings Management Tests
- **Comprehensive Test Coverage**: 400+ tests for settings system
  - Settings loading and merging with defaults
  - YAML serialization with comments
  - Configuration validation and fallback
  - File permissions and security
  - Environment variable overrides
  - Dot notation for get/set commands

- **Property-Based Tests**: Formal correctness validation
  - Property 1: Settings Round-Trip (serialize → deserialize produces equivalent settings)
  - Property 2: Default Merging (partial settings filled with defaults)
  - Property 3: Denylist Immutability (user denylist always includes defaults)
  - Property 4: Environment Variable Fallback (env vars used when config missing)
  - Property 5: Singleton Identity (all get_instance() calls return same object)

#### Multi-Provider Support Tests
- **Client Factory Tests**: 542 lines of comprehensive tests
  - Test creating ShelloClient for OpenAI provider
  - Test creating ShelloBedrockClient for Bedrock provider
  - Test error handling for invalid providers and missing configuration
  - Test boto3 import error handling

- **Settings Manager Tests**: Extended with provider configuration tests
  - Test loading settings with different providers
  - Test provider config resolution with environment variables
  - Test available providers detection

#### Command Trust and Safety Tests
- 550+ tests covering pattern matching, trust evaluation, configuration, and integration
- 8 property-based tests validating correctness properties

### Documentation

#### Settings Management Documentation
- **README Updates**: Configuration section rewritten
  - New "Configuration Management" section with CLI commands
  - YAML configuration examples with inline comments
  - Explanation of default merging strategy
  - Updated all JSON examples to YAML

- **DEVELOPMENT_SETUP.md Updates**: Comprehensive developer documentation
  - New CLI commands section (config --edit, get, set, reset)
  - YAML configuration format with examples
  - Updated configuration hierarchy with defaults.py
  - Project structure showing new settings/ module
  - Updated troubleshooting for YAML validation

- **Design Documentation**: Complete design document
  - Architecture overview with file responsibilities
  - Data flow diagrams (loading and saving)
  - Example generated user-settings.yml
  - Correctness properties with validation strategy
  - Error handling and testing strategy

#### Multi-Provider Support Documentation
- **README Updates**: Comprehensive multi-provider documentation
  - New "AI Provider Support" section with provider overview
  - Runtime provider switching examples and workflow
  - Environment variable documentation for all providers
  - Configuration examples for OpenAI, Bedrock, and multiple providers
  - Updated commands section with `/switch` command

- **DEVELOPMENT_SETUP.md Updates**: Developer-focused provider documentation
  - Provider-specific configuration examples
  - Multiple provider setup instructions
  - Environment variable configuration for all providers
  - Updated troubleshooting section with provider-specific errors
  - Updated project structure showing new files

- **requirements.txt**: Added boto3 with optional dependency comment
  - Marked as optional dependency for AWS Bedrock support
  - Installation instructions for users who only need OpenAI-compatible APIs

#### Command Trust and Safety Documentation
- Comprehensive README section on Command Trust and Safety
- Enhanced inline documentation with examples
- Complete design document with architecture and evaluation flow

### Technical Details

#### Settings Management Technical Details
- **Modular Architecture**: Clean separation of concerns
  - Settings models (dataclasses)
  - Serialization logic (YAML with comments)
  - Management logic (load/save/merge)
  - Public API (convenience functions)

- **Type Safety**: Full type hints throughout
  - Dataclasses for all settings structures
  - Optional fields with proper defaults
  - Type-safe merging and validation

- **Backward Compatibility**: Zero breaking changes
  - Old JSON files still work
  - Existing imports continue to work via re-exports
  - Automatic migration path

- **Security First**: Secure by default
  - Automatic file permissions (0o600)
  - No credentials in error messages
  - Environment variable support for sensitive data

#### Multi-Provider Support Technical Details
- **Modular Provider System**: Clean separation with client factory pattern
- **Type Safety**: Union types for client interfaces, full type hints
- **Backward Compatibility**: Existing OpenAI configurations continue to work
- **Graceful Degradation**: Helpful error messages when boto3 is not installed
- **Zero Breaking Changes**: Existing users can continue using OpenAI without changes

### Security
- Protection against dangerous commands with denylist
- Audit logging of all trust decisions
- Safe defaults on errors or invalid configuration

## [0.3.0] - 2026-01-04

### Added

#### Direct Command Execution
- **Command Detection System**: Automatically detects and routes direct shell commands vs AI queries
  - Recognizes common Unix commands (ls, pwd, cd, cat, grep, find, etc.)
  - Recognizes Windows commands (dir, cls, type, copy, del, etc.)
  - Routes recognized commands directly to shell without AI processing
  - Falls back to AI for natural language queries and complex requests

- **Direct Executor**: Fast command execution without AI overhead
  - Executes commands directly in current shell environment
  - Maintains directory state across commands (cd persistence)
  - Automatic shell detection (bash, PowerShell, cmd)
  - Real-time output streaming
  - Integrated with output caching system
  - 30-second timeout for safety

- **Context Manager**: Tracks direct command history for AI awareness
  - Records last 10 direct commands with output
  - Provides context to AI when switching from direct to AI mode
  - Includes cache IDs for AI to retrieve full output
  - Marks commands as sent to avoid duplicate context
  - Clears on /new command

- **Enhanced Prompt**: Directory-aware prompt display
  - Shows current working directory in prompt
  - Abbreviates home directory as ~
  - Truncates long paths for readability (40 char max)
  - Color-coded path display (orange)
  - Updates dynamically as directory changes

- **Direct Command UI**: Clean rendering for direct command execution
  - Terminal-style header without AI branding
  - Shows user@hostname and current directory
  - Command prompt with $ indicator
  - Distinguishes direct execution from AI-processed commands

### Changed

- **Cache System Improvements**:
  - Removed TTL expiration - cache persists for entire conversation
  - Increased cache size from 10MB to 100MB
  - Cache cleared only on /new command or app exit
  - Counter resets on new conversation for clean cache IDs
  - Updated all references to remove expiration mentions

- **PowerShell Output Handling**:
  - Strips trailing whitespace from each line (removes column padding)
  - Reduces character count by 2-3x for PowerShell commands
  - Preserves output structure and readability
  - Applied consistently across bash_tool and direct_executor

- **Tool Result Metadata**:
  - Added truncation metadata to tool results sent to AI
  - Includes cache_id, total_chars, shown_chars, total_lines, shown_lines
  - AI can see truncation status and make informed decisions
  - Enables smarter use of get_cached_output tool

- **API Debug Logging**:
  - Added detailed HTTP request/response logging for OpenAI API
  - Logs full message content, tool calls, and parameters
  - Shows token usage and model information
  - Helps debug tool calling and prompt issues
  - Enabled via debug flag in ShelloClient

- **Agent Cache Management**:
  - Added clear_cache() method to ShelloAgent
  - Automatically clears cache on /new command
  - Clears cache on Ctrl+C exit
  - Provides get_bash_tool() for shared caching with direct executor

### Testing

- **Direct Command Execution Tests**: 233 tests for direct executor
  - Command execution across different shells
  - Directory change handling
  - Error handling and timeouts
  - Output caching integration

- **Command Detection Tests**: 201 tests for command detector
  - Direct command recognition
  - AI query detection
  - Edge cases and empty input

- **Context Manager Tests**: 241 tests for context management
  - Command recording and history
  - AI context generation
  - History limits and clearing

- **Cache Sequential ID Tests**: 193 tests for cache ID generation
  - Sequential ID generation
  - Counter reset on clear
  - LRU eviction behavior

- **CLI Integration Tests**: 119 tests for end-to-end workflows
  - Direct command execution flow
  - AI query routing
  - Context switching

- **User Input Tests**: 235 tests for prompt display
  - Directory abbreviation
  - Path truncation
  - Prompt formatting

- **Output Utils Tests**: 106 tests for PowerShell padding removal
  - Line padding stripping
  - Structure preservation
  - Edge cases

### Technical Details

- **Modular Command System**: New commands/ submodule with clean separation
  - command_detector.py - Input classification
  - direct_executor.py - Direct command execution
  - context_manager.py - History and context tracking
- **Shared Caching**: Direct executor and bash_tool share same cache instance
- **Zero Latency**: Direct commands execute immediately without API calls
- **Seamless Integration**: Transparent switching between direct and AI modes

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

[Unreleased]: https://github.com/om-mapari/shello-cli/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.4.0
[0.3.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.3.0
[0.2.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.2.0
[0.1.0]: https://github.com/om-mapari/shello-cli/releases/tag/v0.1.0
