# Multi-stage / Production Dockerfile for Financial Modeling Engine
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000

WORKDIR /app

# Install system dependencies (build tools, libraries needed by c-extensions, reportlab, and fonts)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application codebase
COPY . .

# Create required workspace directories
RUN mkdir -p /app/client_inbox /app/client_outbox /app/outputs /app/artifacts /app/inputs

# Expose API port
EXPOSE 8000

# Default command: launch production FastAPI portal via python app.py (binds to $PORT)
CMD ["python", "app.py"]
