# Contributing to ClawChat

Thank you for your interest in contributing to ClawChat! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Security Guidelines](#security-guidelines)
- [Community](#community)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive environment for all contributors.

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher (for frontend development)
- Git
- A GitHub account

### Setting Up Your Development Environment

1. **Fork the Repository**
   - Click the "Fork" button on the top right of the repository page
   - Clone your fork locally:
     ```bash
     git clone https://github.com/YOUR_USERNAME/clawchat.git
     cd clawchat
     ```

2. **Set Up Python Environment**
   ```bash
   # Create a virtual environment
   python -m venv venv
   
   # Activate the virtual environment
   # On Linux/Mac:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   
   # Install dependencies
   pip install -r backend/requirements.txt
   pip install -r tests/requirements.txt
   ```

3. **Set Up Frontend Environment**
   ```bash
   # Install Playwright browsers for testing
   npx playwright install chromium
   ```

4. **Configure Git**
   ```bash
   # Add the original repository as upstream
   git remote add upstream https://github.com/original-owner/clawchat.git
   
   # Fetch the latest changes
   git fetch upstream
   ```

## Development Workflow

### Branch Strategy

We follow a feature branch workflow:

1. **Main Branches:**
   - `main`: Production-ready code
   - `develop`: Integration branch for features

2. **Feature Branches:**
   - Create branches from `develop`
   - Use descriptive names: `feature/description`, `fix/issue-number`, `docs/topic`

### Creating a New Feature

1. **Sync with Upstream**
   ```bash
   git checkout develop
   git pull upstream develop
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Write code following our [coding standards](#coding-standards)
   - Add tests for new functionality
   - Update documentation as needed

4. **Run Tests Locally**
   ```bash
   # Run all tests
   ./run_tests.sh
   
   # Run specific test types
   ./run_tests.sh unit
   ./run_tests.sh integration
   ```

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

### Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, missing semi-colons, etc.)
- `refactor:` Code refactoring
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

Example:
```
feat: add file upload functionality

- Implement secure file upload endpoint
- Add validation for file types
- Update API documentation

Closes #123
```

## Pull Request Process

### Before Submitting a PR

1. **Ensure Tests Pass**
   ```bash
   ./run_tests.sh ci
   ```

2. **Check Code Quality**
   ```bash
   # Run linters
   black --check backend/ tests/
   flake8 backend/ tests/
   mypy backend/
   ```

3. **Update Documentation**
   - Update README.md if needed
   - Add docstrings to new functions
   - Update API documentation

4. **Review Your Changes**
   ```bash
   git diff develop
   ```

### Creating a Pull Request

1. **Push to Your Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub**
   - Go to the original repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

3. **PR Requirements**
   - Descriptive title and description
   - Link to related issues
   - Screenshots for UI changes
   - Confirmation that tests pass
   - Documentation updates

### PR Review Process

1. **Automated Checks**
   - CI/CD pipeline runs automatically
   - All checks must pass before review

2. **Code Review**
   - At least one maintainer must approve
   - Address all review comments
   - Keep the PR updated with develop

3. **Merge Approval**
   - Squash commits into logical units
   - Use "Squash and merge" for feature branches
   - Delete the feature branch after merge

## Coding Standards

### Python Code

1. **Formatting**
   - Use [Black](https://black.readthedocs.io/) for formatting
   - Line length: 88 characters
   - Use double quotes for strings

2. **Imports**
   ```python
   # Standard library imports
   import os
   import sys
   
   # Third-party imports
   import websockets
   import yaml
   
   # Local imports
   from .security import SecurityManager
   ```

3. **Type Hints**
   ```python
   def process_file(file_path: str, max_size: int = 1024) -> Optional[bytes]:
       """Process a file and return its content."""
       # Function body
   ```

4. **Error Handling**
   ```python
   try:
       result = await process_data(data)
   except ValueError as e:
       logger.error(f"Invalid data: {e}")
       raise
   except Exception as e:
       logger.exception("Unexpected error")
       raise RuntimeError("Processing failed") from e
   ```

### JavaScript/HTML/CSS

1. **JavaScript**
   - Use ES6+ features
   - Prefer `const` and `let` over `var`
   - Use async/await for asynchronous code

2. **HTML**
   - Semantic HTML5 elements
   - Accessibility attributes (aria-labels, alt text)
   - Responsive design

3. **CSS**
   - Use CSS variables for theming
   - Mobile-first approach
   - BEM naming convention

### Security Guidelines

1. **Input Validation**
   ```python
   # Always validate user input
   def validate_path(user_path: str) -> bool:
       # Prevent path traversal
       normalized = os.path.normpath(user_path)
       return not os.path.isabs(normalized) and '..' not in normalized
   ```

2. **No Secrets in Code**
   - Use environment variables
   - Never commit API keys or passwords
   - Use GitHub Secrets for CI/CD

3. **Dependency Security**
   - Regularly update dependencies
   - Use `safety check` to scan for vulnerabilities
   - Pin versions in requirements.txt

## Testing Guidelines

### Writing Tests

1. **Test Structure**
   ```python
   import pytest
   
   class TestFileOperations:
       """Test suite for file operations."""
       
       @pytest.fixture
       def temp_file(self, tmp_path):
           """Create a temporary file for testing."""
           file_path = tmp_path / "test.txt"
           file_path.write_text("test content")
           return file_path
       
       def test_file_read(self, temp_file):
           """Test reading a file."""
           content = read_file(temp_file)
           assert content == "test content"
       
       @pytest.mark.integration
       def test_file_upload_integration(self):
           """Integration test for file upload."""
           # Test with actual server
   ```

2. **Test Coverage**
   - Aim for 80%+ coverage
   - Test edge cases and error conditions
   - Mock external dependencies

3. **Performance Tests**
   ```python
   @pytest.mark.performance
   def test_concurrent_connections(self):
       """Test server performance with concurrent connections."""
       # Performance testing code
   ```

### Running Tests

```bash
# Run all tests with coverage
./run_tests.sh

# Run specific test types
./run_tests.sh unit      # Unit tests only
./run_tests.sh integration  # Integration tests
./run_tests.sh security   # Security tests
./run_tests.sh ci        # CI mode (strict)

# Run with pytest directly
pytest tests/ -v --cov=backend --cov-report=html
```

## Documentation

### Code Documentation

1. **Docstrings**
   ```python
   def process_message(message: str, user: User) -> ProcessResult:
       """
       Process an incoming chat message.
       
       Args:
           message: The message text to process
           user: The user who sent the message
           
       Returns:
           ProcessResult containing processed message and metadata
           
       Raises:
           ValueError: If message is empty or invalid
           SecurityError: If user doesn't have permission
       """
       # Function implementation
   ```

2. **README Updates**
   - Update README.md for new features
   - Include setup instructions
   - Add examples and screenshots

### API Documentation

- Update API documentation in `docs/api.md`
- Include request/response examples
- Document authentication requirements

## Security Guidelines

### Reporting Security Issues

**DO NOT** report security vulnerabilities through public GitHub issues.

1. **Email Security Team**
   - Send details to security@clawchat.example.com
   - Include steps to reproduce
   - Describe potential impact

2. **Responsible Disclosure**
   - We will acknowledge receipt within 48 hours
   - We'll work with you to understand and fix the issue
   - Public disclosure after fix is released

### Security Best Practices

1. **Code Security**
   - Validate all user input
   - Use parameterized queries
   - Implement rate limiting
   - Use secure defaults

2. **Dependencies**
   - Regularly update dependencies
   - Use `safety check` in CI/CD
   - Monitor for security advisories

3. **Secrets Management**
   - Never commit secrets
   - Use environment variables
   - Rotate keys regularly

## Community

### Getting Help

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For questions and discussions
- **Slack**: Join our community Slack (link in README)

### Recognition

Contributors are recognized in:
- GitHub contributors list
- Release notes
- Project documentation

### Becoming a Maintainer

After consistent quality contributions, you may be invited to become a maintainer. Maintainers:
- Review and merge pull requests
- Triage issues
- Help with project direction
- Mentor new contributors

## License

By contributing to ClawChat, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).

---

Thank you for contributing to ClawChat! Your efforts help make secure communication accessible to everyone.