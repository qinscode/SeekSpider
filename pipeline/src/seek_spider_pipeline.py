"""
Seek Job Spider Pipeline

Scrapes job listings from Seek.com.au for IT positions.
"""

import subprocess
import sys
import os
from typing import Literal
from pydantic import BaseModel, Field
from datetime import datetime
from dateutil import tz

from apscheduler.triggers.cron import CronTrigger
from plombery import register_pipeline, task, Trigger, get_logger

# Get project directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SCRAPER_DIR = os.path.join(PROJECT_ROOT, "scraper")

# Common Australian locations for Seek
LOCATIONS = Literal[
    "All Perth WA",
    "All Sydney NSW",
    "All Melbourne VIC",
    "All Brisbane QLD",
    "All Adelaide SA",
    "All Canberra ACT",
    "All Hobart TAS",
    "All Darwin NT",
    "All Australia",
]

# Job classifications
CLASSIFICATIONS = Literal[
    "6281",  # Information & Communication Technology
    "1200",  # Accounting
    "6251",  # Banking & Financial Services
    "6304",  # Engineering
    "6317",  # Healthcare & Medical
]


class SeekSpiderParams(BaseModel):
    """Parameters for Seek Spider"""

    location: LOCATIONS = Field(
        default="All Perth WA",
        description="Location to search for jobs"
    )
    classification: CLASSIFICATIONS = Field(
        default="6281",
        description="Job classification (6281=IT, 1200=Accounting, 6304=Engineering)"
    )
    run_post_processing: bool = Field(
        default=True,
        description="Run AI-powered post-processing (requires AI API configuration)"
    )
    concurrent_requests: int = Field(
        default=16,
        ge=1,
        le=32,
        description="Number of concurrent requests"
    )
    download_delay: float = Field(
        default=2.0,
        ge=0.5,
        le=10.0,
        description="Delay between requests in seconds"
    )


@task
async def run_seek_spider(params: SeekSpiderParams) -> dict:
    """Run the Seek job spider using subprocess"""

    logger = get_logger()
    logger.info("Starting Seek Spider")
    logger.info(f"Parameters: location={params.location}, classification={params.classification}")
    logger.info(f"Post-processing enabled: {params.run_post_processing}")

    try:
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{PROJECT_ROOT}:{SCRAPER_DIR}:{env.get('PYTHONPATH', '')}"
        env['SCRAPY_SETTINGS_MODULE'] = 'SeekSpider.settings'

        # Build scrapy command with spider arguments
        cmd = [
            sys.executable, '-m', 'scrapy', 'crawl', 'seek',
            '-a', f'location={params.location}',
            '-a', f'classification={params.classification}',
            '-s', f'CONCURRENT_REQUESTS={params.concurrent_requests}',
            '-s', f'DOWNLOAD_DELAY={params.download_delay}',
            '-s', 'LOG_LEVEL=INFO',
        ]

        logger.info(f"Running command: {' '.join(cmd)}")
        logger.info(f"Working directory: {SCRAPER_DIR}")

        # Run the spider
        process = subprocess.Popen(
            cmd,
            cwd=SCRAPER_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Stream output to logger
        for line in process.stdout:
            line = line.strip()
            if line:
                logger.info(line)

        # Wait for process to complete
        return_code = process.wait()

        if return_code != 0:
            return {
                "status": "error",
                "error": f"Spider exited with code {return_code}",
                "timestamp": datetime.now().isoformat()
            }

        result = {
            "status": "success",
            "message": "Seek Spider completed successfully",
            "location": params.location,
            "classification": params.classification,
            "post_processing": params.run_post_processing,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("Seek Spider completed successfully")
        return result

    except Exception as e:
        logger.error(f"Seek Spider failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


register_pipeline(
    id="seek_spider",
    description="Scrape job listings from Seek.com.au",
    tasks=[run_seek_spider],
    params=SeekSpiderParams,
    triggers=[
        # Perth - Daily 6 AM
        Trigger(
            id="perth_daily_6am",
            name="Perth Daily 6 AM",
            description="Scrape Perth IT jobs at 6:00 AM",
            params=SeekSpiderParams(
                location="All Perth WA",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(
                hour=6,
                minute=0,
                timezone=tz.gettz("Australia/Perth")
            ),
        ),
        # Perth - Daily 6 PM
        Trigger(
            id="perth_daily_6pm",
            name="Perth Daily 6 PM",
            description="Scrape Perth IT jobs at 6:00 PM",
            params=SeekSpiderParams(
                location="All Perth WA",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(
                hour=18,
                minute=0,
                timezone=tz.gettz("Australia/Perth")
            ),
        ),
    ],
)
