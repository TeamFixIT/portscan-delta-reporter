# Development Manager Documentation

## Overview

The `dev_manager.py` script is a comprehensive development environment manager for the Port Scanner Delta Reporter project. It replaces traditional npm scripts with pure Python alternatives, providing a unified development workflow across all project components.

## Features

- **Unified Development Environment**: Single command to set up and manage the entire development stack
- **Cross-Platform Support**: Works on Windows, macOS, and Linux
- **Automated Setup**: Handles virtual environments, dependencies, and database initialization
- **Development Server Management**: Starts and manages backend and client services
- **Git Configuration**: Automated Git setup with commit signing support
- **Code Quality Tools**: Integrated linting, formatting, and testing
- **Clean Shutdown**: Graceful process management with signal handling

## Installation

The `dev_manager.py` script is located in the `scripts/` directory and requires Python 3.7 or higher.

```bash
# Make sure you're in the project root
cd /path/to/portscan_delta_reporter

# Run the development manager
python scripts/dev_manager.py --help
```

## Commands

### setup

Sets up the complete development environment including virtual environments, dependencies, and database initialization.

```bash
python scripts/dev_manager.py setup
```

**What it does:**

- Checks system requirements (Python 3, pip)
- Creates virtual environments for backend and client
- Installs Python dependencies from requirements.txt
- Initializes the database with tables
- Downloads frontend assets (Bootstrap, Chart.js) or configures CDN usage
- Verifies setup completion

**Prerequisites:**

- Python 3.7+
- pip3
- Internet connection (for dependency downloads)

### dev

Starts the development environment with hot reloading and debug mode.

```bash
# Start backend only
python scripts/dev_manager.py dev

# Start backend with test client
python scripts/dev_manager.py dev --with-client
```

**What it does:**

- Starts Flask backend server on `http://localhost:5000`
- Enables debug mode and hot reloading
- Optionally starts test client for scanning
- Provides real-time logging output
- Handles graceful shutdown on Ctrl+C

**Services Started:**

- **Backend Server**: Flask application with debug mode
- **Test Client**: (Optional) Scanning client for development testing

**Environment Variables:**

- `FLASK_ENV=development`
- `FLASK_DEBUG=1`
- `LOG_LEVEL=DEBUG` (for client)
- `SERVER_URL=http://localhost:5000` (for client)

### test

Runs the complete test suite across all project components.

```bash
python scripts/dev_manager.py test
```

**What it does:**

- Runs backend tests using pytest
- Runs client tests using pytest
- Provides detailed test output with `-v` flag
- Reports test coverage and results
- Exits with error code if any tests fail

**Test Structure:**

```
backend/tests/          # Backend unit and integration tests
client/tests/           # Client component tests
```

### lint

Runs code quality checks using pylint across all Python code.

```bash
python scripts/dev_manager.py lint
```

**What it does:**

- Lints backend code in `app/` directory
- Lints client code in `src/` directory
- Reports code quality issues and suggestions
- Follows PEP 8 standards
- Provides detailed linting reports

### format

Formats all Python code using Black formatter.

```bash
python scripts/dev_manager.py format
```

**What it does:**

- Formats backend code in `app/` directory
- Formats client code in `src/` directory
- Applies consistent code style
- Follows Black's opinionated formatting
- Modifies files in-place

### clean

Cleans up generated files and Python cache.

```bash
python scripts/dev_manager.py clean
```

**What it does:**

- Removes `__pycache__` directories
- Deletes `.pyc` files
- Cleans up temporary files
- Provides detailed cleanup report

### git-setup

Interactive Git configuration setup with commit signing support.

```bash
python scripts/dev_manager.py git-setup
```

**What it does:**

- Configures Git user name and email
- Sets up useful Git defaults
- Configures commit signing (SSH or GPG)
- Generates SSH keys if needed
- Provides setup instructions for GitHub integration

**Configuration Options:**

- **SSH Signing**: Recommended for simplicity
- **GPG Signing**: Traditional method with more security features
- **Skip Signing**: For basic setup without commit signing

### git-verify

Verifies Git configuration and signing setup.

```bash
python scripts/dev_manager.py git-verify
```

**What it does:**

- Checks Git user configuration
- Verifies commit signing setup
- Tests signing key configuration
- Provides setup completion status

## Project Structure

The dev_manager.py script expects the following project structure:

