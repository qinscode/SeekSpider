#!/bin/bash
set -e

# Docker entrypoint script for SeekSpider

echo "=========================================="
echo "Starting SeekSpider"
echo "=========================================="
echo ""

# Display environment information
echo "Environment Configuration:"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  Working Directory: $(pwd)"
echo "  Python Version: $(python --version)"
echo ""

# Check if database connection is configured
if [ -n "$POSTGRESQL_HOST" ]; then
    echo "✓ Database configuration detected"
else
    echo "✗ Database configuration not found"
fi

# Check if AI API is configured
if [ -n "$AI_API_KEY" ]; then
    echo "✓ AI API configured"
else
    echo "ℹ AI API not configured (post-processing disabled)"
fi

echo ""
echo "Starting application server..."
echo "=========================================="
echo ""

# Start the application
cd /app/pipeline
exec python src/app.py

