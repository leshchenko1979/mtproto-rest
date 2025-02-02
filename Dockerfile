# Build stage
FROM python:3.12-alpine as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONOPTIMIZE=2

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    python3-dev

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONOPTIMIZE=2 \
    WORKERS=2 \
    WORKER_CLASS=uvicorn.workers.UvicornWorker \
    MAX_REQUESTS=1000 \
    MAX_REQUESTS_JITTER=50 \
    KEEP_ALIVE=75 \
    GRACEFUL_TIMEOUT=10 \
    PATH="/usr/local/bin:$PATH"

# Create non-root user
RUN adduser -D appuser

# Create necessary directories and clean up
RUN mkdir -p /app/sessions /app/logs && \
    chown -R appuser:appuser /app && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

WORKDIR /app

# Copy Python packages and executables from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# Copy application code
COPY --chown=appuser:appuser . .

# Create empty .env file if not mounted
RUN touch .env && chown appuser:appuser .env

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application with optimizations
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--no-access-log", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*", \
     "--no-server-header", \
     "--limit-concurrency", "100", \
     "--backlog", "100", \
     "--timeout-keep-alive", "75"]