```
portscan_delta_reporter/
├── scripts/
│   └── dev_manager.py          # This script
├── backend/                    # Flask backend (was server/)
│   ├── venv/                   # Python virtual environment
│   ├── requirements.txt        # Python dependencies
│   ├── run.py                  # Flask application entry point
│   ├── app/                    # Application code
│   └── tests/                  # Backend tests
├── client/                     # Scanning client
│   ├── venv/                   # Python virtual environment
│   ├── requirements.txt        # Python dependencies
│   ├── src/                    # Client source code
│   └── tests/                  # Client tests
└── frontend/                   # Frontend assets (optional)
    └── static/
        ├── css/
        └── js/
```

## Development Workflow

### Initial Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/TeamFixIT/portscan-delta-reporter.git
   cd portscan-delta-reporter
   ```

2. **Run setup**

   ```bash
   python scripts/dev_manager.py setup
   ```

3. **Configure Git (optional)**
   ```bash
   python scripts/dev_manager.py git-setup
   ```

### Daily Development

1. **Start development environment**

   ```bash
   python scripts/dev_manager.py dev
   ```

2. **Run tests before committing**

   ```bash
   python scripts/dev_manager.py test
   ```

3. **Format code**

   ```bash
   python scripts/dev_manager.py format
   ```

4. **Check code quality**
   ```bash
   python scripts/dev_manager.py lint
   ```

### Code Quality Workflow

```bash
# Format code
python scripts/dev_manager.py format

# Check linting
python scripts/dev_manager.py lint

# Run tests
python scripts/dev_manager.py test

# Clean up if needed
python scripts/dev_manager.py clean
```

## Environment Configuration

### Backend Environment Variables

The script configures the following environment variables for backend development:

- `FLASK_ENV=development`: Enables development mode
- `FLASK_DEBUG=1`: Enables debug mode and hot reloading
- Database connection: Uses SQLite by default for development

### Client Environment Variables

For client development:

- `LOG_LEVEL=DEBUG`: Enables detailed logging
- `SERVER_URL=http://localhost:5000`: Points to local development server

## Dependencies

### System Requirements

- **Python 3.7+**: Required for all components
- **pip3**: Python package installer
- **Git**: Version control (for git-setup command)
- **Internet Connection**: For downloading dependencies and assets

### Python Packages

The script automatically installs packages from:

- `backend/requirements.txt`: Flask, SQLAlchemy, etc.
- `client/requirements.txt`: nmap-python, requests, etc.

### Development Tools

Automatically installed development tools:

- **pytest**: Testing framework
- **pylint**: Code quality checker
- **black**: Code formatter

### Frontend Assets

Optionally downloads:

- **Bootstrap 5.3.0**: CSS framework
- **Chart.js 4.4.0**: Charting library

## Troubleshooting

### Common Issues

#### Virtual Environment Issues

**Problem**: Virtual environment creation fails

```bash
Error: Failed to create virtual environment
```

**Solution**:

```bash
# Ensure venv module is available
python -m venv --help

# On Ubuntu/Debian, install python3-venv
sudo apt install python3-venv

# On CentOS/RHEL, install python3-venv
sudo yum install python3-venv
```

#### Permission Issues

**Problem**: Permission denied when creating directories

```bash
PermissionError: [Errno 13] Permission denied
```

**Solution**:

```bash
# Ensure you have write permissions to the project directory
chmod -R u+w portscan_delta_reporter/

# Or run with appropriate permissions
sudo python scripts/dev_manager.py setup
```

#### Port Already in Use

**Problem**: Flask server can't start

```bash
OSError: [Errno 48] Address already in use
```

**Solution**:

```bash
# Find and kill process using port 5000
lsof -i :5000
kill -9 <PID>

# Or use a different port
export FLASK_RUN_PORT=5001
python scripts/dev_manager.py dev
```

#### Git Configuration Issues

**Problem**: Git commands fail

```bash
Error: Git not found in PATH
```

**Solution**:

```bash
# Install Git
# macOS: xcode-select --install
# Ubuntu: sudo apt install git
# Windows: Download from https://git-scm.com/

# Verify installation
git --version
```

### Debug Mode

To debug the dev_manager.py script itself:

```bash
# Add debug prints to the script
export PYTHONPATH="."
python -u scripts/dev_manager.py setup

# Or run with Python debugger
python -m pdb scripts/dev_manager.py dev
```

### Log Files

Application logs are available at:

- Backend logs: Console output during development
- Client logs: `client/logs/` directory
- Test logs: pytest output with `-v` flag

## Configuration Files

### Backend Configuration

