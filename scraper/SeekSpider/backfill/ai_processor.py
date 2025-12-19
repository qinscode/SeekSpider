"""
AI processing integration for backfill module.

This module provides async AI analysis integration using the ai_analysis module.
"""

import logging
from typing import Optional, Dict

from ai_analysis import AsyncAIAnalyzer, AIAnalysisConfig, AIAnalyzer


class BackfillAIProcessor:
    """Wrapper for AI analysis in backfill context"""

    def __init__(self, config=None, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger('backfill.ai')

        # Create AI analysis config
        ai_config = AIAnalysisConfig(
            only_missing=True,  # Only analyze missing
        )

        self._async_analyzer = AsyncAIAnalyzer(ai_config, self.logger)
        self._enabled = True

    def start(self) -> bool:
        """Start the async AI processing thread"""
        if not self._enabled:
            return False
        return self._async_analyzer.start()

    def stop(self):
        """Stop the async AI processing thread"""
        self._async_analyzer.stop()

    def queue_analysis(self, job_id: int, description: str, pay_range: str = None):
        """Queue a job for async AI analysis"""
        self._async_analyzer.queue_analysis(job_id, description, pay_range)

    def get_stats(self) -> Dict[str, int]:
        """Get AI processing statistics"""
        return self._async_analyzer.get_stats()


def run_post_ai_analysis(logger: logging.Logger, region_filter: str = None):
    """Run AI analysis after backfill completes (post-processing)"""
    logger.info("=" * 50)
    logger.info("STARTING AI ANALYSIS (POST-PROCESSING)")
    logger.info("=" * 50)

    try:
        config = AIAnalysisConfig(
            region_filter=region_filter,
            only_missing=True,
        )

        analyzer = AIAnalyzer(config, logger)
        analyzer.run()

    except Exception as e:
        logger.error(f"AI Analysis failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
