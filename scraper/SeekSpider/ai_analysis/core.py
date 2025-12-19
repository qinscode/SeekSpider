"""
Core AI Analysis functionality.
"""

import logging
import queue
import threading
from typing import Optional, Dict, List, Tuple

from .config import AIAnalysisConfig, AnalysisType


class AIAnalyzer:
    """Main AI analyzer that orchestrates tech stack and salary analysis"""

    def __init__(self, config: AIAnalysisConfig = None, logger: logging.Logger = None):
        self.config = config or AIAnalysisConfig()
        self.logger = logger or logging.getLogger('ai_analysis')

        # Initialize components lazily
        self._db = None
        self._ai_client = None
        self._tech_analyzer = None
        self._salary_normalizer = None
        self._app_config = None

        self.stats = {
            'tech_analyzed': 0,
            'tech_failed': 0,
            'tech_skipped': 0,
            'salary_normalized': 0,
            'salary_skipped': 0,
            'salary_failed': 0,
        }

    def _init_components(self):
        """Initialize AI components"""
        if self._db is not None:
            return

        from core.config import config as app_config
        from core.database import DatabaseManager
        from core.ai_client import AIClient
        from core.logger import Logger
        from utils.tech_stack_analyzer import TechStackAnalyzer
        from utils.salary_normalizer import SalaryNormalizer

        self._app_config = app_config
        self._db = DatabaseManager(app_config)
        self._ai_client = AIClient(app_config, self.logger)  # Pass logger

        ai_logger = Logger("ai_analysis")
        self._tech_analyzer = TechStackAnalyzer(self._db, self._ai_client, ai_logger)
        self._salary_normalizer = SalaryNormalizer(self._db, self._ai_client, ai_logger)

    def run(self):
        """Run AI analysis based on configuration"""
        self._init_components()

        self.logger.info("=" * 60)
        self.logger.info("Starting AI Analysis...")

        if self.config.region_filter:
            self.logger.info(f"Region filter: {self.config.region_filter}")

        if self.config.should_run_tech_stack():
            self.logger.info("Running Tech Stack Analysis...")
            self._run_tech_stack_analysis()

        if self.config.should_run_salary():
            self.logger.info("Running Salary Normalization...")
            self._run_salary_analysis()

        self._print_summary()

    def _run_tech_stack_analysis(self):
        """Run tech stack analysis on jobs"""
        jobs = self._get_jobs_for_tech_analysis()

        self.logger.info(f"Found {len(jobs)} jobs for tech stack analysis")

        for i, (job_id, description) in enumerate(jobs, 1):
            if self.config.limit and i > self.config.limit:
                break

            try:
                result = self._tech_analyzer.analyze_job(job_id, description)
                if result:
                    self.stats['tech_analyzed'] += 1
                    self.logger.info(f"[{i}/{len(jobs)}] Tech analyzed job {job_id}: {result}")
                else:
                    self.stats['tech_skipped'] += 1
            except Exception as e:
                self.stats['tech_failed'] += 1
                self.logger.warning(f"[{i}/{len(jobs)}] Tech analysis failed for job {job_id}: {e}")

    def _run_salary_analysis(self):
        """Run salary normalization on jobs"""
        jobs = self._get_jobs_for_salary_analysis()

        self.logger.info(f"Found {len(jobs)} jobs for salary normalization")

        for i, (job_id, pay_range) in enumerate(jobs, 1):
            if self.config.limit and i > self.config.limit:
                break

            try:
                result = self._salary_normalizer.normalize_salary(job_id, pay_range)
                if result and (result[0] > 0 or result[1] > 0):
                    self.stats['salary_normalized'] += 1
                    self.logger.info(f"[{i}/{len(jobs)}] Salary normalized job {job_id}: {result}")
                else:
                    self.stats['salary_skipped'] += 1
            except Exception as e:
                self.stats['salary_failed'] += 1
                self.logger.warning(f"[{i}/{len(jobs)}] Salary normalization failed for job {job_id}: {e}")

    def _get_jobs_for_tech_analysis(self) -> List[Tuple[int, str]]:
        """Get jobs that need tech stack analysis"""
        conditions = ['"JobDescription" IS NOT NULL', '"JobDescription" != \'\'']

        if self.config.only_missing:
            conditions.append('("TechStack" IS NULL OR "TechStack" = \'[]\' OR "TechStack" = \'\')')

        if self.config.region_filter:
            conditions.append(f'"Region" = \'{self.config.region_filter}\'')

        where_clause = ' AND '.join(conditions)
        limit_clause = f"LIMIT {self.config.limit}" if self.config.limit else ""

        query = f'''
            SELECT "Id", "JobDescription"
            FROM "{self._app_config.POSTGRESQL_TABLE}"
            WHERE {where_clause}
            ORDER BY "CreatedAt" DESC
            {limit_clause}
        '''

        try:
            return self._db.execute_query(query)
        except Exception as e:
            self.logger.error(f"Error fetching jobs for tech analysis: {e}")
            return []

    def _get_jobs_for_salary_analysis(self) -> List[Tuple[int, str]]:
        """Get jobs that need salary normalization"""
        conditions = ['"PayRange" IS NOT NULL', '"PayRange" != \'\'']

        if self.config.only_missing:
            conditions.append('("MinSalary" IS NULL OR "MinSalary" = 0)')

        if self.config.region_filter:
            conditions.append(f'"Region" = \'{self.config.region_filter}\'')

        where_clause = ' AND '.join(conditions)
        limit_clause = f"LIMIT {self.config.limit}" if self.config.limit else ""

        query = f'''
            SELECT "Id", "PayRange"
            FROM "{self._app_config.POSTGRESQL_TABLE}"
            WHERE {where_clause}
            ORDER BY "CreatedAt" DESC
            {limit_clause}
        '''

        try:
            return self._db.execute_query(query)
        except Exception as e:
            self.logger.error(f"Error fetching jobs for salary analysis: {e}")
            return []

    def analyze_single_job(self, job_id: int, description: str = None, pay_range: str = None) -> Dict:
        """Analyze a single job (for use by backfill module)"""
        self._init_components()
        results = {}

        if description and self.config.should_run_tech_stack():
            try:
                tech_result = self._tech_analyzer.analyze_job(job_id, description)
                results['tech_stack'] = tech_result
                if tech_result:
                    self.stats['tech_analyzed'] += 1
                else:
                    self.stats['tech_skipped'] += 1
            except Exception as e:
                self.stats['tech_failed'] += 1
                results['tech_error'] = str(e)

        if pay_range and self.config.should_run_salary():
            try:
                salary_result = self._salary_normalizer.normalize_salary(job_id, pay_range)
                results['salary'] = salary_result
                if salary_result and (salary_result[0] > 0 or salary_result[1] > 0):
                    self.stats['salary_normalized'] += 1
                else:
                    self.stats['salary_skipped'] += 1
            except Exception as e:
                self.stats['salary_failed'] += 1
                results['salary_error'] = str(e)

        return results

    def _print_summary(self):
        """Print analysis summary"""
        self.logger.info("=" * 50)
        self.logger.info("AI ANALYSIS SUMMARY")
        self.logger.info("=" * 50)

        if self.config.should_run_tech_stack():
            self.logger.info("Tech Stack Analysis:")
            self.logger.info(f"  Analyzed: {self.stats['tech_analyzed']}")
            self.logger.info(f"  Skipped: {self.stats['tech_skipped']}")
            self.logger.info(f"  Failed: {self.stats['tech_failed']}")

        if self.config.should_run_salary():
            self.logger.info("Salary Normalization:")
            self.logger.info(f"  Normalized: {self.stats['salary_normalized']}")
            self.logger.info(f"  Skipped: {self.stats['salary_skipped']}")
            self.logger.info(f"  Failed: {self.stats['salary_failed']}")

        # Print API key statistics
        if self._ai_client:
            key_status = self._ai_client.get_key_status()
            self.logger.info("API Key Status:")
            self.logger.info(f"  Total keys: {key_status['total_keys']}")
            self.logger.info(f"  Available keys: {key_status['available_keys']}")
            if key_status['exhausted_keys']:
                self.logger.info(f"  Exhausted keys: {key_status['exhausted_keys']}")

        self.logger.info("=" * 50)

    def get_stats(self) -> Dict[str, int]:
        """Get analysis statistics"""
        return self.stats.copy()


