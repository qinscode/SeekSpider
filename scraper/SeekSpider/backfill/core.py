"""
Core backfill functionality - JobDescriptionBackfiller class.
"""

import csv
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Tuple, Optional

from bs4 import BeautifulSoup

from .config import BackfillConfig
from .drivers import DriverManager
from .ai_processor import BackfillAIProcessor


class JobDescriptionBackfiller:
    """Backfill missing job descriptions using Chrome browser automation"""

    def __init__(self, config: BackfillConfig = None, logger: logging.Logger = None):
        self.config = config or BackfillConfig()
        self.config.validate()

        self.logger = logger or logging.getLogger('backfill')

        # Initialize managers
        self.driver_manager = DriverManager(self.config, self.logger)
        self.ai_processor = BackfillAIProcessor(self.config, self.logger)

        # Database connection
        self.db = None
        self._init_database()

        # Driver state (for serial mode)
        self.driver = None
        self.jobs_since_restart = 0
        self.consecutive_failures = 0

        # Thread safety locks
        self.db_lock = threading.Lock()
        self.csv_lock = threading.Lock()

        # CSV logging
        self.csv_file = None
        self.csv_writer = None
        self.csv_handle = None

        # Statistics
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'cloudflare_blocked': 0,
            'driver_restarts': 0,
        }

    def _init_database(self):
        """Initialize database connection"""
        from core.config import config as app_config
        from core.database import DatabaseManager
        self.db = DatabaseManager(app_config)
        self._app_config = app_config

    def get_jobs_without_description(self, limit: int = None) -> List[Tuple]:
        """Get jobs where JobDescription is empty, filtered by region if specified"""
        params = []

        # Build WHERE clause conditions
        conditions = ['("JobDescription" IS NULL OR "JobDescription" = \'\' OR "JobDescription" = \'None\')']

        if not self.config.include_inactive:
            conditions.append('"IsActive" = \'True\'')

        if self.config.region_filter:
            conditions.append('"Region" = %s')
            params.append(self.config.region_filter)

        where_clause = ' AND '.join(conditions)
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f'''
            SELECT "Id", "Url", "JobTitle"
            FROM "{self._app_config.POSTGRESQL_TABLE}"
            WHERE {where_clause}
            ORDER BY "CreatedAt" DESC
            {limit_clause}
        '''

        try:
            return self.db.execute_query(query, tuple(params) if params else None)
        except Exception as e:
            self.logger.error(f"Error fetching jobs: {e}")
            return []

    def run(self, limit: int = None):
        """Run the backfill process"""
        self.logger.info("=" * 60)
        self.logger.info("Starting job description backfill...")

        region_msg = f"for region: {self.config.region_filter}" if self.config.region_filter else "for all regions"
        limit_msg = f"up to {limit}" if limit else "all"
        self.logger.info(f"Fetching {limit_msg} jobs without descriptions {region_msg}...")

        if self.config.region_filter:
            self.logger.info(f"⚠️  REGION FILTER ACTIVE: Only processing jobs with Region='{self.config.region_filter}'")
            self.logger.info(f"    This prevents conflicts with other region backfill processes")
        else:
            self.logger.warning("⚠️  NO REGION FILTER: Processing ALL regions (may cause conflicts if multiple backfills run simultaneously)")

        if self.config.workers > 1:
            self.logger.info(f"🚀 CONCURRENT MODE: Using {self.config.workers} workers for parallel processing")
        else:
            self.logger.info("📝 SERIAL MODE: Processing jobs one by one")

        self.logger.info("=" * 60)

        jobs = self.get_jobs_without_description(limit)
        self.stats['total'] = len(jobs)

        if self.config.region_filter:
            self.logger.info(f"✓ Found {len(jobs)} jobs to process for region '{self.config.region_filter}'")
        else:
            self.logger.info(f"Found {len(jobs)} jobs to process (all regions)")

        if not jobs:
            self.logger.info("No jobs to process.")
            return

        try:
            self._init_csv()
            self.ai_processor.start()

            if self.config.workers > 1:
                self._run_concurrent(jobs)
            else:
                self._run_serial(jobs)

        finally:
            self.ai_processor.stop()
            self._close_csv()

        self._print_summary()

    def _run_serial(self, jobs: List[Tuple]):
        """Run backfill in serial mode"""
        self.driver = self.driver_manager.create_driver()

        try:
            for i, (job_id, url, title) in enumerate(jobs, 1):
                self.logger.info(f"[{i}/{len(jobs)}] Processing job {job_id}: {title[:50]}...")

                # Check for periodic restart
                self._periodic_restart_check()

                description, suburb, status = self._fetch_with_retry(url)

                if status == 'cloudflare':
                    self.logger.warning("  Cloudflare blocked - skipping")
                    self.stats['cloudflare_blocked'] += 1
                    self.consecutive_failures += 1
                    time.sleep(self.config.delay * 2)

                    if self.consecutive_failures >= self.config.max_consecutive_failures:
                        self.logger.warning(f"  {self.consecutive_failures} consecutive failures, restarting driver...")
                        self._restart_driver("consecutive failures")
                    continue

                if status == 'success' and description:
                    self.consecutive_failures = 0
                    text_only = BeautifulSoup(description, 'lxml').get_text()[:100].replace('\n', ' ').strip()
                    self.logger.info(f"  Description preview: {text_only}...")

                    if self._update_job(job_id, description, suburb):
                        self.logger.info(f"  Updated successfully (description: {len(description)} chars, suburb: {suburb})")
                        self.stats['success'] += 1
                        self._write_csv_row(job_id, title, url, suburb, description)

                        text_description = BeautifulSoup(description, 'lxml').get_text(separator=' ').strip()
                        self.ai_processor.queue_analysis(job_id, text_description)
                    else:
                        self.stats['failed'] += 1
                        self.consecutive_failures += 1
                else:
                    self.logger.warning(f"  Failed: {status}")
                    self.stats['failed'] += 1
                    self.consecutive_failures += 1

                    if self.consecutive_failures >= self.config.max_consecutive_failures:
                        self.logger.warning(f"  {self.consecutive_failures} consecutive failures, restarting driver...")
                        self._restart_driver("consecutive failures")

                self.jobs_since_restart += 1
                delay = self.config.delay + random.uniform(0, 2)
                time.sleep(delay)

        finally:
            DriverManager.close_driver(self.driver)
            self.driver_manager.stop_virtual_display()

    def _run_concurrent(self, jobs: List[Tuple]):
        """Run backfill in concurrent mode with multiple workers"""
        self.logger.info(f"Initializing {self.config.workers} Chrome driver instances...")

        drivers = []
        for i in range(self.config.workers):
            try:
                driver = self.driver_manager.create_driver()
                drivers.append(driver)
                self.logger.info(f"  Worker {i+1}/{self.config.workers} initialized")
            except Exception as e:
                self.logger.error(f"  Failed to initialize worker {i+1}: {e}")

        if not drivers:
            self.logger.error("Failed to initialize any drivers, falling back to serial mode")
            self._run_serial(jobs)
            return

        self.logger.info(f"✓ {len(drivers)} workers ready for concurrent processing")

        try:
            with ThreadPoolExecutor(max_workers=len(drivers), thread_name_prefix='Worker') as executor:
                futures = []
                for i, job_data in enumerate(jobs, 1):
                    driver_index = (i - 1) % len(drivers)
                    driver_instance = drivers[driver_index]

                    future = executor.submit(
                        self._process_single_job,
                        job_data,
                        i,
                        len(jobs),
                        driver_instance
                    )
                    futures.append(future)
                    time.sleep(0.5)

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.error(f"Worker error: {e}")

        finally:
            self.logger.info("Cleaning up driver instances...")
            for i, driver in enumerate(drivers):
                try:
                    DriverManager.close_driver(driver)
                    self.logger.info(f"  Worker {i+1} driver closed")
                except Exception as e:
                    self.logger.error(f"  Error closing worker {i+1}: {e}")

            self.driver_manager.stop_virtual_display()

    def _process_single_job(self, job_data: Tuple, job_index: int, total_jobs: int, driver_instance) -> bool:
        """Process a single job (used for concurrent execution)"""
        job_id, url, title = job_data
        self.logger.info(f"[{job_index}/{total_jobs}] [Worker-{threading.current_thread().name}] Processing job {job_id}: {title[:50]}...")

        description, suburb, status = self._fetch_with_retry_concurrent(url, driver_instance)

        if status == 'cloudflare':
            self.logger.warning(f"  [Worker-{threading.current_thread().name}] Cloudflare blocked - skipping")
            self.stats['cloudflare_blocked'] += 1
            return False

        if status == 'success' and description:
            text_only = BeautifulSoup(description, 'lxml').get_text()[:100].replace('\n', ' ').strip()
            self.logger.info(f"  [Worker-{threading.current_thread().name}] Description preview: {text_only}...")

            if self._update_job(job_id, description, suburb):
                self.logger.info(f"  [Worker-{threading.current_thread().name}] Updated successfully (description: {len(description)} chars, suburb: {suburb})")
                self.stats['success'] += 1
                self._write_csv_row(job_id, title, url, suburb, description)

                text_description = BeautifulSoup(description, 'lxml').get_text(separator=' ').strip()
                self.ai_processor.queue_analysis(job_id, text_description)
                return True
            else:
                self.stats['failed'] += 1
                return False
        else:
            self.logger.warning(f"  [Worker-{threading.current_thread().name}] Failed: {status}")
            self.stats['failed'] += 1
            return False

    def _fetch_job_description(self, url: str, driver=None) -> Tuple[Optional[str], Optional[str], str]:
        """Fetch job description from URL"""
        driver = driver or self.driver

        try:
            driver.get(url)
            time.sleep(3)

            page_source = driver.page_source
            if 'challenge' in page_source.lower() or 'cf-browser-verification' in page_source.lower():
                self.logger.warning("  Cloudflare challenge detected, waiting...")
                time.sleep(10)
                page_source = driver.page_source

            soup = BeautifulSoup(page_source, 'lxml')

            # Extract job description
            job_details = soup.find("div", attrs={"data-automation": "jobAdDetails"})
            if not job_details:
                job_details = soup.find("div", attrs={"data-automation": "jobDescription"})
            if not job_details:
                job_details = soup.find("div", class_=lambda x: x and 'jobDescription' in str(x).lower())

            description = str(job_details) if job_details else None

            # Extract suburb
            location = soup.find("span", attrs={"data-automation": "job-detail-location"})
            suburb = location.text if location else None

            return description, suburb, 'success' if description else 'no_description'

        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower():
                return None, None, 'timeout'
            if 'no such window' in error_msg.lower() or 'target window already closed' in error_msg.lower():
                return None, None, 'driver_crashed'
            return None, None, error_msg

    def _fetch_with_retry(self, url: str) -> Tuple[Optional[str], Optional[str], str]:
        """Fetch job description with retry logic (serial mode)"""
        for attempt in range(self.config.max_job_retries + 1):
            try:
                if not DriverManager.is_driver_alive(self.driver):
                    self._restart_driver("driver not responding")
                    time.sleep(2)

                description, suburb, status = self._fetch_job_description(url)

                if status == 'driver_crashed':
                    self.logger.warning(f"  Driver crashed (attempt {attempt + 1}/{self.config.max_job_retries + 1})")
                    self._restart_driver("driver crashed")
                    time.sleep(2)

                    if attempt < self.config.max_job_retries:
                        continue
                    else:
                        return None, None, 'max_retries_exceeded'

                return description, suburb, status

            except Exception as e:
                self.logger.error(f"  Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_job_retries:
                    self._restart_driver(f"exception: {e}")
                    time.sleep(2)
                else:
                    return None, None, f'exception: {e}'

        return None, None, 'max_retries_exceeded'

    def _fetch_with_retry_concurrent(self, url: str, driver_instance) -> Tuple[Optional[str], Optional[str], str]:
        """Fetch job description with retry logic (concurrent mode)"""
        for attempt in range(self.config.max_job_retries + 1):
            try:
                description, suburb, status = self._fetch_job_description(url, driver_instance)

                if status == 'driver_crashed':
                    self.logger.warning(f"  Driver crashed (attempt {attempt + 1}/{self.config.max_job_retries + 1})")
                    if attempt < self.config.max_job_retries:
                        time.sleep(2)
                        continue
                    else:
                        return None, None, 'max_retries_exceeded'

                return description, suburb, status

            except Exception as e:
                self.logger.error(f"  Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_job_retries:
                    time.sleep(2)
                else:
                    return None, None, f'exception: {e}'

        return None, None, 'max_retries_exceeded'

    def _restart_driver(self, reason: str = "unknown"):
        """Restart the Chrome driver (serial mode)"""
        self.logger.warning(f"  Restarting driver (reason: {reason})...")
        self.stats['driver_restarts'] += 1

        DriverManager.close_driver(self.driver)
        time.sleep(2)

        self.driver = self.driver_manager.create_driver()
        self.jobs_since_restart = 0
        self.consecutive_failures = 0
        self.logger.info("  Driver restarted successfully")

    def _periodic_restart_check(self):
        """Check if driver should be restarted based on job count"""
        if self.jobs_since_restart >= self.config.restart_interval:
            self.logger.info(f"Periodic restart: processed {self.jobs_since_restart} jobs since last restart")
            self._restart_driver(f"periodic restart after {self.config.restart_interval} jobs")
            return True
        return False

    def _update_job(self, job_id: int, description: str, suburb: str = None) -> bool:
        """Update job description in database (thread-safe)"""
        try:
            job_data = {'JobDescription': description}
            if suburb:
                job_data['Suburb'] = suburb

            with self.db_lock:
                affected_rows = self.db.update_job(job_id, job_data)

            if affected_rows == 0:
                self.logger.warning(f"  Job {job_id} was already updated by another process (skipped)")
                return False

            return True
        except Exception as e:
            self.logger.error(f"  Database update failed: {e}")
            return False

    def _init_csv(self):
        """Initialize CSV file for logging"""
        if self.csv_file:
            self.csv_handle = open(self.csv_file, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_handle)
            self.csv_writer.writerow(['job_id', 'job_title', 'url', 'suburb', 'description_length', 'job_description', 'scraped_at'])
            self.logger.info(f"CSV logging enabled: {self.csv_file}")

    def _close_csv(self):
        """Close CSV file handle"""
        if self.csv_handle:
            self.csv_handle.close()
            self.csv_handle = None
            self.csv_writer = None

    def _write_csv_row(self, job_id, title, url, suburb, description):
        """Write a row to the CSV log file (thread-safe)"""
        if self.csv_writer:
            text_description = BeautifulSoup(description, 'lxml').get_text(separator=' ').strip()
            with self.csv_lock:
                self.csv_writer.writerow([
                    job_id,
                    title,
                    url,
                    suburb or '',
                    len(description),
                    text_description,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ])
                self.csv_handle.flush()

    def set_csv_file(self, csv_file: str):
        """Set CSV file path for logging"""
        self.csv_file = csv_file

    def _print_summary(self):
        """Print summary"""
        ai_stats = self.ai_processor.get_stats()

        self.logger.info("=" * 50)
        self.logger.info("BACKFILL SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total jobs processed: {self.stats['total']}")
        self.logger.info(f"Successfully updated: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Cloudflare blocked: {self.stats['cloudflare_blocked']}")
        self.logger.info(f"Driver restarts: {self.stats['driver_restarts']}")
        self.logger.info(f"Success rate: {self.stats['success']/max(self.stats['total'],1)*100:.1f}%")

        if self.config.enable_async_ai:
            self.logger.info("-" * 50)
            self.logger.info("AI ANALYSIS (async)")
            self.logger.info(f"Tech stack analyzed: {ai_stats['ai_analyzed']}")
            self.logger.info(f"Tech stack failures: {ai_stats['ai_failed']}")
            self.logger.info(f"Salary normalized: {ai_stats['salary_normalized']}")
            self.logger.info(f"Salary skipped (no pay range): {ai_stats['salary_skipped']}")
            self.logger.info(f"Salary failures: {ai_stats['salary_failed']}")

        self.logger.info("=" * 50)

    def get_stats(self) -> dict:
        """Get combined statistics"""
        stats = self.stats.copy()
        stats.update(self.ai_processor.get_stats())
        return stats
