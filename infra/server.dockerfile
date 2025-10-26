# Dockerfile for Flask Server
FROM python:3.11-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server application code
COPY . .

# Create directories for sessions, uploads, scan results, and instance
RUN mkdir -p /app/sessions /app/uploads /app/scan_results /app/instance && \
    chmod -R 755 /app/sessions /app/uploads /app/scan_results /app/instance

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py

# Create entrypoint script for initialization
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Flask Server..."\n\
\n\
# Check if setup.sh exists and run it\n\
if [ -f ./setup.sh ]; then\n\
    echo "Running setup.sh..."\n\
    ./setup.sh\n\
fi\n\
\n\
# initialise database if not already initialised\n\
if [ ! -f /app/instance/app.db ]; then\n\
    echo "Initializing database..."\n\
    flask init-db\n\
fi\n\
\n\
# Start the Flask server\n\
exec flask run --host=0.0.0.0 --port=5000\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Expose Flask port
EXPOSE 5000

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]