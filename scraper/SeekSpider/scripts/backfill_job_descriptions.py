#!/usr/bin/env python3
"""
Backfill missing job descriptions from Seek job pages.

This script fetches job descriptions for records where JobDescription is empty,
starting from the most recent jobs. Uses undetected-chromedriver to bypass Cloudflare.

Usage:
    python backfill_job_descriptions.py [--limit 100] [--delay 5]
"""

import argparse
import csv
import logging
import os
import queue
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env from project root
from dotenv import load_dotenv
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

from core.config import config
from core.database import DatabaseManager
from core.output_manager import OutputManager


def setup_logging(region: str = None):
    """Setup logging to both console and file, and create CSV log file"""
    # Use OutputManager for directory structure
    output_manager = OutputManager('backfill_logs', region=region)
    output_dir = output_manager.setup()

    timestamp = output_manager.timestamp
    log_file = output_manager.get_file_path(f'backfill_{timestamp}.log')
    csv_file = output_manager.get_file_path(f'backfill_{timestamp}.csv')

    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger('backfill')
    logger.setLevel(logging.INFO)

    # Clear any existing handlers
    logger.handlers.clear()

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    logger.addHandler(console_handler)

    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Log file: {log_file}")
    logger.info(f"CSV file: {csv_file}")
    return logger, csv_file


