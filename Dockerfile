# Multi-stage build for production
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies (including Playwright deps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers and system dependencies
# Use PLAYWRIGHT_BROWSERS_PATH to control installation location
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN python -m playwright install chromium
RUN python -m playwright install-deps chromium

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies including Playwright system dependencies and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy Playwright browsers from builder to a user-accessible location
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
COPY --from=builder /ms-playwright /ms-playwright

# Copy application code
COPY . .

# Ensure sibling imports in backend/ resolve (ai_generator, speech, database...)
ENV PYTHONPATH=/app/backend

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app /ms-playwright
USER app

# Render assigns PORT at runtime; default to 5000 for local docker runs
ENV PORT=5000
EXPOSE 5000

# Health check hits the runtime port
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f "http://localhost:${PORT}/health" || exit 1

# Run with gunicorn in production.
# Single worker (SQLite), multiple threads. max-requests recycles the worker
# periodically because headless Chromium leaks memory across Playwright runs.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --threads 4 --timeout 180 --graceful-timeout 30 --max-requests 40 --max-requests-jitter 10 --access-logfile - --error-logfile - backend.app:app"]