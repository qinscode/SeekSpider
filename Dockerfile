# Multi-stage Dockerfile for SeekSpider
# Seek job scraper with Plombery task scheduler

# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder

# Install pnpm
RUN corepack enable && corepack prepare pnpm@10.19.0 --activate

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package.json frontend/pnpm-lock.yaml* ./

# Install dependencies
RUN pnpm install --frozen-lockfile

# Copy frontend source code
COPY frontend/ ./

# Build frontend
RUN pnpm build

# Stage 2: Build Python Application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files
COPY pyproject.toml setup.cfg MANIFEST.in ./

# Copy frontend build artifacts from previous stage
COPY --from=frontend-builder /app/src/plombery/static ./src/plombery/static

# Copy Python source code
COPY src/ ./src/

# Install Python dependencies (Plombery)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Copy pipeline and scraper code
COPY pipeline/ ./pipeline/
COPY scraper/ ./scraper/
COPY requirements.txt ./

# Install scraper requirements (Scrapy, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Install additional pipeline requirements
RUN pip install --no-cache-dir \
    python-dateutil \
    pandas

# Create directories for data and logs
RUN mkdir -p /app/data /app/logs

# Copy entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Set environment variables
ENV PYTHONPATH=/app/pipeline:/app:/app/src:/app/scraper:${PYTHONPATH}
ENV PYTHONUNBUFFERED=1
ENV SCRAPY_SETTINGS_MODULE=SeekSpider.settings

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set working directory for application
WORKDIR /app/pipeline

# Use entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
