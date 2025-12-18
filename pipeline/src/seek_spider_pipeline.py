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

import psycopg2
from apscheduler.triggers.cron import CronTrigger
from plombery import register_pipeline, task, Trigger, get_logger

# Get project directories
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SCRAPER_DIR = os.path.join(PROJECT_ROOT, "scraper")

# Australian regions
REGIONS = Literal[
    "Perth",
    "Sydney",
    "Melbourne",
    "Brisbane",
    "Gold Coast",
    "Adelaide",
    "Canberra",
    "Hobart",
    "Darwin",
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

    region: REGIONS = Field(
        default="Perth",
        description="Australian region to search for jobs"
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
    logger.info(f"Parameters: region={params.region}, classification={params.classification}")
    logger.info(f"Post-processing enabled: {params.run_post_processing}")

    try:
        # Set up environment
        env = os.environ.copy()
        env['PYTHONPATH'] = f"{PROJECT_ROOT}:{SCRAPER_DIR}:{env.get('PYTHONPATH', '')}"
        env['SCRAPY_SETTINGS_MODULE'] = 'SeekSpider.settings'

        # Build scrapy command with spider arguments (using region instead of location)
        cmd = [
            sys.executable, '-m', 'scrapy', 'crawl', 'seek',
            '-a', f'region={params.region}',
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
            "region": params.region,
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


# Perth timezone for all Australian regions
PERTH_TZ = tz.gettz("Australia/Perth")

register_pipeline(
    id="seek_spider",
    description="Scrape job listings from Seek.com.au",
    tasks=[run_seek_spider],
    params=SeekSpiderParams,
    triggers=[
        # Perth - Daily 6 AM & 6 PM
        Trigger(
            id="perth_daily_6am",
            name="Perth Daily 6 AM",
            description="Scrape Perth IT jobs at 6:00 AM",
            params=SeekSpiderParams(
                region="Perth",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=6, minute=0, timezone=PERTH_TZ),
        ),
        Trigger(
            id="perth_daily_6pm",
            name="Perth Daily 6 PM",
            description="Scrape Perth IT jobs at 6:00 PM",
            params=SeekSpiderParams(
                region="Perth",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=18, minute=0, timezone=PERTH_TZ),
        ),

        # Sydney - Daily 6 AM & 6 PM
        Trigger(
            id="sydney_daily_6am",
            name="Sydney Daily 6 AM",
            description="Scrape Sydney IT jobs at 6:00 AM",
            params=SeekSpiderParams(
                region="Sydney",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=6, minute=15, timezone=PERTH_TZ),
        ),
        Trigger(
            id="sydney_daily_6pm",
            name="Sydney Daily 6 PM",
            description="Scrape Sydney IT jobs at 6:00 PM",
            params=SeekSpiderParams(
                region="Sydney",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=18, minute=15, timezone=PERTH_TZ),
        ),

        # Melbourne - Daily 6 AM & 6 PM
        Trigger(
            id="melbourne_daily_6am",
            name="Melbourne Daily 6 AM",
            description="Scrape Melbourne IT jobs at 6:00 AM",
            params=SeekSpiderParams(
                region="Melbourne",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=6, minute=30, timezone=PERTH_TZ),
        ),
        Trigger(
            id="melbourne_daily_6pm",
            name="Melbourne Daily 6 PM",
            description="Scrape Melbourne IT jobs at 6:00 PM",
            params=SeekSpiderParams(
                region="Melbourne",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=18, minute=30, timezone=PERTH_TZ),
        ),

        # Brisbane - Daily 6 AM & 6 PM
        Trigger(
            id="brisbane_daily_6am",
            name="Brisbane Daily 6 AM",
            description="Scrape Brisbane IT jobs at 6:00 AM",
            params=SeekSpiderParams(
                region="Brisbane",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=6, minute=45, timezone=PERTH_TZ),
        ),
        Trigger(
            id="brisbane_daily_6pm",
            name="Brisbane Daily 6 PM",
            description="Scrape Brisbane IT jobs at 6:00 PM",
            params=SeekSpiderParams(
                region="Brisbane",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=18, minute=45, timezone=PERTH_TZ),
        ),

        # Adelaide - Daily 7 AM & 7 PM
        Trigger(
            id="adelaide_daily_7am",
            name="Adelaide Daily 7 AM",
            description="Scrape Adelaide IT jobs at 7:00 AM",
            params=SeekSpiderParams(
                region="Adelaide",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=7, minute=0, timezone=PERTH_TZ),
        ),
        Trigger(
            id="adelaide_daily_7pm",
            name="Adelaide Daily 7 PM",
            description="Scrape Adelaide IT jobs at 7:00 PM",
            params=SeekSpiderParams(
                region="Adelaide",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=19, minute=0, timezone=PERTH_TZ),
        ),

        # Canberra - Daily 7 AM & 7 PM
        Trigger(
            id="canberra_daily_7am",
            name="Canberra Daily 7 AM",
            description="Scrape Canberra IT jobs at 7:00 AM",
            params=SeekSpiderParams(
                region="Canberra",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=7, minute=15, timezone=PERTH_TZ),
        ),
        Trigger(
            id="canberra_daily_7pm",
            name="Canberra Daily 7 PM",
            description="Scrape Canberra IT jobs at 7:00 PM",
            params=SeekSpiderParams(
                region="Canberra",
                classification="6281",
                run_post_processing=True,
            ),
            schedule=CronTrigger(hour=19, minute=15, timezone=PERTH_TZ),
        ),
    ],
)


# ============================================================================
# Daily Reset IsNew Pipeline
# ============================================================================

class ResetIsNewParams(BaseModel):
    """Parameters for Reset IsNew task"""
    dry_run: bool = Field(
        default=False,
        description="If True, only show what would be changed without making changes"
    )


@task
async def reset_is_new(params: ResetIsNewParams) -> dict:
    """Reset IsNew field to False for all jobs at midnight"""

    logger = get_logger()
    logger.info("Starting daily IsNew reset task")

    try:
        # Get database configuration from environment
        db_config = {
            'host': os.getenv('POSTGRESQL_HOST'),
            'port': int(os.getenv('POSTGRESQL_PORT', 5432)),
            'user': os.getenv('POSTGRESQL_USER'),
            'password': os.getenv('POSTGRESQL_PASSWORD'),
            'database': os.getenv('POSTGRESQL_DATABASE'),
        }
        table_name = os.getenv('POSTGRESQL_TABLE', 'seek_jobs')

        # Validate config
        missing = [k for k, v in db_config.items() if not v and k != 'port']
        if missing:
            raise ValueError(f"Missing database config: {missing}")

        # Connect to database
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        # Set timezone to Perth for all timestamp operations
        cursor.execute("SET timezone = 'Australia/Perth'")

        # First, count how many records have IsNew = True
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "IsNew" = TRUE')
        count_before = cursor.fetchone()[0]
        logger.info(f"Found {count_before} jobs with IsNew=True")

        if params.dry_run:
            logger.info("DRY RUN: Would reset IsNew to False for all jobs")
            cursor.close()
            conn.close()
            return {
                "status": "dry_run",
                "jobs_would_be_reset": count_before,
                "timestamp": datetime.now().isoformat()
            }

        # Reset IsNew to False for all jobs
        cursor.execute(f'''
            UPDATE "{table_name}"
            SET "IsNew" = FALSE, "UpdatedAt" = now()
            WHERE "IsNew" = TRUE
        ''')
        affected_rows = cursor.rowcount
        conn.commit()

        logger.info(f"Reset {affected_rows} jobs to IsNew=False")

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "jobs_reset": affected_rows,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Reset IsNew failed: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


register_pipeline(
    id="reset_is_new",
    description="Reset IsNew field to False for all jobs (run at midnight)",
    tasks=[reset_is_new],
    params=ResetIsNewParams,
    triggers=[
        # Daily at midnight Perth time
        Trigger(
            id="daily_midnight",
            name="Daily Midnight Reset",
            description="Reset IsNew to False at midnight Perth time",
            params=ResetIsNewParams(dry_run=False),
            schedule=CronTrigger(
                hour=0,
                minute=0,
                timezone=tz.gettz("Australia/Perth")
            ),
        ),
    ],
)
