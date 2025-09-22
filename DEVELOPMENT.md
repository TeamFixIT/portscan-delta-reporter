# Dev Manager Quick Reference

## Commands

| Command             | Description                           | Usage                                             |
| ------------------- | ------------------------------------- | ------------------------------------------------- |
| `setup`             | Initial development environment setup | `python scripts/dev_manager.py setup`             |
| `dev`               | Start development server              | `python scripts/dev_manager.py dev`               |
| `dev --with-client` | Start dev server + test client        | `python scripts/dev_manager.py dev --with-client` |
| `test`              | Run all tests                         | `python scripts/dev_manager.py test`              |
| `lint`              | Check code quality                    | `python scripts/dev_manager.py lint`              |
| `format`            | Format Python code                    | `python scripts/dev_manager.py format`            |
| `clean`             | Clean cache files                     | `python scripts/dev_manager.py clean`             |
| `git-setup`         | Configure Git + signing               | `python scripts/dev_manager.py git-setup`         |
| `git-verify`        | Verify Git configuration              | `python scripts/dev_manager.py git-verify`        |

## Quick Start

```bash
# 1. Setup (run once)
python scripts/dev_manager.py setup

# 2. Start development
python scripts/dev_manager.py dev

# 3. Before committing
python scripts/dev_manager.py format
python scripts/dev_manager.py test
```

## Development Workflow

```bash
# Daily workflow
python scripts/dev_manager.py dev       # Start dev server
# ... make changes ...
python scripts/dev_manager.py format   # Format code
python scripts/dev_manager.py lint     # Check quality
python scripts/dev_manager.py test     # Run tests
git add . && git commit -S -m "feat: add feature"
```

## Services

| Service   | URL                             | Description      |
| --------- | ------------------------------- | ---------------- |
| Web App   | http://localhost:5000           | Main application |
| API       | http://localhost:5000/api       | REST API         |
| Dashboard | http://localhost:5000/dashboard | Admin interface  |

## File Structure

```
project/
├── scripts/dev_manager.py    # This tool
├── backend/                  # Flask server
│   ├── venv/                # Virtual environment
│   ├── requirements.txt     # Dependencies
│   └── app/                 # Application code
├── client/                  # Scanning client
│   ├── venv/               # Virtual environment
│   ├── requirements.txt    # Dependencies
│   └── src/                # Client code
└── docs/                   # Documentation
    └── dev-manager.md      # Full documentation
```

## Troubleshooting

| Problem           | Solution                             |
| ----------------- | ------------------------------------ |
| Port 5000 in use  | `lsof -i :5000` then `kill -9 <PID>` |
| Virtual env fails | Install `python3-venv` package       |
| Permission denied | Check directory permissions          |
| Git not found     | Install Git for your OS              |
| Dependencies fail | Check internet connection            |

## Environment Variables

### Backend

- `FLASK_ENV=development`
- `FLASK_DEBUG=1`

### Client

- `LOG_LEVEL=DEBUG`
- `SERVER_URL=http://localhost:5000`

## Code Quality

```bash
# Check everything
python scripts/dev_manager.py lint     # Quality check
python scripts/dev_manager.py format   # Auto-format
python scripts/dev_manager.py test     # Run tests
python scripts/dev_manager.py clean    # Clean cache
```

## Git Signing

```bash
# Setup Git with signing
python scripts/dev_manager.py git-setup

# Verify configuration
python scripts/dev_manager.py git-verify

# Choose SSH signing (recommended) or GPG
```

For complete documentation, see `docs/dev-manager.md`
