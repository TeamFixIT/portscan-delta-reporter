FROM python:3.11-slim

WORKDIR /app

# Install system packages required to build netifaces
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    gcc \
    libffi-dev \
    nmap \
    && rm -rf /var/lib/apt/lists/*

COPY ../src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../src ./src