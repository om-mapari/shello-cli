# Contributing to Shello CLI

Thank you for your interest in contributing to Shello CLI! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Respect differing viewpoints and experiences

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report:
- Check the [existing issues](https://github.com/om-mapari/shello-cli/issues)
- Try the latest version to see if the bug still exists
- Collect information about your environment

When creating a bug report, include:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Environment details (OS, version, etc.)

Use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.md).

### Suggesting Features

Feature suggestions are welcome! Please:
- Check if the feature has already been suggested
- Provide a clear use case
- Explain why this feature would be useful
- Consider if it fits the project's scope

Use the [feature request template](.github/ISSUE_TEMPLATE/feature_request.md).

### Pull Requests

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then:
   git clone https://github.com/YOUR_USERNAME/shello-cli.git
   cd shello-cli
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make your changes**
   - Write clear, commented code
   - Follow the existing code style
   - Add tests for new features
   - Update documentation as needed

4. **Test your changes**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Test the executable build
   pyinstaller shello.spec --clean
   dist/shello --version
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```
   
   Commit message format:
   - `Add feature: ...` for new features
   - `Fix: ...` for bug fixes
   - `Update: ...` for updates to existing features
   - `Docs: ...` for documentation changes

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```
   Then create a Pull Request on GitHub.

## Development Setup

### Prerequisites
- Python 3.11 or higher
- pip
- git

### Setup
```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/shello-cli.git
cd shello-cli

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest hypothesis pyinstaller

# Run tests
pytest tests/ -v
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Use meaningful variable names

Example:
```python
def process_user_input(user_input: str) -> dict:
    """
    Process user input and return structured data.
    
    Args:
        user_input: Raw input string from user
        
    Returns:
        Dictionary containing processed input data
    """
    # Implementation
    pass
```

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for good test coverage
- Use property-based testing with Hypothesis where appropriate

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_openai_client.py -v

# Run with coverage
pytest tests/ --cov=shello_cli
```

## Documentation

When adding features:
- Update README.md if user-facing
- Update SETUP.md for configuration changes
- Add entries to CHANGELOG.md
- Update docstrings and comments
- Add examples if helpful

## Project Structure

```
shello_cli/
├── agent/              # AI agent implementation
├── api/                # API clients (OpenAI, etc.)
├── chat/               # Chat session management
├── commands/           # CLI command implementations
├── tools/              # Tool implementations
├── ui/                 # User interface components
├── utils/              # Utility functions
└── types.py            # Type definitions

tests/                  # Test files
docs/                   # Documentation
.github/                # GitHub templates and workflows
```

## Release Process

Maintainers handle releases:

1. Update version in `shello_cli/__init__.py`
2. Update CHANGELOG.md
3. Create and push version tag
4. GitHub Actions builds and publishes release

## Questions?

- Open an issue for questions
- Check existing documentation
- Look at closed issues for similar questions

## Recognition

Contributors will be:
- Listed in release notes
- Credited in the project
- Appreciated by the community!

Thank you for contributing to Shello CLI! 🎉
