#!/usr/bin/env python3
"""
Flask Application Entry Point

Run this file to start the Port Scanner Delta Reporter server.
"""

import os
from app import create_app, db, socketio

# Create Flask app
app = create_app()

@app.cli.command('init-db')
def init_db():
    """Initialize the database with tables."""
    with app.app_context():
        db.create_all()
        print("Database initialized!")

@app.cli.command('reset-db') 
def reset_db():
    """Reset the database (drop and recreate all tables)."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset!")

if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Run the app with SocketIO support
    socketio.run(
        app,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=True
    )