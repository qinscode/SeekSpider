#!/usr/bin/env python3
"""
Spider Smoke Test

Quick functional test to verify the spider can run and scrape data.
This test performs actual requests to Seek.com.au (limited scope).

Usage:
    python tests/test_spider_smoke.py
    python tests/test_spider_smoke.py --region Perth --limit 5
    python tests/test_spider_smoke.py --spider-only
    python tests/test_spider_smoke.py --backfill-only
    python tests/test_spider_smoke.py --ai-only
"""

import os
import sys
import argparse
import subprocess
from datetime import datetime

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPER_DIR = os.path.join(PROJECT_ROOT, 'scraper')

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


def run_spider_test(region: str = 'Perth', limit: int = 5, dry_run: bool = False) -> int:
    """
    Run a quick spider test

    Args:
        region: Region to scrape
        limit: Maximum number of jobs to scrape
        dry_run: If True, just check spider can start

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print("=" * 70)
    print("SPIDER SMOKE TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: {region}")
    print(f"Limit: {limit}")
    print(f"Dry run: {dry_run}")
    print("=" * 70)

    # Set up environment
    env = os.environ.copy()
    env['PYTHONPATH'] = f"{PROJECT_ROOT}:{SCRAPER_DIR}:{env.get('PYTHONPATH', '')}"
    env['SCRAPY_SETTINGS_MODULE'] = 'SeekSpider.settings'

    # Build command
    cmd = [
        sys.executable, '-m', 'scrapy', 'crawl', 'seek',
        '-a', f'region={region}',
        '-a', 'classification=6281',
        '-s', f'CLOSESPIDER_ITEMCOUNT={limit}',
        '-s', 'LOG_LEVEL=INFO',
        '-s', 'CONCURRENT_REQUESTS=4',
        '-s', 'DOWNLOAD_DELAY=1.0',
    ]

    if dry_run:
        # For dry run, just check spider starts
        cmd.extend(['-s', 'CLOSESPIDER_TIMEOUT=10'])

    print(f"\nCommand: {' '.join(cmd)}")
    print(f"Working directory: {SCRAPER_DIR}")
    print("\n" + "-" * 70)
    print("SPIDER OUTPUT:")
    print("-" * 70 + "\n")

    try:
        result = subprocess.run(
            cmd,
            cwd=SCRAPER_DIR,
            env=env,
            timeout=300,  # 5 minute timeout
        )

        print("\n" + "-" * 70)

        if result.returncode == 0:
            print("\nSPIDER TEST: PASSED")
            return 0
        else:
            print(f"\nSPIDER TEST: FAILED (exit code: {result.returncode})")
            return result.returncode

    except subprocess.TimeoutExpired:
        print("\nSPIDER TEST: TIMEOUT (5 minutes)")
        return 1
    except Exception as e:
        print(f"\nSPIDER TEST: ERROR - {e}")
        return 1


def run_backfill_test(region: str = 'Perth', limit: int = 3) -> int:
    """
    Run a quick backfill test

    Args:
        region: Region to backfill
        limit: Maximum number of jobs to backfill

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print("\n" + "=" * 70)
    print("BACKFILL SMOKE TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: {region}")
    print(f"Limit: {limit}")
    print("=" * 70)

    # Set up environment
    env = os.environ.copy()
    seekspider_dir = os.path.join(SCRAPER_DIR, 'SeekSpider')
    env['PYTHONPATH'] = f"{PROJECT_ROOT}:{SCRAPER_DIR}:{env.get('PYTHONPATH', '')}"

    # Build command
    cmd = [
        sys.executable, '-m', 'backfill',
        '--region', region,
        '--region-filter', region,
        '--limit', str(limit),
        '--workers', '1',
        '--delay', '3.0',
        '--headless',  # Use headless for testing
        '--skip-ai',  # Skip AI analysis in test
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print(f"Working directory: {seekspider_dir}")
    print("\n" + "-" * 70)
    print("BACKFILL OUTPUT:")
    print("-" * 70 + "\n")

    try:
        result = subprocess.run(
            cmd,
            cwd=seekspider_dir,
            env=env,
            timeout=180,  # 3 minute timeout
        )

        print("\n" + "-" * 70)

        if result.returncode == 0:
            print("\nBACKFILL TEST: PASSED")
            return 0
        else:
            print(f"\nBACKFILL TEST: FAILED (exit code: {result.returncode})")
            return result.returncode

    except subprocess.TimeoutExpired:
        print("\nBACKFILL TEST: TIMEOUT (3 minutes)")
        return 1
    except Exception as e:
        print(f"\nBACKFILL TEST: ERROR - {e}")
        return 1


def run_ai_analysis_test(region: str = 'Perth', limit: int = 5) -> int:
    """
    Run a quick AI analysis test

    Args:
        region: Region to analyze
        limit: Maximum number of jobs to analyze

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    print("\n" + "=" * 70)
    print("AI ANALYSIS SMOKE TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Region: {region}")
    print(f"Limit: {limit}")
    print("=" * 70)

    # Check if AI config is available
    ai_api_key = os.getenv('AI_API_KEY') or os.getenv('AI_API_KEYS')
    if not ai_api_key:
        print("\nAI ANALYSIS TEST: SKIPPED (No AI_API_KEY configured)")
        return 0

    # Set up environment
    env = os.environ.copy()
    seekspider_dir = os.path.join(SCRAPER_DIR, 'SeekSpider')
    env['PYTHONPATH'] = f"{PROJECT_ROOT}:{SCRAPER_DIR}:{env.get('PYTHONPATH', '')}"

    # Build command
    cmd = [
        sys.executable, '-m', 'ai_analysis',
        '--type', 'all',
        '--region', region,
        '--region-filter', region,
        '--limit', str(limit),
    ]

    print(f"\nCommand: {' '.join(cmd)}")
    print(f"Working directory: {seekspider_dir}")
    print("\n" + "-" * 70)
    print("AI ANALYSIS OUTPUT:")
    print("-" * 70 + "\n")

    try:
        result = subprocess.run(
            cmd,
            cwd=seekspider_dir,
            env=env,
            timeout=120,  # 2 minute timeout
        )

        print("\n" + "-" * 70)

        if result.returncode == 0:
            print("\nAI ANALYSIS TEST: PASSED")
            return 0
        else:
            print(f"\nAI ANALYSIS TEST: FAILED (exit code: {result.returncode})")
            return result.returncode

    except subprocess.TimeoutExpired:
        print("\nAI ANALYSIS TEST: TIMEOUT (2 minutes)")
        return 1
    except Exception as e:
        print(f"\nAI ANALYSIS TEST: ERROR - {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description='Spider Smoke Test')
    parser.add_argument('--region', default='Perth', help='Region to test')
    parser.add_argument('--limit', type=int, default=5, help='Max items to process')
    parser.add_argument('--spider-only', action='store_true', help='Only test spider')
    parser.add_argument('--backfill-only', action='store_true', help='Only test backfill')
    parser.add_argument('--ai-only', action='store_true', help='Only test AI analysis')
    parser.add_argument('--dry-run', action='store_true', help='Quick check only')

    args = parser.parse_args()

    exit_code = 0

    if args.spider_only:
        exit_code = run_spider_test(args.region, args.limit, args.dry_run)
    elif args.backfill_only:
        exit_code = run_backfill_test(args.region, args.limit)
    elif args.ai_only:
        exit_code = run_ai_analysis_test(args.region, args.limit)
    else:
        # Run all tests
        spider_result = run_spider_test(args.region, args.limit, args.dry_run)
        if spider_result != 0:
            exit_code = spider_result

        backfill_result = run_backfill_test(args.region, min(args.limit, 3))
        if backfill_result != 0:
            exit_code = backfill_result

        ai_result = run_ai_analysis_test(args.region, min(args.limit, 5))
        if ai_result != 0:
            exit_code = ai_result

    print("\n" + "=" * 70)
    if exit_code == 0:
        print("ALL SMOKE TESTS PASSED!")
    else:
        print("SOME SMOKE TESTS FAILED!")
    print("=" * 70)

    return exit_code


if __name__ == '__main__':
    sys.exit(main())
