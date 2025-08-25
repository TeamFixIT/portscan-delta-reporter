# Use official lightweight Python image
FROM python:3.11-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies (for nmap)
RUN apt-get update && apt-get install -y nmap && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .

# Create output directory inside container
RUN mkdir -p scan_results

# Set environment variable (optional for configs)
ENV SCAN_CONFIG=/app/config/example_config.json

# Default command (run scanner)
CMD ["python", "src/scanner.py"]
