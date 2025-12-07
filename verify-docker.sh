#!/bin/bash

# Plombery Docker Verification Script
# This script verifies that the Docker container is working correctly

set -e

echo "=========================================="
echo "Plombery Docker Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print success
success() {
    echo -e "${GREEN}✓${NC} $1"
}

# Function to print error
error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to print warning
warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if Docker is running
echo "1. Checking Docker..."
if docker info > /dev/null 2>&1; then
    success "Docker is running"
else
    error "Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if container is running
echo ""
echo "2. Checking container status..."
if docker compose ps | grep -q "plombery.*running"; then
    success "Container is running"
else
    warning "Container is not running. Starting it now..."
    docker compose up -d
    sleep 5
fi

# Check container health
echo ""
echo "3. Checking container health..."
HEALTH=$(docker inspect plombery-krampus --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
if [ "$HEALTH" = "healthy" ]; then
    success "Container is healthy"
elif [ "$HEALTH" = "starting" ]; then
    warning "Container is starting... waiting 10 seconds"
    sleep 10
    HEALTH=$(docker inspect plombery-krampus --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    if [ "$HEALTH" = "healthy" ]; then
        success "Container is now healthy"
    else
        error "Container health check failed: $HEALTH"
    fi
else
    error "Container health check failed: $HEALTH"
fi

# Test API endpoints
echo ""
echo "4. Testing API endpoints..."

# Test /api/auth/whoami
if curl -s --max-time 5 http://localhost:8000/api/auth/whoami | grep -q "is_authentication_enabled"; then
    success "/api/auth/whoami is responding"
else
    error "/api/auth/whoami is not responding"
fi

# Test /api/auth/providers
if curl -s --max-time 5 http://localhost:8000/api/auth/providers | grep -q "\[\]"; then
    success "/api/auth/providers is responding"
else
    error "/api/auth/providers is not responding"
fi

# Check PYTHONPATH
echo ""
echo "5. Checking PYTHONPATH configuration..."
PYTHONPATH_VALUE=$(docker compose exec plombery printenv PYTHONPATH 2>/dev/null || echo "")
if echo "$PYTHONPATH_VALUE" | grep -q "/app:/app/src"; then
    success "PYTHONPATH is correctly configured: $PYTHONPATH_VALUE"
else
    error "PYTHONPATH is incorrect: $PYTHONPATH_VALUE"
fi

# Check static files
echo ""
echo "6. Checking frontend static files..."
if docker compose exec plombery test -f /app/src/plombery/static/index.html 2>/dev/null; then
    success "Frontend static files exist"
    if docker compose exec plombery test -d /app/src/plombery/static/assets 2>/dev/null; then
        FILE_COUNT=$(docker compose exec plombery ls -1 /app/src/plombery/static/assets/ 2>/dev/null | wc -l)
        success "Found $FILE_COUNT asset files"
    fi
else
    error "Frontend static files not found"
    echo "   This may cause the web UI to fail"
fi

# Test home page
echo ""
echo "7. Testing web UI..."
if curl -s --max-time 5 http://localhost:8000/ | grep -q "<title>Plombery</title>"; then
    success "Web UI is accessible"
else
    error "Web UI is not responding correctly"
fi

# Check scraper module
echo ""
echo "8. Checking scraper module import..."
if docker compose exec plombery python -c "import scraper.flow_meter_scraper.fetch_flow_meter_data" 2>/dev/null; then
    success "Scraper module can be imported"
else
    error "Scraper module import failed"
fi

# Check pipelines API
echo ""
echo "9. Checking pipelines registration..."
PIPELINE_COUNT=$(curl -s --max-time 5 http://localhost:8000/api/pipelines/ 2>/dev/null | grep -o '"id"' | wc -l || echo "0")
if [ "$PIPELINE_COUNT" -gt "0" ]; then
    success "Found $PIPELINE_COUNT registered pipeline(s)"
else
    error "No pipelines registered"
fi

# Final summary
echo ""
echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo "Access the application at: http://localhost:8000"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f              - View container logs"
echo "  docker compose ps                   - Check container status"
echo "  docker compose exec plombery /bin/bash  - Open shell in container"
echo ""
