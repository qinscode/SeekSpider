#!/usr/bin/python3

"""
SeekSpider - Seek.com.au Job Scraper
Run via the run.sh or run.ps1 script
"""

from plombery import get_app  # noqa: F401

# Import pipelines
from src import seek_spider_pipeline  # noqa: F401


if __name__ == "__main__":
    import uvicorn
    import os

    # Detect if running in Docker
    in_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER') == 'true'

    # Bind to 0.0.0.0 in Docker, 127.0.0.1 for local development
    host = "0.0.0.0" if in_docker else "127.0.0.1"

    # `reload_dirs` is used to reload when the plombery package itself changes
    # this is useful during development of the plombery package, normally shouldn't
    # be used
    uvicorn.run(
        "plombery:get_app",
        host=host,
        port=8000,
        reload=True,
        factory=True,
        reload_dirs=".."
    )
