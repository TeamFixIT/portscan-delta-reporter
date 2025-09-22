# Dockerfile for Raspberry Pi 4 Client Simulator
FROM python:3.11-slim

# Install system packages required for scanning
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    libffi-dev \
    nmap \
    net-tools \
    iputils-ping \
    dnsutils \
    tcpdump \
    procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy client application code
COPY . .

# Create logs directory
RUN mkdir -p /var/log && chmod 755 /var/log

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command (can be overridden)
CMD ["python", "client_agent.py"]
