#!/usr/bin/env python3
"""
Flask Application Entry Point
"""
from app import create_app
import os

app = create_app()


def main():
    debug = os.environ.get("FLASK_ENV") == "development"
    if debug:
        app.run(
            host="0.0.0.0",
            port=int(os.environ.get("PORT", 5000)),
            debug=debug,
            threaded=True,
        )
    else:
        print("Use gunicorn to run the server in production mode.")


if __name__ == "__main__":
    main()
