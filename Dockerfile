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

# Expose port
EXPOSE 5000

# Health check - use wget instead of curl for smaller footprint, or keep curl since we installed it
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with gunicorn in production
# Single worker for SQLite compatibility, use Redis for session/caching
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "120", "backend.app:app"]