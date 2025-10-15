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
    curl \
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

# Make setup.sh executable if it exists
RUN if [ -f setup.sh ]; then chmod +x setup.sh; fi

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Raspberry Pi Client..."\n\
\n\
# Run setup if it exists\n\
if [ -f ./setup.sh ]; then\n\
    echo "Running setup.sh..."\n\
    ./setup.sh\n\
fi\n\
\n\
# Wait a bit for server to be fully ready\n\
echo "Waiting for server to be ready..."\n\
sleep 5\n\
\n\
# Start the client agent\n\
echo "Starting client_agent.py..."\n\
exec python client_agent.py\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]