# Port Scanner Delta Reporter – Alpha Release (`v1.0.0-alpha`)

**Port Scanner Delta Reporter** is a Flask-based web application for managing and visualizing network port scans.  
This is the **alpha release**, intended for early testing and feedback.

---

## Quick Start

### 1. Download & Extract

Download `portscanner-server-1.0.0-alpha.zip` from the Releases page and extract it:

```bash
unzip portscanner-server-1.0.0-alpha.zip
cd portscanner-server
```

### 2. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install the Application

Install dependencies in editable (development) mode:

```bash
pip install -e .
```

Or, for a production install:

```bash
pip install .
```

### 4. Configure Environment

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Set at least the following:  
- `SECRET_KEY=<your-random-secret-key>`  

You can generate a secure secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Initialize the Database

```bash
flask setup
```

This command:  
- Initializes Flask-Migrate  
- Creates and applies initial migrations  
- Seeds default settings  

### 6. Create an Admin User

```bash
flask create-admin
```

### 7. Start the Server

```bash
portscanner-server
```

Or for development with auto-reload:

```bash
FLASK_ENV=development portscanner-server
```

Then visit:  
http://127.0.0.1:5000

## Available Flask Commands

| Command                  | Description                              |
|--------------------------|------------------------------------------|
| `flask setup`            | Full database initialization             |
| `flask create-admin`     | Create a new admin user                  |
| `flask new-migration -m "message"` | Generate new migration after model changes |
| `flask db upgrade`       | Apply migrations                         |
| `flask db downgrade`     | Roll back last migration                 |
| `flask reset-db`         | Recreate the database from scratch |
| `flask init-scheduler`   | Start or reload scheduled scan jobs      |

## System Requirements

- Python 3.9 or newer  
- pip (latest version recommended)  
- Works on Linux, macOS, and Windows  

## Environment Variables

| Variable                  | Description                  | Default                  |
|---------------------------|------------------------------|--------------------------|
| `SECRET_KEY`              | Flask secret key             | *required*               |
| `SQLALCHEMY_DATABASE_URI` | Database connection string   | `sqlite:///data/app.db`  |
| `HOST`                    | Bind address                 | `127.0.0.1`              |
| `PORT`                    | Port number                  | `5000`                   |
| `FLASK_ENV`               | Environment mode             | `development` or `production` |

## Directory Structure

```
portscanner-server/
├── app/                  # Main application package
│   ├── __init__.py
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   └── templates/
├── run.py                # Application entry point
├── pyproject.toml        # Build & dependency configuration
├── setup_server.sh          # Automated setup script
├── .env.example          # Example environment file
└── README.md
```

## Troubleshooting

- **“No module named 'run'”**  
  Reinstall in editable mode:  
  ```bash
  pip uninstall portscanner-server -y
  pip install -e .
  ```

- **“no such table” errors**  
  Initialize the database again:  
  ```bash
  flask setup
  ```

- **Reset and start fresh**  
  ```bash
  rm -rf migrations/ data/
  flask setup
  flask create-admin
  ```

## Deployment Example (Gunicorn)

For production environments (Linux):  

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:run"
```

Or using systemd:  

```
[Unit]
Description=Port Scanner Delta Reporter
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/portscanner-server
Environment="PATH=/path/to/portscanner-server/venv/bin"
ExecStart=/path/to/portscanner-server/venv/bin/portscanner-server

[Install]
WantedBy=multi-user.target
```

## Alpha Release Notes

This is an early build for testing core functionality.  
Expect incomplete features and possible bugs.  
Feedback and issue reports are appreciated!

**Author:** TeamFixIT 
**License:** MIT  
**Version:** 1.0.0-alpha