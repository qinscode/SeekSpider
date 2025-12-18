from urllib.parse import urlencode
import logging

import requests
import scrapy
from bs4 import BeautifulSoup
from scrapy import Request
from scrapy.exceptions import CloseSpider

from SeekSpider.core.ai_client import AIClient
from SeekSpider.core.config import config
from SeekSpider.core.database import DatabaseManager
from SeekSpider.core.output_manager import OutputManager
from SeekSpider.core.regions import AUSTRALIAN_REGIONS, DEFAULT_REGION, get_seek_location, is_valid_region
from SeekSpider.items import SeekspiderItem
from SeekSpider.scripts.backfill_job_descriptions import JobDescriptionBackfiller
from SeekSpider.utils.salary_normalizer import SalaryNormalizer
from SeekSpider.utils.tech_frequency_analyzer import TechStatsAnalyzer
from SeekSpider.utils.tech_stack_analyzer import TechStackAnalyzer


class SeekSpider(scrapy.Spider):
    name = "seek"
    allowed_domains = ["www.seek.com.au"]
    base_url = "https://www.seek.com.au/api/jobsearch/v5/search"
    jd_url = "https://www.seek.com.au/job/"
    remove_text = '(Information & Communication Technology)'

    def __init__(self, location=None, classification=None, region=None, limit=None, *args, **kwargs):
        super(SeekSpider, self).__init__(*args, **kwargs)

        # Initialize core components
        self.db = DatabaseManager(config)
        self.db.set_logger(self.logger)
        self.ai_client = AIClient(config)

        # Initialize scraped job IDs set
        self.scraped_job_ids = set()

        # Item limit for testing (None = unlimited)
        self.item_limit = int(limit) if limit else None
        self.items_scraped = 0

        # Handle region parameter
        if region:
            if is_valid_region(region):
                self.region = region
                self.location = get_seek_location(region)
            else:
                self.logger.warning(f"Invalid region '{region}', using default: {DEFAULT_REGION}")
                self.logger.info(f"Available regions: {list(AUSTRALIAN_REGIONS.keys())}")
                self.region = DEFAULT_REGION
                self.location = get_seek_location(DEFAULT_REGION)
        elif location:
            # If location is provided but not region, try to infer region from location
            self.location = location
            # Try to find matching region
            self.region = DEFAULT_REGION
            for reg, loc in AUSTRALIAN_REGIONS.items():
                if loc == location:
                    self.region = reg
                    break
        else:
            # Default to Perth
            self.region = DEFAULT_REGION
            self.location = get_seek_location(DEFAULT_REGION)

        self.classification = classification or '6281'

        # Initialize search parameters
        self.search_params = {
            'siteKey': 'AU-Main',
            'sourcesystem': 'houston',
            'where': self.location,
            'page': 1,
            'seekSelectAllPages': 'true',
            'classification': self.classification,
            'subclassification': '',
            'include': 'seodata',
            'locale': 'en-AU',
        }

        self.logger.info(f"Spider initialized - Region: {self.region}, Location: {self.location}, Classification: {self.classification}")

        # Initialize headers
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                          'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                          'Version/17.4.1 Safari/605.1.15',
        }

        # Job categories mapping
        self.job_categories = {
            '6282': 'Architects',
            '6283': 'Business/Systems Analysts',
            '6284': 'Computer Operators',
            '6285': 'Consultants',
            '6286': 'Database Development & Administration',
            '6287': 'Developers/Programmers',
            '6288': 'Engineering - Hardware',
            '6289': 'Engineering - Network',
            '6290': 'Engineering - Software',
            '6291': 'Help Desk & IT Support',
            '6292': 'Management',
            '6293': 'Networks & Systems Administration',
            '6294': 'Product Management & Development',
            '6295': 'Programme & Project Management',
            '6296': 'Sales - Pre & Post',
            '6297': 'Security',
            '6298': 'Team Leaders',
            '6299': 'Technical Writing',
            '6300': 'Telecommunications',
            '6301': 'Testing & Quality Assurance',
            '6302': 'Web Development & Production',
            '6303': 'Other'
        }

    def start_requests(self):
        """Start the crawling process"""
        # Get first category
        self.current_category, _ = self.job_categories.popitem()
        self.search_params['subclassification'] = self.current_category

        self.logger.info(f'Starting category: {self.current_category}')
        yield self.make_requests_from_url(self.base_url)

    def make_requests_from_url(self, url):
        """Create request with current parameters"""
        query_string = urlencode(self.search_params)
        url = f"{url}?{query_string}"

        self.logger.info("Starting search request")
        return Request(url, headers=self.headers, dont_filter=True)

    def parse(self, response):
        """Parse search results page"""
        raw_data = response.json()

        # Get pagination info
        items_per_page = raw_data.get('solMetadata', {}).get('pageSize', 20)
        total_count = raw_data.get('totalCount', 0)
        total_pages = (total_count + items_per_page - 1) // items_per_page

        self.logger.info(
            f'Total: {total_count}, Per Page: {items_per_page}, Pages: {total_pages}'
        )

        # Process job listings
        for data in raw_data['data']:
            yield self.parse_job(data)

        # Handle pagination
        if self.search_params['page'] < total_pages:
            yield from self._handle_next_page()
        else:
            yield from self._handle_next_category()

    def _handle_next_page(self):
        """Handle pagination within current category"""
        self.search_params['page'] += 1
        next_page = self.make_requests_from_url(self.base_url)
        self.logger.info(f'Next Page: {self.search_params["page"]}')
        yield next_page

    def _handle_next_category(self):
        """Handle moving to next category"""
        if self.job_categories:
            self.current_category, category_name = self.job_categories.popitem()
            self.search_params['subclassification'] = self.current_category
            self.search_params['page'] = 1

            # 构建完整URL用于日志
            query_string = urlencode(self.search_params)
            next_url = f"{self.base_url}?{query_string}"

            self.logger.info(f'Next Subclass: {self.current_category} ({category_name}), URL: {next_url}')
            yield self.make_requests_from_url(self.base_url)
        else:
            self.logger.info('No more categories to scrape')
            raise CloseSpider('Finished scraping all categories')

    def parse_job(self, data):
        """Parse individual job listing and request detail page"""
        item = SeekspiderItem()

        # Basic job info
        if data.get('classifications') and len(data['classifications']) > 0:
            item['job_type'] = data['classifications'][0].get('subclassification', '').get('description', '')

        item['job_id'] = str(data['id'])
        self.scraped_job_ids.add(item['job_id'])
        item['url'] = self.jd_url + str(data['id'])
        item['job_title'] = data.get('title', '')
        item['posted_date'] = data.get('listingDate', '')
        item['region'] = self.region  # Set region from spider configuration

        # Location info
        if data.get('locations') and len(data['locations']) > 0:
            item['area'] = data['locations'][0].get('label', '')

        # Advertiser info
        if 'advertiser' in data:
            item['advertiser_id'] = data['advertiser'].get('id', '')
            item['business_name'] = data['advertiser'].get('description', '')

        # Work type
        if data.get('workTypes') and len(data['workTypes']) > 0:
            item['work_type'] = data['workTypes'][0]

        # Salary info
        item['pay_range'] = data.get('salaryLabel', '')

        # Job description will be fetched from detail page
        # Don't use teaser - if we can't get full JD, store empty
        item['job_description'] = ''

        # Request detail page to get full job description
        # Allow 403 responses to be processed (Cloudflare blocking)
        return Request(
            url=item['url'],
            callback=self.parse_job_detail,
            meta={'item': item, 'handle_httpstatus_list': [403]},
            headers=self.headers,
            dont_filter=True
        )

    def parse_job_detail(self, response):
        """Parse job detail page to get full description"""
        item = response.meta['item']

        # Check item limit
        if self.item_limit and self.items_scraped >= self.item_limit:
            self.logger.info(f"Item limit ({self.item_limit}) reached, closing spider")
            raise CloseSpider(f'Item limit ({self.item_limit}) reached')

        try:
            soup = BeautifulSoup(response.text, 'lxml')

            # Check if we got blocked by Cloudflare
            if 'challenge' in response.text.lower() or response.status == 403:
                self.logger.warning(f"Cloudflare challenge for job {item['job_id']}, JD will be empty")
                self.items_scraped += 1
                return item

            # Extract location
            location = soup.find("span", attrs={"data-automation": "job-detail-location"})
            if location:
                item['suburb'] = location.text

            # Extract work type
            work_type = soup.find("span", attrs={"data-automation": "job-detail-work-type"})
            if work_type and not item.get('work_type'):
                item['work_type'] = work_type.text

            # Extract job type
            job_type = soup.find("span", attrs={"data-automation": "job-detail-classifications"})
            if job_type and not item.get('job_type'):
                item['job_type'] = job_type.text

            # Extract salary
            salary = soup.find("span", attrs={"data-automation": "job-detail-salary"})
            if salary and not item.get('pay_range'):
                item['pay_range'] = salary.text

            # Extract job description - try multiple selectors
            job_details = soup.find("div", attrs={"data-automation": "jobAdDetails"})
            if not job_details:
                job_details = soup.find("div", attrs={"data-automation": "jobDescription"})
            if not job_details:
                # Try finding by class pattern
                job_details = soup.find("div", class_=lambda x: x and 'jobDescription' in str(x).lower())

            if job_details:
                item['job_description'] = str(job_details)
            else:
                self.logger.warning(f"Could not find job description for {item['job_id']}")

        except Exception as e:
            self.logger.error(f"Error parsing job detail {item['job_id']}: {str(e)}")

        self.items_scraped += 1
        return item

    def closed(self, reason):
        """Handle spider closing"""
        self.logger.info(f"Spider closing: {reason}")

        # Store scraped job IDs for later use
        self.crawler.stats.set_value('scraped_job_ids', self.scraped_job_ids)

        # Run post-processing
        try:
            self._run_post_processing()
        except Exception as e:
            self.logger.error(f"Post-processing error: {str(e)}")

    def _run_post_processing(self):
        """Run post-scraping analysis"""
        self.logger.info("Starting post-processing...")

        # Step 1: Backfill missing job descriptions
        self.logger.info("Step 1: Running job description backfill...")
        try:
            # Create output files for backfill logging
            output_manager = OutputManager('backfill_logs', region=self.region)
            output_dir = output_manager.setup()
            csv_file = output_manager.get_file_path(f'backfill_{output_manager.timestamp}.csv')
            log_file = output_manager.get_file_path(f'backfill_{output_manager.timestamp}.log')

            # Create a separate logger for backfill that writes to both spider log and backfill log
            backfill_logger = logging.getLogger('backfill')
            backfill_logger.setLevel(logging.INFO)
            backfill_logger.handlers.clear()

            # Add file handler for backfill log
            backfill_file_handler = logging.FileHandler(log_file, encoding='utf-8')
            backfill_file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S'
            ))
            backfill_logger.addHandler(backfill_file_handler)

            # Also propagate to spider logger
            backfill_logger.propagate = False
            backfill_logger.addHandler(logging.StreamHandler())

            backfiller = JobDescriptionBackfiller(
                delay=5.0,
                logger=backfill_logger,
                headless=False,  # Use visible browser for better Cloudflare bypass
                use_xvfb=False,
                csv_file=csv_file
            )
            backfiller.run(limit=None)  # Process all jobs without description
            self.logger.info(f"Backfill completed: {backfiller.stats['success']} jobs updated")
            self.logger.info(f"Backfill CSV: {csv_file}")
            self.logger.info(f"Backfill log: {log_file}")

            # Close backfill log handler
            backfill_file_handler.close()
            backfill_logger.removeHandler(backfill_file_handler)
        except Exception as e:
            self.logger.error(f"Backfill error: {str(e)}")

        # Step 2: Initialize analyzers
        self.logger.info("Step 2: Running AI analysis...")
        tech_analyzer = TechStackAnalyzer(self.db, self.ai_client, self.logger)
        salary_normalizer = SalaryNormalizer(self.db, self.ai_client, self.logger)
        stats_analyzer = TechStatsAnalyzer(self.db, self.logger)

        # Run analysis
        tech_analyzer.process_all_jobs()
        salary_normalizer.process_all_jobs()
        stats_analyzer.process_all_jobs()

        self.logger.info("Post-processing complete")
