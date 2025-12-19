#!/usr/bin/env python3
"""
CLI entry point for backfill module.

Usage:
    python -m backfill --region Sydney --limit 100
    python -m backfill --region-filter Melbourne --workers 3
"""

import argparse
import logging
import os
import sys

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env from project root
from dotenv import load_dotenv
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

from core.output_manager import OutputManager

from .config import BackfillConfig
from .core import JobDescriptionBackfiller
from .ai_processor import run_post_ai_analysis


def setup_logging(region: str = None):
    """Setup logging to both console and file, and create CSV log file"""
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


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Backfill missing job descriptions from Seek',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python -m backfill --region Sydney --limit 100
    python -m backfill --region-filter Melbourne --workers 3
    python -m backfill --headless --workers 1
        '''
    )

    # Processing options
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum number of jobs to process (default: no limit)')
    parser.add_argument('--delay', type=float, default=5.0,
                        help='Base delay between requests in seconds (default: 5.0)')
    parser.add_argument('--workers', type=int, default=3,
                        help='Number of concurrent workers (1-5, default: 3)')

    # Browser options
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode (default: False)')
    parser.add_argument('--no-xvfb', action='store_true',
                        help='Disable virtual display (Xvfb). By default Xvfb is enabled.')

    # Region options
    parser.add_argument('--region', type=str, default=None,
                        help='Region for output organization (e.g., Sydney, Perth)')
    parser.add_argument('--region-filter', type=str, default=None,
                        help='Filter jobs by region. If not specified, processes all regions.')

    # AI options
    parser.add_argument('--skip-ai', action='store_true',
                        help='Skip AI analysis after backfill (post-processing)')
    parser.add_argument('--no-async-ai', action='store_true',
                        help='Disable async AI analysis during scraping')

    # Other options
    parser.add_argument('--include-inactive', action='store_true',
                        help='Include inactive jobs in backfill')
    parser.add_argument('--restart-interval', type=int, default=30,
                        help='Restart Chrome driver every N jobs (default: 30, serial mode only)')

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Setup logging
    logger, csv_file = setup_logging(region=args.region)

    # Create configuration
    config = BackfillConfig(
        delay=args.delay,
        workers=args.workers,
        limit=args.limit,
        headless=args.headless,
        use_xvfb=not args.no_xvfb,
        region_filter=args.region_filter,
        region=args.region,
        include_inactive=args.include_inactive,
        enable_async_ai=not args.no_async_ai,
        skip_ai_post=args.skip_ai,
        restart_interval=args.restart_interval,
    )

    logger.info(f"Arguments: limit={args.limit}, delay={args.delay}, headless={args.headless}, "
                f"xvfb={not args.no_xvfb}, skip_ai={args.skip_ai}, no_async_ai={args.no_async_ai}, "
                f"include_inactive={args.include_inactive}, region={args.region}, "
                f"region_filter={args.region_filter}, restart_interval={args.restart_interval}, "
                f"workers={args.workers}")

    # Create and run backfiller
    backfiller = JobDescriptionBackfiller(config, logger)
    backfiller.set_csv_file(csv_file)
    backfiller.run(limit=args.limit)

    # Run post AI analysis if needed
    stats = backfiller.get_stats()
    if not args.skip_ai and stats['success'] > 0:
        run_post_ai_analysis(logger)
    elif args.skip_ai:
        logger.info("AI analysis skipped (--skip-ai flag)")
    else:
        logger.info("AI analysis skipped (no successful backfills)")


if __name__ == '__main__':
    main()
