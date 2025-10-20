FROM python:3.11-alpine

# Install iptables and dependencies
RUN apk add --no-cache \
    iptables \
    ip6tables \
    curl

# Install Flask
RUN pip install --no-cache-dir flask

# Create app directory
WORKDIR /app

# Copy application files
COPY app.py /app/app.py
COPY templates/index.html /app/templates/index.html

# Expose port
EXPOSE 5000

# Run the application
CMD ["python3", "app.py"]
