#!/usr/bin/env python3
"""
Backfill missing job descriptions from Seek job pages.

This script fetches job descriptions for records where JobDescription is empty,
starting from the most recent jobs.

Usage:
    python backfill_job_descriptions.py [--limit 100] [--delay 3]
"""

import argparse
import os
import random
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.config import config
from core.database import DatabaseManager


class JobDescriptionBackfiller:
    """Backfill missing job descriptions"""

    def __init__(self, delay: float = 3.0):
        self.delay = delay
        self.db = DatabaseManager(config)
        self.session = requests.Session()

        # Browser-like headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-AU,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        }

        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'cloudflare_blocked': 0,
        }

    def get_jobs_without_description(self, limit: int = 100) -> list:
        """Get jobs where JobDescription is empty, ordered by most recent"""
        query = f'''
            SELECT "Id", "Url", "JobTitle"
            FROM "{config.POSTGRESQL_TABLE}"
            WHERE ("JobDescription" IS NULL OR "JobDescription" = '' OR "JobDescription" = 'None')
            AND "IsActive" = TRUE
            ORDER BY "CreatedAt" DESC
            LIMIT {limit}
        '''

        try:
            return self.db.execute_query(query)
        except Exception as e:
            print(f"Error fetching jobs: {e}")
            return []

    def fetch_job_description(self, url: str) -> tuple:
        """
        Fetch job description from URL.
        Returns (description, suburb) or (None, None) if failed.
        """
        try:
            response = self.session.get(url, headers=self.headers, timeout=30)

            # Check for Cloudflare challenge
            if 'challenge' in response.text.lower() or response.status_code == 403:
                return None, None, 'cloudflare'

            if response.status_code != 200:
                return None, None, f'status_{response.status_code}'

            soup = BeautifulSoup(response.text, 'lxml')

            # Extract job description - try multiple selectors
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

        except requests.exceptions.Timeout:
            return None, None, 'timeout'
        except Exception as e:
            return None, None, str(e)

    def update_job(self, job_id: int, description: str, suburb: str = None):
        """Update job description in database"""
        try:
            job_data = {'JobDescription': description}
            if suburb:
                job_data['Suburb'] = suburb

            self.db.update_job(job_id, job_data)
            return True
        except Exception as e:
            print(f"Error updating job {job_id}: {e}")
            return False

    def run(self, limit: int = 100):
        """Run the backfill process"""
        print(f"[{datetime.now()}] Starting job description backfill...")
        print(f"Fetching up to {limit} jobs without descriptions...")

        jobs = self.get_jobs_without_description(limit)
        self.stats['total'] = len(jobs)

        print(f"Found {len(jobs)} jobs to process\n")

        if not jobs:
            print("No jobs to process.")
            return

        for i, (job_id, url, title) in enumerate(jobs, 1):
            print(f"[{i}/{len(jobs)}] Processing job {job_id}: {title[:50]}...")

            description, suburb, status = self.fetch_job_description(url)

            if status == 'cloudflare':
                print(f"  ⚠️  Cloudflare blocked - skipping")
                self.stats['cloudflare_blocked'] += 1
                # Increase delay when blocked
                time.sleep(self.delay * 2)
                continue

            if status == 'success' and description:
                if self.update_job(job_id, description, suburb):
                    print(f"  ✓ Updated successfully")
                    self.stats['success'] += 1
                else:
                    print(f"  ✗ Database update failed")
                    self.stats['failed'] += 1
            else:
                print(f"  ✗ Failed: {status}")
                self.stats['failed'] += 1

            # Random delay to avoid rate limiting
            delay = self.delay + random.uniform(0, 2)
            time.sleep(delay)

        self._print_summary()

    def _print_summary(self):
        """Print summary of the backfill process"""
        print("\n" + "=" * 50)
        print("BACKFILL SUMMARY")
        print("=" * 50)
        print(f"Total jobs processed: {self.stats['total']}")
        print(f"Successfully updated: {self.stats['success']}")
        print(f"Failed: {self.stats['failed']}")
        print(f"Cloudflare blocked: {self.stats['cloudflare_blocked']}")
        print(f"Success rate: {self.stats['success']/max(self.stats['total'],1)*100:.1f}%")
        print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description='Backfill missing job descriptions')
    parser.add_argument('--limit', type=int, default=100,
                        help='Maximum number of jobs to process (default: 100)')
    parser.add_argument('--delay', type=float, default=3.0,
                        help='Base delay between requests in seconds (default: 3.0)')

    args = parser.parse_args()

    backfiller = JobDescriptionBackfiller(delay=args.delay)
    backfiller.run(limit=args.limit)


if __name__ == '__main__':
    main()
