# Build stage
FROM python:3.13-alpine as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONOPTIMIZE=2 \
    RUSTFLAGS="-C target-feature=-crt-static" \
    CARGO_NET_GIT_FETCH_WITH_CLI=true \
    CARGO_BUILD_JOBS=4

# Install minimal build dependencies
RUN apk add --no-cache \
    build-base \
    rust \
    cargo

WORKDIR /app

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies with optimized Rust build
RUN --mount=type=cache,target=/root/.cargo/registry \
    --mount=type=cache,target=/root/.cargo/git \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.13-alpine

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

# Install minimal runtime dependencies and curl for health checks
RUN apk add --no-cache libstdc++ curl

# Create non-root user
RUN adduser -D appuser

# Create necessary directories and clean up
RUN mkdir -p /app/sessions /app/logs && \
    chown -R appuser:appuser /app && \
    rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

WORKDIR /app

# Copy only necessary Python packages and executables from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/

# Copy application code
COPY --chown=appuser:appuser . .

# Create empty .env file if not mounted
RUN touch .env && chown appuser:appuser .env

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run the application with optimizations
CMD ["uvicorn", "app.main:app", \
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
