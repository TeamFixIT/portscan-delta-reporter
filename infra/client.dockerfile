# Dockerfile for Client Simulator
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
    sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject.toml and install Python dependencies
COPY pyproject.toml .
RUN pip install .

# Copy client application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting Client..."\n\
\n\
# Check if setup.sh exists and run it\n\
if [ -f ./setup.sh ]; then\n\
    echo "Running setup.sh..."\n\
    ./setup.sh\n\
fi\n\
\n\
# Start the client agent\n\
exec python client_agent.py\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Use the entrypoint script
ENTRYPOINT ["/entrypoint.sh"]