# Dockerfile for Flask Server
FROM python:3.11-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server application code
COPY . .

# Create instance directory for database
RUN mkdir -p instance

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=run.py

# Expose Flask port
EXPOSE 5000

# Default command
CMD ["python", "run.py"]
