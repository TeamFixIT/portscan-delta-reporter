#!/usr/bin/env python3
"""
Flask Application Entry Point
This allows running the app with: python -m app
"""
from gevent import monkey

monkey.patch_all()

import os
from app import create_app, socketio

app = create_app()


def main():
    """Main entry point for the application"""
    from pathlib import Path

    # Check if database exists
    BASE_DIR = Path(__file__).resolve().parent
    db_path = BASE_DIR / "data" / "app.db"
    migrations_dir = BASE_DIR / "migrations"

    first_run = not db_path.exists() or not migrations_dir.exists()
    print(first_run)
    if first_run:
        print("\n" + "=" * 60)
        print("FIRST TIME SETUP REQUIRED")
        print("=" * 60)
        print("\nIt looks like this is your first time running the application.")
        print("Please run the following commands to set up the database:\n")
        print("  1. flask setup          # Initialize database and migrations")
        print("  2. flask create-admin   # Create an admin user")
        print("  3. portscanner-server   # Start the server")
        print("\nOr run: flask setup && flask create-admin && portscanner-server")
        print("=" * 60 + "\n")
        return

    # Get configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"

    print(f"\nStarting Port Scanner Delta Reporter on {host}:{port}")
    print(f"Debug mode: {debug}\n")

    if debug:
        # Development server with debug mode
        socketio.run(app, host=host, port=port, debug=True)
    else:
        # Production - should use gunicorn or similar WSGI server
        socketio.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