The backend uses environment variables and Flask configuration:

- Development database: `backend/instance/portscan_dev.db`
- Flask configuration: Set via environment variables

### Client Configuration

Client configuration files:

- `client/config.yml`: Main configuration
- `client/config.example.yml`: Example configuration

### Git Configuration

Git settings managed by the script:

- Global Git configuration: `~/.gitconfig`
- SSH keys: `~/.ssh/`
- GPG keys: `~/.gnupg/`

## Integration

### IDE Integration

#### VS Code

Add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Setup Dev Environment",
      "type": "shell",
      "command": "python",
      "args": ["scripts/dev_manager.py", "setup"],
      "group": "build"
    },
    {
      "label": "Start Development Server",
      "type": "shell",
      "command": "python",
      "args": ["scripts/dev_manager.py", "dev"],
      "group": "test",
      "isBackground": true
    },
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "python",
      "args": ["scripts/dev_manager.py", "test"],
      "group": "test"
    }
  ]
}
```

#### PyCharm

Configure as external tools:

1. File → Settings → Tools → External Tools
2. Add new tool with command: `python scripts/dev_manager.py`
3. Set working directory to project root

### CI/CD Integration

#### GitHub Actions

Example workflow:

```yaml
name: Development Workflow
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.9"
      - name: Setup Environment
        run: python scripts/dev_manager.py setup
      - name: Run Tests
        run: python scripts/dev_manager.py test
      - name: Check Code Quality
        run: python scripts/dev_manager.py lint
```

## Migration Notes

### From npm Scripts

If migrating from an npm-based setup:

**Old**:

```bash
npm install
npm run dev
npm test
```

**New**:

```bash
python scripts/dev_manager.py setup
python scripts/dev_manager.py dev
python scripts/dev_manager.py test
```

### From Docker Compose

If migrating from Docker Compose development:

**Old**:

```bash
docker-compose up -d
docker-compose exec backend python -m pytest
```

**New**:

```bash
python scripts/dev_manager.py dev
python scripts/dev_manager.py test
```

## Best Practices

### Development

1. **Always run setup first**: After cloning or pulling major changes
2. **Use format before committing**: Ensures consistent code style
3. **Run tests regularly**: Catch issues early
4. **Clean up periodically**: Remove cache files and temporary data

### Code Quality

1. **Follow linting suggestions**: Address pylint warnings
2. **Write tests**: Maintain good test coverage
3. **Use meaningful commit messages**: Follow conventional commit format
4. **Sign commits**: Use the git-setup command for security

### Performance

1. **Use virtual environments**: Isolates dependencies
2. **Profile during development**: Monitor performance regularly
3. **Optimize imports**: Remove unused imports
4. **Monitor resource usage**: Watch memory and CPU usage during development

## API Reference

### DevManager Class

The main class that provides all development management functionality.

#### Methods

##### `__init__(self)`

Initializes the DevManager with project directory paths.

##### `setup(self)`

Sets up the complete development environment.

**Raises**: `SystemExit` if prerequisites not met

##### `dev(self)`

Starts the development environment with hot reloading.

**Signals**: Handles SIGINT and SIGTERM for graceful shutdown

##### `test(self) -> bool`

Runs all tests and returns success status.

**Returns**: `True` if all tests pass, `False` otherwise

##### `lint(self)`

Runs code quality checks with pylint.

##### `format_code(self)`

Formats code with Black formatter.

##### `clean(self)`

Cleans up generated files and cache.

##### `setup_git_signing(self)`

Interactive Git configuration with signing setup.

##### `verify_git_setup(self)`

Verifies Git configuration completeness.

### Configuration Properties

- `self.root_dir`: Project root directory
- `self.backend_dir`: Backend code directory
- `self.client_dir`: Client code directory
- `self.frontend_dir`: Frontend assets directory
- `self.processes`: List of managed processes

## Contributing

To contribute to the dev_manager.py script:

1. **Follow the existing code style**: Use Black formatting
2. **Add tests**: Test new functionality
3. **Update documentation**: Keep this doc current
4. **Use type hints**: For better code clarity
5. **Handle errors gracefully**: Provide helpful error messages

### Testing Changes

```bash
# Test the script on a clean environment
git clone https://github.com/TeamFixIT/portscan-delta-reporter.git test-repo
cd test-repo
python scripts/dev_manager.py setup
python scripts/dev_manager.py test
```

## License

This script is part of the Port Scanner Delta Reporter project and follows the same license terms.
