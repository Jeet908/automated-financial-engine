# Multi-stage / Production Dockerfile for Financial Modeling Engine
FROM python:3.11-slim

# Prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

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

# Create inbox and outbox directories
RUN mkdir -p /app/client_inbox /app/client_outbox /app/outputs

# Expose API port
EXPOSE 8000

# Default command: launch FastAPI server via uvicorn binding dynamically to Railway's $PORT or 8000
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
