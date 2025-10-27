FROM python:3.11-slim

# Install system packages
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Just copy pyproject.toml and install dependencies
COPY pyproject.toml .
RUN pip install .

# Set Flask app location
ENV FLASK_APP=run.py

EXPOSE 5000

CMD ["python", "./run.py"]