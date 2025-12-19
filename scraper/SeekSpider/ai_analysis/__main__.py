#!/usr/bin/env python3
"""
CLI entry point for AI Analysis module.

Usage:
    python -m ai_analysis --type all
    python -m ai_analysis --type tech_stack --region Sydney --limit 100
    python -m ai_analysis --type salary --region Melbourne
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

from .config import AIAnalysisConfig, AnalysisType
from .core import AIAnalyzer


def setup_logging(region: str = None):
    """Setup logging to both console and file"""
    output_manager = OutputManager('ai_analysis_logs', region=region)
    output_dir = output_manager.setup()

    timestamp = output_manager.timestamp
    log_file = output_manager.get_file_path(f'ai_analysis_{timestamp}.log')

    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    logger = logging.getLogger('ai_analysis')
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

    return logger


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='AI Analysis for job data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
    python -m ai_analysis --type all
    python -m ai_analysis --type tech_stack --region Sydney --limit 100
    python -m ai_analysis --type salary --region Melbourne
        '''
    )

    parser.add_argument('--type', type=str, default='all',
                        choices=['all', 'tech_stack', 'salary'],
                        help='Type of analysis to run (default: all)')
    parser.add_argument('--region', type=str, default=None,
                        help='Region for output organization (e.g., Sydney, Perth)')
    parser.add_argument('--region-filter', type=str, default=None,
                        help='Filter jobs by region')
    parser.add_argument('--limit', type=int, default=None,
                        help='Maximum number of jobs to process')
    parser.add_argument('--include-existing', action='store_true',
                        help='Re-analyze jobs that already have analysis')

    return parser.parse_args()


def main():
    """Main entry point"""
    args = parse_args()

    # Setup logging
    logger = setup_logging(region=args.region)

    # Parse analysis type
    if args.type == 'all':
        analysis_types = [AnalysisType.ALL]
    elif args.type == 'tech_stack':
        analysis_types = [AnalysisType.TECH_STACK]
    elif args.type == 'salary':
        analysis_types = [AnalysisType.SALARY]
    else:
        analysis_types = [AnalysisType.ALL]

    # Create configuration
    config = AIAnalysisConfig(
        analysis_types=analysis_types,
        limit=args.limit,
        region_filter=args.region_filter,
        region=args.region,
        only_missing=not args.include_existing,
    )

    logger.info(f"Arguments: type={args.type}, region={args.region}, "
                f"region_filter={args.region_filter}, limit={args.limit}, "
                f"include_existing={args.include_existing}")

    # Run analysis
    analyzer = AIAnalyzer(config, logger)
    analyzer.run()


if __name__ == '__main__':
    main()
