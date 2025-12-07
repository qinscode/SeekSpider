#!/bin/bash

# Get the project root directory (parent of pipeline/)
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Activate virtual environment if it exists
if [ -f "${PROJECT_ROOT}/.venv/bin/activate" ]; then
    source "${PROJECT_ROOT}/.venv/bin/activate"
    echo "Virtual environment activated"
else
    echo "Warning: Virtual environment not found at ${PROJECT_ROOT}/.venv"
fi

# Set PYTHONPATH to include:
# 1. Project root (for scraper module)
# 2. src directory (for plombery package)
export PYTHONPATH="${PROJECT_ROOT}:${PROJECT_ROOT}/src:${PYTHONPATH}"

echo "PYTHONPATH: ${PYTHONPATH}"
echo "Python: $(which python)"

# Run the application
python src/app.py