# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.4.x   | :white_check_mark: |
| 0.3.x   | :white_check_mark: |
| < 0.3.0 | :x:                |

## Reporting a Vulnerability

**Do not** report security vulnerabilities through public GitHub issues.

Send reports to: **mapariom05@gmail.com**

Include:
- Description and steps to reproduce
- Potential impact
- Suggested fix (if any)

**Response Timeline:**
- Acknowledgment: 48 hours
- Fix: Critical issues within 7 days, others within 30 days

## Security Best Practices

**API Keys:**
- Never commit to version control
- Use environment variables or keyring storage
- Rotate regularly

**Command Execution:**
- Review AI-suggested commands before approval
- Use allowlist/denylist patterns
- Avoid `--yolo` mode in production

**Configuration:**
- Settings files use 0o600 permissions (user-only)
- Don't share files containing credentials

## Security Considerations

- Shello executes commands with your user permissions
- All API communication uses HTTPS
- API keys stored securely via system keyring
- Command output cached locally (cleared on exit)

Thank you for helping keep Shello CLI secure! 🔒