class AsyncAIAnalyzer:
    """Async wrapper for AI analysis (used by backfill module)"""

    def __init__(self, config: AIAnalysisConfig = None, logger: logging.Logger = None):
        self.config = config or AIAnalysisConfig()
        self.logger = logger or logging.getLogger('ai_analysis.async')

        self.ai_queue: queue.Queue = queue.Queue()
        self.ai_thread: Optional[threading.Thread] = None
        self.ai_stop_event = threading.Event()

        self._analyzer: Optional[AIAnalyzer] = None

        self.stats = {
            'tech_analyzed': 0,
            'tech_failed': 0,
            'salary_normalized': 0,
            'salary_skipped': 0,
            'salary_failed': 0,
        }

    def start(self) -> bool:
        """Start the async AI processing thread"""
        try:
            self._analyzer = AIAnalyzer(self.config, self.logger)
            self._analyzer._init_components()

            self.ai_thread = threading.Thread(target=self._worker, daemon=True)
            self.ai_thread.start()
            self.logger.info("Async AI analysis thread started")
            return True
        except Exception as e:
            self.logger.warning(f"Failed to start async AI: {e}")
            return False

    def stop(self):
        """Stop the async AI processing thread"""
        if self.ai_thread and self.ai_thread.is_alive():
            self.logger.info("Stopping async AI thread...")
            self.ai_stop_event.set()
            try:
                self.ai_queue.put_nowait((None, None, None))
            except:
                pass
            self.ai_thread.join(timeout=10)
            self.logger.info("Async AI thread stopped")

    def queue_analysis(self, job_id: int, description: str = None, pay_range: str = None):
        """Queue a job for async AI analysis"""
        if self.ai_thread and self.ai_thread.is_alive():
            try:
                self.ai_queue.put_nowait((job_id, description, pay_range))
            except queue.Full:
                self.logger.warning(f"AI queue full, skipping analysis for job {job_id}")

    def _worker(self):
        """Worker thread for async AI analysis"""
        self.logger.info("AI worker thread running...")

        while not self.ai_stop_event.is_set():
            try:
                try:
                    job_id, description, pay_range = self.ai_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if job_id is None:
                    break

                results = self._analyzer.analyze_single_job(job_id, description, pay_range)

                # Update stats
                if 'tech_stack' in results:
                    if results['tech_stack']:
                        self.stats['tech_analyzed'] += 1
                        self.logger.info(f"  [AI-Tech] Analyzed job {job_id}: {results['tech_stack']}")
                if 'tech_error' in results:
                    self.stats['tech_failed'] += 1

                if 'salary' in results:
                    if results['salary'] and (results['salary'][0] > 0 or results['salary'][1] > 0):
                        self.stats['salary_normalized'] += 1
                        self.logger.info(f"  [AI-Salary] Normalized job {job_id}: {results['salary']}")
                    else:
                        self.stats['salary_skipped'] += 1
                if 'salary_error' in results:
                    self.stats['salary_failed'] += 1

                self.ai_queue.task_done()

            except Exception as e:
                self.logger.error(f"AI worker error: {e}")

        self.logger.info("AI worker thread stopped")

    def get_stats(self) -> Dict[str, int]:
        """Get analysis statistics"""
        return self.stats.copy()
