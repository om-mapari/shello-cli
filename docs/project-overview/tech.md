# Shello CLI - Tech Stack & Developer Runbook

## Language & Runtime
- Python 3.11+ (officially supports 3.11, 3.12, 3.13)
- Type hints used throughout

## Build System
- Hatchling (build backend)
- PyInstaller for standalone executables (configured in `shello.spec`)
- Version managed in `shello_cli/__init__.py`

## Key Dependencies
- `click` - CLI framework and routing
- `rich` - Terminal UI (Console, Markdown, Live) and layout rendering
- `prompt_toolkit` - Stateful user input handling
- `pydantic` - Settings validation and model definitions
- `openai` - OpenAI API client (and compatible gateways like OpenRouter)
- `boto3` - AWS Bedrock client for Nova/Claude invocation
- `paramiko` - Native SSH client for remote execution
- `pyyaml` - Parser and serializer for settings files
- `keyring` - Secure local credential storage

---

## Developer Runbook & Execution Mechanics

### 1. Stateful Process Control
Local shell commands run within a stateful `subprocess.Popen` execution engine.
* **Background Threads**: Non-blocking reader threads collect stdout/stderr in a thread-safe `queue.Queue`.
* **Soft Timeout (2s)**: Exceeding the deadline yields partial output to the LLM with `error_type="soft_timeout"` while keeping the subprocess running.
* **Sequential Cache Indexing**: Streaming outputs use a `GeneratorWrapper`. When the stream generator completes, the resulting `ToolResult` holds the `truncation_info`. The output pipeline avoids double-caching by checking for this wrapper metadata, ensuring cache IDs (`cmd_001`, `cmd_002`, etc.) remain sequential.

### 2. Common Commands

```bash
# Run application
python main.py

# Run unit and property tests (RECOMMENDED - excludes integration tests that need live API keys)
pytest tests/ -x -q --tb=short -m "not integration"

# Run tests with coverage (excluding integration)
pytest tests/ -m "not integration" --cov=shello_cli --cov-report=html

# Run specific test file
pytest tests/test_bash_tool.py -x -q --tb=short

# Run ALL tests including integration (requires valid API keys configured)
pytest tests/ --tb=short -q

# Build standalone executable (Windows)
build.bat

# Install in development mode
uv pip install -e .
```

> **⚠️ Integration Testing Note**: Tests in `test_openai_client_integration.py` and `test_message_processor_integration.py` are marked as `integration` and make live network calls. They will fail with 401 errors if keys are not configured. Always run with `-m "not integration"` during local development.

---

## Configuration Files
- `pyproject.toml` - Metadata, dependencies, Hatchling configuration, and Pytest configs
- `pytest.ini` - Custom markers (e.g. `integration`, `no_mock_settings`)
- `shello.spec` - PyInstaller build specification (including Paramiko & Cryptography hidden imports)
