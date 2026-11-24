"""
Core backfill functionality - JobDescriptionBackfiller class.

Job descriptions are fetched from Seek's GraphQL API (see fetcher.py), which
bypasses the Cloudflare-protected HTML job page. No browser is involved.
"""

import csv
import logging
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import List, Tuple, Optional

import requests
from bs4 import BeautifulSoup

from .config import BackfillConfig
from .fetcher import fetch_job_detail, TRANSIENT_STATUSES
from .ai_processor import BackfillAIProcessor


class JobDescriptionBackfiller:
    """Backfill missing job descriptions via Seek's GraphQL API"""

    def __init__(self, config: BackfillConfig = None, logger: logging.Logger = None):
        self.config = config or BackfillConfig()
        self.config.validate()

        self.logger = logger or logging.getLogger('backfill')

        # Managers
        self.ai_processor = BackfillAIProcessor(
            self.config, self.logger, enabled=self.config.enable_async_ai
        )

        # HTTP session shared across requests (connection pooling).
        self.session = requests.Session()

        # Database connection
        self.db = None
        self._init_database()

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
            'no_description': 0,
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
        self.logger.info("Starting job description backfill (GraphQL API)...")

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
        for i, (job_id, url, title) in enumerate(jobs, 1):
            self.logger.info(f"[{i}/{len(jobs)}] Processing job {job_id}: {title[:50]}...")
            self._process_job(job_id, url, title)

            # Polite delay between requests.
            time.sleep(self.config.delay + random.uniform(0, 1))

    def _run_concurrent(self, jobs: List[Tuple]):
        """Run backfill in concurrent mode with multiple worker threads"""
        self.logger.info(f"✓ {self.config.workers} workers ready for concurrent processing")

        with ThreadPoolExecutor(max_workers=self.config.workers, thread_name_prefix='Worker') as executor:
            futures = []
            for i, (job_id, url, title) in enumerate(jobs, 1):
                future = executor.submit(self._process_single_job, (job_id, url, title), i, len(jobs))
                futures.append(future)
                # Small stagger so requests don't all fire on the same instant.
                time.sleep(min(self.config.delay, 1.0) / self.config.workers)

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.logger.error(f"Worker error: {e}")

    def _process_single_job(self, job_data: Tuple, job_index: int, total_jobs: int) -> bool:
        """Process a single job (used for concurrent execution)"""
        job_id, url, title = job_data
        worker = threading.current_thread().name
        self.logger.info(f"[{job_index}/{total_jobs}] [Worker-{worker}] Processing job {job_id}: {title[:50]}...")
        return self._process_job(job_id, url, title, worker=worker)

    def _process_job(self, job_id, url, title, worker: str = None) -> bool:
        """Fetch one job description and persist it. Returns True on success."""
        prefix = f"  [Worker-{worker}]" if worker else " "

        description, suburb, status = self._fetch_with_retry(job_id)

        if status != 'success' or not description:
            if status == 'no_description':
                self.stats['no_description'] += 1
            else:
                self.stats['failed'] += 1
            self.logger.warning(f"{prefix} Failed: {status}")
            return False

        text_only = BeautifulSoup(description, 'lxml').get_text()[:100].replace('\n', ' ').strip()
        self.logger.info(f"{prefix} Description preview: {text_only}...")

        if self._update_job(job_id, description, suburb):
            self.logger.info(f"{prefix} Updated successfully (description: {len(description)} chars, suburb: {suburb})")
            self.stats['success'] += 1
            self._write_csv_row(job_id, title, url, suburb, description)

            text_description = BeautifulSoup(description, 'lxml').get_text(separator=' ').strip()
            self.ai_processor.queue_analysis(job_id, text_description)
            return True

        self.stats['failed'] += 1
        return False

    def _fetch_with_retry(self, job_id) -> Tuple[Optional[str], Optional[str], str]:
        """Fetch a job description via GraphQL, retrying transient failures."""
        status = 'request_error'
        for attempt in range(self.config.max_job_retries + 1):
            description, suburb, status = fetch_job_detail(
                job_id,
                timeout=self.config.request_timeout,
                session=self.session,
                logger=self.logger,
            )

            if status not in TRANSIENT_STATUSES:
                return description, suburb, status

            # Transient: back off and retry.
            if attempt < self.config.max_job_retries:
                backoff = self.config.delay * (attempt + 1)
                self.logger.warning(
                    f"  Transient failure ({status}) for job {job_id}, "
                    f"retry {attempt + 1}/{self.config.max_job_retries} after {backoff:.1f}s"
                )
                time.sleep(backoff)

        return None, None, status

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
        self.logger.info(f"No description available: {self.stats['no_description']}")
        self.logger.info(f"Success rate: {self.stats['success']/max(self.stats['total'],1)*100:.1f}%")

        if self.config.enable_async_ai:
            self.logger.info("-" * 50)
            self.logger.info("AI ANALYSIS (async)")
            self.logger.info(f"Tech stack analyzed: {ai_stats.get('tech_analyzed', 0)}")
            self.logger.info(f"Tech stack failures: {ai_stats.get('tech_failed', 0)}")
            self.logger.info(f"Tech stack skipped: {ai_stats.get('tech_skipped', 0)}")
            self.logger.info(f"Salary normalized: {ai_stats.get('salary_normalized', 0)}")
            self.logger.info(f"Salary skipped (no pay range): {ai_stats.get('salary_skipped', 0)}")
            self.logger.info(f"Salary failures: {ai_stats.get('salary_failed', 0)}")

        self.logger.info("=" * 50)

    def get_stats(self) -> dict:
        """Get combined statistics"""
        stats = self.stats.copy()
        stats.update(self.ai_processor.get_stats())
        return stats