class JobDescriptionBackfiller:
    """Backfill missing job descriptions using undetected-chromedriver"""

    # Restart driver every N jobs to prevent memory leaks and crashes
    DRIVER_RESTART_INTERVAL = 30
    # Maximum consecutive failures before forcing driver restart
    MAX_CONSECUTIVE_FAILURES = 3
    # Maximum retries for a single job
    MAX_JOB_RETRIES = 2

    def __init__(self, delay: float = 5.0, logger=None, headless: bool = True, use_xvfb: bool = False, include_inactive: bool = False, csv_file: str = None, enable_async_ai: bool = True, region_filter: str = None, workers: int = 1):
        self.delay = delay
        self.logger = logger or logging.getLogger('backfill')
        self.db = DatabaseManager(config)
        self.headless = headless
        self.use_xvfb = use_xvfb
        self.include_inactive = include_inactive
        self.region_filter = region_filter  # Filter jobs by region
        self.workers = max(1, min(workers, 5))  # Limit workers between 1-5
        self.driver = None
        self.virtual_display = None
        self.driver_restarts = 0
        self.csv_file = csv_file
        self.csv_writer = None
        self.csv_handle = None
        self.enable_async_ai = enable_async_ai

        # Thread-safe lock for database and CSV operations
        self.db_lock = threading.Lock()
        self.csv_lock = threading.Lock()

        # Counter for periodic restart
        self.jobs_since_restart = 0
        self.consecutive_failures = 0

        # Async AI analysis queue and thread
        self.ai_queue: queue.Queue = queue.Queue()
        self.ai_thread: Optional[threading.Thread] = None
        self.ai_stop_event = threading.Event()
        self.ai_db = None
        self.tech_analyzer = None
        self.salary_normalizer = None

        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'cloudflare_blocked': 0,
            'driver_restarts': 0,
            'ai_analyzed': 0,
            'ai_failed': 0,
            'salary_normalized': 0,
            'salary_skipped': 0,
            'salary_failed': 0,
        }

    def _init_driver(self):
        """Initialize Chrome driver with virtual display support"""
        # Check if we have a real display
        # On macOS, we don't need DISPLAY env var - Chrome can display windows natively
        import platform
        is_macos = platform.system() == 'Darwin'
        display = os.environ.get('DISPLAY')
        has_real_display = is_macos or bool(display)

        # Check if we're in a container with Chromium
        in_container = os.path.exists('/usr/bin/chromium') or os.path.exists('/usr/bin/chromium-browser')

        # Start virtual display if:
        # 1. Explicitly requested via --xvfb, OR
        # 2. No real display and not in headless mode
        need_xvfb = self.use_xvfb or (not has_real_display and not self.headless)
        xvfb_started = False

        if need_xvfb and not self.virtual_display:
            try:
                from pyvirtualdisplay import Display
                self.virtual_display = Display(visible=False, size=(1920, 1080))
                self.virtual_display.start()
                self.logger.info("Virtual display started (Xvfb)")
                xvfb_started = True
            except ImportError:
                self.logger.warning("pyvirtualdisplay not installed")
                if not has_real_display:
                    self.logger.warning("No display available, using headless mode")
                    self.headless = True
            except Exception as e:
                self.logger.warning(f"Failed to start virtual display: {e}")
                if not has_real_display:
                    self.logger.warning("No display available, using headless mode")
                    self.headless = True

        # Try to use undetected-chromedriver first (works better against Cloudflare)
        use_undetected = True

        if in_container:
            # In container, try undetected-chromedriver with system Chromium
            try:
                import undetected_chromedriver as uc

                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument('--headless=new')

                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--lang=en-AU')
                options.add_argument('--disable-blink-features=AutomationControlled')

                # Set Chromium binary for container
                chromium_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else '/usr/bin/chromium-browser'
                options.binary_location = chromium_path
                self.logger.info(f"Using undetected-chromedriver with Chromium at: {chromium_path}")

                self.driver = uc.Chrome(options=options, version_main=None, browser_executable_path=chromium_path)
                self.logger.info("Successfully initialized undetected-chromedriver in container")

            except Exception as e:
                self.logger.warning(f"Failed to use undetected-chromedriver in container: {e}")
                self.logger.info("Falling back to standard Selenium...")
                use_undetected = False

                # Fallback to standard Selenium
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options

                options = Options()
                if self.headless:
                    options.add_argument('--headless=new')

                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--lang=en-AU')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                options.add_experimental_option('excludeSwitches', ['enable-automation'])
                options.add_experimental_option('useAutomationExtension', False)

                chromium_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else '/usr/bin/chromium-browser'
                options.binary_location = chromium_path
                self.logger.info(f"Using Chromium at: {chromium_path}")

                chromedriver_path = '/usr/bin/chromedriver'
                if os.path.exists(chromedriver_path):
                    service = Service(executable_path=chromedriver_path)
                    self.logger.info(f"Using chromedriver at: {chromedriver_path}")
                else:
                    service = Service()

                self.driver = webdriver.Chrome(service=service, options=options)
        else:
            # Use undetected-chromedriver for local development
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')

            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--lang=en-AU')
            options.add_argument('--disable-blink-features=AutomationControlled')

            self.driver = uc.Chrome(options=options, version_main=None)

        self.driver.set_page_load_timeout(60)
        self.logger.info(f"Chrome driver initialized (headless={self.headless}, xvfb={xvfb_started}, real_display={has_real_display}, container={in_container})")

    def _close_driver(self):
        """Close the Chrome driver and virtual display"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

        # Close virtual display if it was started
        if hasattr(self, 'virtual_display') and self.virtual_display:
            try:
                self.virtual_display.stop()
                self.logger.info("Virtual display stopped")
            except:
                pass
            self.virtual_display = None

    def get_jobs_without_description(self, limit: int = None) -> list:
        """Get jobs where JobDescription is empty, filtered by region if specified"""
        params = []

        # Build WHERE clause conditions
        conditions = ['("JobDescription" IS NULL OR "JobDescription" = \'\' OR "JobDescription" = \'None\')']

        if not self.include_inactive:
            conditions.append('"IsActive" = \'True\'')

        if self.region_filter:
            conditions.append('"Region" = %s')
            params.append(self.region_filter)

        where_clause = ' AND '.join(conditions)
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f'''
            SELECT "Id", "Url", "JobTitle"
            FROM "{config.POSTGRESQL_TABLE}"
            WHERE {where_clause}
            ORDER BY "CreatedAt" DESC
            {limit_clause}
        '''

        try:
            return self.db.execute_query(query, tuple(params) if params else None)
        except Exception as e:
            self.logger.error(f"Error fetching jobs: {e}")
            return []

    def _is_driver_alive(self) -> bool:
        """Check if the Chrome driver is still alive"""
        try:
            _ = self.driver.current_url
            return True
        except:
            return False

    def _restart_driver(self, reason: str = "unknown"):
        """Restart the Chrome driver"""
        self.logger.warning(f"  Restarting driver (reason: {reason})...")
        self.stats['driver_restarts'] += 1

        # Close existing driver (if any)
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

        # Wait before restarting
        time.sleep(2)

        # Reinitialize driver (keep virtual display running)
        self._init_driver()
        self.jobs_since_restart = 0
        self.consecutive_failures = 0
        self.logger.info("  Driver restarted successfully")

    def _periodic_restart_check(self):
        """Check if driver should be restarted based on job count"""
        if self.jobs_since_restart >= self.DRIVER_RESTART_INTERVAL:
            self.logger.info(f"Periodic restart: processed {self.jobs_since_restart} jobs since last restart")
            self._restart_driver(reason=f"periodic restart after {self.DRIVER_RESTART_INTERVAL} jobs")
            return True
        return False

    def _init_async_ai(self):
        """Initialize async AI analysis thread"""
        if not self.enable_async_ai:
            return

        try:
            from core.ai_client import AIClient
            from core.logger import Logger
            from utils.tech_stack_analyzer import TechStackAnalyzer
            from utils.salary_normalizer import SalaryNormalizer

            # Create a separate database connection for AI thread
            ai_db = DatabaseManager(config)
            ai_client = AIClient(config)
            ai_logger = Logger("async_ai")

            self.ai_db = ai_db
            self.tech_analyzer = TechStackAnalyzer(ai_db, ai_client, ai_logger)
            self.salary_normalizer = SalaryNormalizer(ai_db, ai_client, ai_logger)

            # Start AI worker thread
            self.ai_thread = threading.Thread(target=self._ai_worker, daemon=True)
            self.ai_thread.start()
            self.logger.info("Async AI analysis thread started (TechStack + Salary)")
        except Exception as e:
            self.logger.warning(f"Failed to initialize async AI: {e}")
            self.enable_async_ai = False

    def _ai_worker(self):
        """Worker thread for async AI analysis"""
        self.logger.info("AI worker thread running...")

        while not self.ai_stop_event.is_set():
            try:
                # Wait for a job with timeout to allow checking stop event
                try:
                    job_id, description = self.ai_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if job_id is None:  # Sentinel value to stop
                    break

                # Perform Tech Stack analysis
                try:
                    tech_result = self.tech_analyzer.analyze_job(job_id, description)
                    if tech_result:
                        self.stats['ai_analyzed'] += 1
                        self.logger.info(f"  [AI-Tech] Analyzed job {job_id}: {tech_result}")
                    else:
                        self.stats['ai_failed'] += 1
                except Exception as e:
                    self.stats['ai_failed'] += 1
                    self.logger.warning(f"  [AI-Tech] Failed to analyze job {job_id}: {e}")

                # Perform Salary normalization
                try:
                    # Get pay_range from database
                    query = f'SELECT "PayRange" FROM "{config.POSTGRESQL_TABLE}" WHERE "Id" = %s'
                    result = self.ai_db.execute_query(query, (job_id,))
                    if result and result[0][0]:
                        pay_range = result[0][0]
                        salary_result = self.salary_normalizer.normalize_salary(job_id, pay_range)
                        if salary_result and (salary_result[0] > 0 or salary_result[1] > 0):
                            self.stats['salary_normalized'] += 1
                            self.logger.info(f"  [AI-Salary] Normalized job {job_id}: {salary_result}")
                        else:
                            self.stats['salary_skipped'] += 1
                    else:
                        self.stats['salary_skipped'] += 1
                except Exception as e:
                    self.stats['salary_failed'] += 1
                    self.logger.warning(f"  [AI-Salary] Failed to normalize job {job_id}: {e}")

                self.ai_queue.task_done()

            except Exception as e:
                self.logger.error(f"AI worker error: {e}")

        self.logger.info("AI worker thread stopped")

    def _queue_ai_analysis(self, job_id: int, description: str):
        """Queue a job for async AI analysis"""
        if self.enable_async_ai and self.ai_thread and self.ai_thread.is_alive():
            try:
                self.ai_queue.put_nowait((job_id, description))
            except queue.Full:
                self.logger.warning(f"  AI queue full, skipping analysis for job {job_id}")

    def _stop_async_ai(self):
        """Stop the async AI analysis thread"""
        if self.ai_thread and self.ai_thread.is_alive():
            self.logger.info("Stopping async AI thread...")
            self.ai_stop_event.set()
            # Put sentinel value to unblock the queue
            try:
                self.ai_queue.put_nowait((None, None))
            except:
                pass
            self.ai_thread.join(timeout=10)
            self.logger.info("Async AI thread stopped")

    def fetch_job_description(self, url: str) -> tuple:
        """Fetch job description from URL using Chrome"""
        # Check if driver is alive, restart if needed
        if not self._is_driver_alive():
            self._restart_driver()

        try:
            self.driver.get(url)

            # Wait for page to potentially pass Cloudflare
            time.sleep(3)

            # Check for Cloudflare challenge
            page_source = self.driver.page_source
            if 'challenge' in page_source.lower() or 'cf-browser-verification' in page_source.lower():
                self.logger.warning("  Cloudflare challenge detected, waiting...")
                time.sleep(10)  # Wait for challenge to complete
                page_source = self.driver.page_source

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

    def update_job(self, job_id: int, description: str, suburb: str = None):
        """Update job description in database (thread-safe with race condition protection)"""
        try:
            job_data = {'JobDescription': description}
            if suburb:
                job_data['Suburb'] = suburb

            with self.db_lock:
                affected_rows = self.db.update_job(job_id, job_data)

            # Return True only if row was actually updated
            # If affected_rows is 0, it means another process already updated this job
            if affected_rows == 0:
                self.logger.warning(f"  Job {job_id} was already updated by another process (skipped)")
                return False

            return True
        except Exception as e:
            self.logger.error(f"  Database update failed: {e}")
            return False

    def _init_csv(self):
        """Initialize CSV file for logging scraped job descriptions"""
        if self.csv_file:
            self.csv_handle = open(self.csv_file, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_handle)
            # Write header
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
            # Extract text from HTML for cleaner CSV output
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
                self.csv_handle.flush()  # Ensure data is written immediately

    def _process_single_job(self, job_data, job_index, total_jobs, driver_instance):
        """Process a single job (used for concurrent execution)"""
        job_id, url, title = job_data
        self.logger.info(f"[{job_index}/{total_jobs}] [Worker-{threading.current_thread().name}] Processing job {job_id}: {title[:50]}...")

        # Try to fetch job description with retry logic
        description, suburb, status = self._fetch_with_retry_concurrent(url, driver_instance)

        if status == 'cloudflare':
            self.logger.warning(f"  [Worker-{threading.current_thread().name}] Cloudflare blocked - skipping")
            self.stats['cloudflare_blocked'] += 1
            return False

        if status == 'success' and description:
            # Log first 100 chars of description
            text_only = BeautifulSoup(description, 'lxml').get_text()[:100].replace('\n', ' ').strip()
            self.logger.info(f"  [Worker-{threading.current_thread().name}] Description preview: {text_only}...")

            if self.update_job(job_id, description, suburb):
                self.logger.info(f"  [Worker-{threading.current_thread().name}] Updated successfully (description: {len(description)} chars, suburb: {suburb})")
                self.stats['success'] += 1
                # Write to CSV log
                self._write_csv_row(job_id, title, url, suburb, description)

                # Queue for async AI analysis
                text_description = BeautifulSoup(description, 'lxml').get_text(separator=' ').strip()
                self._queue_ai_analysis(job_id, text_description)
                return True
            else:
                self.stats['failed'] += 1
                return False
        else:
            self.logger.warning(f"  [Worker-{threading.current_thread().name}] Failed: {status}")
            self.stats['failed'] += 1
            return False

    def _fetch_with_retry_concurrent(self, url: str, driver_instance) -> tuple:
        """Fetch job description with retry logic (for concurrent execution)"""
        for attempt in range(self.MAX_JOB_RETRIES + 1):
            try:
                description, suburb, status = self._fetch_job_description_with_driver(url, driver_instance)

                # Handle driver crash
                if status == 'driver_crashed':
                    self.logger.warning(f"  Driver crashed (attempt {attempt + 1}/{self.MAX_JOB_RETRIES + 1})")
                    if attempt < self.MAX_JOB_RETRIES:
                        time.sleep(2)
                        continue
                    else:
                        return None, None, 'max_retries_exceeded'

                return description, suburb, status

            except Exception as e:
                self.logger.error(f"  Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_JOB_RETRIES:
                    time.sleep(2)
                else:
                    return None, None, f'exception: {e}'

        return None, None, 'max_retries_exceeded'

    def _fetch_job_description_with_driver(self, url: str, driver_instance) -> tuple:
        """Fetch job description using provided driver instance"""
        try:
            driver_instance.get(url)

            # Wait for page to potentially pass Cloudflare
            time.sleep(3)

            # Check for Cloudflare challenge
            page_source = driver_instance.page_source
            if 'challenge' in page_source.lower() or 'cf-browser-verification' in page_source.lower():
                self.logger.warning("  Cloudflare challenge detected, waiting...")
                time.sleep(10)
                page_source = driver_instance.page_source

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

    def run(self, limit: int = None):
        """Run the backfill process"""
        self.logger.info("=" * 60)
        self.logger.info("Starting job description backfill...")
        region_msg = f"for region: {self.region_filter}" if self.region_filter else "for all regions"
        limit_msg = f"up to {limit}" if limit else "all"
        self.logger.info(f"Fetching {limit_msg} jobs without descriptions {region_msg}...")

        if self.region_filter:
            self.logger.info(f"⚠️  REGION FILTER ACTIVE: Only processing jobs with Region='{self.region_filter}'")
            self.logger.info(f"    This prevents conflicts with other region backfill processes")
        else:
            self.logger.warning("⚠️  NO REGION FILTER: Processing ALL regions (may cause conflicts if multiple backfills run simultaneously)")

        if self.workers > 1:
            self.logger.info(f"🚀 CONCURRENT MODE: Using {self.workers} workers for parallel processing")
        else:
            self.logger.info(f"📝 SERIAL MODE: Processing jobs one by one")

        self.logger.info("=" * 60)

        jobs = self.get_jobs_without_description(limit)
        self.stats['total'] = len(jobs)

        if self.region_filter:
            self.logger.info(f"✓ Found {len(jobs)} jobs to process for region '{self.region_filter}'")
        else:
            self.logger.info(f"Found {len(jobs)} jobs to process (all regions)")


        if not jobs:
            self.logger.info("No jobs to process.")
            return

        try:
            self._init_csv()
            self._init_async_ai()

            if self.workers > 1:
                # Concurrent execution
                self._run_concurrent(jobs)
            else:
                # Serial execution (original behavior)
                self._run_serial(jobs)

        finally:
            self._stop_async_ai()
            self._close_csv()

        self._print_summary()

    def _run_serial(self, jobs):
        """Run backfill in serial mode (original behavior)"""
        self._init_driver()

        try:
            for i, (job_id, url, title) in enumerate(jobs, 1):
                self.logger.info(f"[{i}/{len(jobs)}] Processing job {job_id}: {title[:50]}...")

                # Check for periodic restart before processing
                self._periodic_restart_check()

                # Try to fetch job description with retry logic
                description, suburb, status = self._fetch_with_retry(url)

                if status == 'cloudflare':
                    self.logger.warning("  Cloudflare blocked - skipping")
                    self.stats['cloudflare_blocked'] += 1
                    self.consecutive_failures += 1
                    time.sleep(self.delay * 2)

                    # Check if too many consecutive failures
                    if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                        self.logger.warning(f"  {self.consecutive_failures} consecutive failures, restarting driver...")
                        self._restart_driver(reason="consecutive failures")
                    continue

                if status == 'success' and description:
                    # Reset failure counter on success
                    self.consecutive_failures = 0

                    # Log first 100 chars of description
                    text_only = BeautifulSoup(description, 'lxml').get_text()[:100].replace('\n', ' ').strip()
                    self.logger.info(f"  Description preview: {text_only}...")

                    if self.update_job(job_id, description, suburb):
                        self.logger.info(f"  Updated successfully (description: {len(description)} chars, suburb: {suburb})")
                        self.stats['success'] += 1
                        # Write to CSV log
                        self._write_csv_row(job_id, title, url, suburb, description)

                        # Queue for async AI analysis (use the plain text for AI)
                        text_description = BeautifulSoup(description, 'lxml').get_text(separator=' ').strip()
                        self._queue_ai_analysis(job_id, text_description)
                    else:
                        self.stats['failed'] += 1
                        self.consecutive_failures += 1
                else:
                    self.logger.warning(f"  Failed: {status}")
                    self.stats['failed'] += 1
                    self.consecutive_failures += 1

                    # Check if too many consecutive failures
                    if self.consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
                        self.logger.warning(f"  {self.consecutive_failures} consecutive failures, restarting driver...")
                        self._restart_driver(reason="consecutive failures")

                # Increment job counter
                self.jobs_since_restart += 1

                # Random delay
                delay = self.delay + random.uniform(0, 2)
                time.sleep(delay)

        finally:
            self._close_driver()

    def _run_concurrent(self, jobs):
        """Run backfill in concurrent mode with multiple workers"""
        self.logger.info(f"Initializing {self.workers} Chrome driver instances...")

        # Create driver instances for each worker
        drivers = []
        for i in range(self.workers):
            try:
                driver = self._create_driver_instance()
                drivers.append(driver)
                self.logger.info(f"  Worker {i+1}/{self.workers} initialized")
            except Exception as e:
                self.logger.error(f"  Failed to initialize worker {i+1}: {e}")

        if not drivers:
            self.logger.error("Failed to initialize any drivers, falling back to serial mode")
            self._run_serial(jobs)
            return

        self.logger.info(f"✓ {len(drivers)} workers ready for concurrent processing")

        try:
            # Use ThreadPoolExecutor for concurrent processing
            with ThreadPoolExecutor(max_workers=len(drivers), thread_name_prefix='Worker') as executor:
                # Submit jobs to thread pool
                futures = []
                for i, job_data in enumerate(jobs, 1):
                    # Round-robin assign driver to each job
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

                    # Add delay between starting jobs to avoid overwhelming
                    time.sleep(0.5)

                # Wait for all jobs to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.error(f"Worker error: {e}")

        finally:
            # Clean up all driver instances
            self.logger.info("Cleaning up driver instances...")
            for i, driver in enumerate(drivers):
                try:
                    driver.quit()
                    self.logger.info(f"  Worker {i+1} driver closed")
                except Exception as e:
                    self.logger.error(f"  Error closing worker {i+1}: {e}")

            # Close virtual display if it was started
            if hasattr(self, 'virtual_display') and self.virtual_display:
                try:
                    self.virtual_display.stop()
                    self.logger.info("Virtual display stopped")
                except:
                    pass

    def _create_driver_instance(self):
        """Create a new Chrome driver instance"""
        # Check if we have a real display
        import platform
        is_macos = platform.system() == 'Darwin'
        display = os.environ.get('DISPLAY')
        has_real_display = is_macos or bool(display)

        # Check if we're in a container with Chromium
        in_container = os.path.exists('/usr/bin/chromium') or os.path.exists('/usr/bin/chromium-browser')

        # Start virtual display if needed (only once for all drivers)
        need_xvfb = self.use_xvfb or (not has_real_display and not self.headless)

        if need_xvfb and not self.virtual_display:
            try:
                from pyvirtualdisplay import Display
                self.virtual_display = Display(visible=False, size=(1920, 1080))
                self.virtual_display.start()
                self.logger.info("Virtual display started (Xvfb)")
            except ImportError:
                self.logger.warning("pyvirtualdisplay not installed")
                if not has_real_display:
                    self.headless = True
            except Exception as e:
                self.logger.warning(f"Failed to start virtual display: {e}")
                if not has_real_display:
                    self.headless = True

        # Try to use undetected-chromedriver
        if in_container:
            try:
                import undetected_chromedriver as uc

                options = uc.ChromeOptions()
                if self.headless:
                    options.add_argument('--headless=new')

                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--lang=en-AU')
                options.add_argument('--disable-blink-features=AutomationControlled')

                chromium_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else '/usr/bin/chromium-browser'
                options.binary_location = chromium_path

                driver = uc.Chrome(options=options, version_main=None, browser_executable_path=chromium_path)
                driver.set_page_load_timeout(60)
                return driver

            except Exception as e:
                self.logger.warning(f"Failed to use undetected-chromedriver: {e}")
                # Fallback to standard Selenium
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options

                options = Options()
                if self.headless:
                    options.add_argument('--headless=new')

                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--lang=en-AU')

                chromium_path = '/usr/bin/chromium' if os.path.exists('/usr/bin/chromium') else '/usr/bin/chromium-browser'
                options.binary_location = chromium_path

                chromedriver_path = '/usr/bin/chromedriver'
                if os.path.exists(chromedriver_path):
                    service = Service(executable_path=chromedriver_path)
                else:
                    service = Service()

                driver = webdriver.Chrome(service=service, options=options)
                driver.set_page_load_timeout(60)
                return driver
        else:
            import undetected_chromedriver as uc

            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument('--headless=new')

            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--lang=en-AU')
            options.add_argument('--disable-blink-features=AutomationControlled')

            driver = uc.Chrome(options=options, version_main=None)
            driver.set_page_load_timeout(60)
            return driver

    def _fetch_with_retry(self, url: str) -> tuple:
        """Fetch job description with retry logic"""
        for attempt in range(self.MAX_JOB_RETRIES + 1):
            try:
                # Check if driver is alive
                if not self._is_driver_alive():
                    self._restart_driver(reason="driver not responding")
                    time.sleep(2)

                description, suburb, status = self.fetch_job_description(url)

                # Handle driver crash
                if status == 'driver_crashed':
                    self.logger.warning(f"  Driver crashed (attempt {attempt + 1}/{self.MAX_JOB_RETRIES + 1})")
                    self._restart_driver(reason="driver crashed")
                    time.sleep(2)

                    if attempt < self.MAX_JOB_RETRIES:
                        continue
                    else:
                        return None, None, 'max_retries_exceeded'

                return description, suburb, status

            except Exception as e:
                self.logger.error(f"  Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < self.MAX_JOB_RETRIES:
                    self._restart_driver(reason=f"exception: {e}")
                    time.sleep(2)
                else:
                    return None, None, f'exception: {e}'

        return None, None, 'max_retries_exceeded'

    def _print_summary(self):
        """Print summary"""
        self.logger.info("=" * 50)
        self.logger.info("BACKFILL SUMMARY")
        self.logger.info("=" * 50)
        self.logger.info(f"Total jobs processed: {self.stats['total']}")
        self.logger.info(f"Successfully updated: {self.stats['success']}")
        self.logger.info(f"Failed: {self.stats['failed']}")
        self.logger.info(f"Cloudflare blocked: {self.stats['cloudflare_blocked']}")
        self.logger.info(f"Driver restarts: {self.stats['driver_restarts']}")
        self.logger.info(f"Success rate: {self.stats['success']/max(self.stats['total'],1)*100:.1f}%")
        if self.enable_async_ai:
            self.logger.info("-" * 50)
            self.logger.info("AI ANALYSIS (async)")
            self.logger.info(f"Tech stack analyzed: {self.stats['ai_analyzed']}")
            self.logger.info(f"Tech stack failures: {self.stats['ai_failed']}")
            self.logger.info(f"Salary normalized: {self.stats['salary_normalized']}")
            self.logger.info(f"Salary skipped (no pay range): {self.stats['salary_skipped']}")
            self.logger.info(f"Salary failures: {self.stats['salary_failed']}")
        self.logger.info("=" * 50)


def run_ai_analysis(logger):
    """Run AI analysis after backfill completes"""
    logger.info("=" * 50)
    logger.info("STARTING AI ANALYSIS")
    logger.info("=" * 50)

    try:
        from core.ai_client import AIClient
        from core.database import DatabaseManager
        from core.logger import Logger
        from utils.tech_stack_analyzer import TechStackAnalyzer
        from utils.salary_normalizer import SalaryNormalizer

        # Initialize components
        db_manager = DatabaseManager(config)
        ai_client = AIClient(config)
        ai_logger = Logger("ai_analysis")

        # Run Tech Stack Analysis
        logger.info("Running Tech Stack Analysis...")
        tech_analyzer = TechStackAnalyzer(db_manager, ai_client, ai_logger)
        tech_analyzer.process_all_jobs()
        logger.info("Tech Stack Analysis completed.")

        # Run Salary Normalization
        logger.info("Running Salary Normalization...")
        salary_normalizer = SalaryNormalizer(db_manager, ai_client, ai_logger)
        salary_normalizer.process_all_jobs()
        logger.info("Salary Normalization completed.")

        logger.info("=" * 50)
        logger.info("AI ANALYSIS COMPLETED")
        logger.info("=" * 50)

    except Exception as e:
        logger.error(f"AI Analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    parser = argparse.ArgumentParser(description='Backfill missing job descriptions')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum number of jobs to process (default: no limit)')
    parser.add_argument('--delay', type=float, default=5.0,
                        help='Base delay between requests in seconds (default: 5.0)')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode (may reduce success rate)')
    parser.add_argument('--xvfb', action='store_true',
                        help='Use virtual display (Xvfb) for running in containers or headless environments')
    parser.add_argument('--skip-ai', action='store_true',
                        help='Skip AI analysis after backfill (post-processing)')
    parser.add_argument('--no-async-ai', action='store_true',
                        help='Disable async AI analysis during scraping (enabled by default)')
    parser.add_argument('--include-inactive', action='store_true',
                        help='Include inactive jobs in backfill (default: only active jobs)')
    parser.add_argument('--region', type=str, default=None,
                        help='Region for output organization (e.g., Sydney, Perth)')
    parser.add_argument('--region-filter', type=str, default=None,
                        help='Filter jobs by region (e.g., Sydney, Perth). If not specified, processes all regions.')
    parser.add_argument('--restart-interval', type=int, default=30,
                        help='Restart Chrome driver every N jobs (default: 30, only for serial mode)')
    parser.add_argument('--workers', type=int, default=1,
                        help='Number of concurrent workers (1-5). Default: 1 (serial mode). Use 2-3 for faster processing.')

    args = parser.parse_args()

    logger, csv_file = setup_logging(region=args.region)
    logger.info(f"Arguments: limit={args.limit}, delay={args.delay}, headless={args.headless}, xvfb={args.xvfb}, skip_ai={args.skip_ai}, no_async_ai={args.no_async_ai}, include_inactive={args.include_inactive}, region={args.region}, region_filter={args.region_filter}, restart_interval={args.restart_interval}, workers={args.workers}")

    backfiller = JobDescriptionBackfiller(
        delay=args.delay,
        logger=logger,
        headless=args.headless,
        use_xvfb=args.xvfb,
        include_inactive=args.include_inactive,
        csv_file=csv_file,
        enable_async_ai=not args.no_async_ai,
        region_filter=args.region_filter,
        workers=args.workers
    )

    # Override restart interval if specified
    if args.restart_interval:
        backfiller.DRIVER_RESTART_INTERVAL = args.restart_interval

    backfiller.run(limit=args.limit)

    # Run AI analysis if backfill was successful and not skipped
    if not args.skip_ai and backfiller.stats['success'] > 0:
        run_ai_analysis(logger)
    elif args.skip_ai:
        logger.info("AI analysis skipped (--skip-ai flag)")
    else:
        logger.info("AI analysis skipped (no successful backfills)")


if __name__ == '__main__':
    main()
