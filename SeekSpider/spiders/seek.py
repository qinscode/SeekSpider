from urllib.parse import urlencode

import requests
import scrapy
from bs4 import BeautifulSoup
from scrapy import Request
from scrapy.exceptions import CloseSpider

from SeekSpider.core.ai_client import AIClient
from SeekSpider.core.config import config
from SeekSpider.core.database import DatabaseManager
from SeekSpider.items import SeekspiderItem
from SeekSpider.utils.get_token import get_auth_token
from SeekSpider.utils.salary_normalizer import SalaryNormalizer
from SeekSpider.utils.tech_stack_analyzer import TechStackAnalyzer
from SeekSpider.utils.tech_stats_analyzer import TechStatsAnalyzer


class SeekSpider(scrapy.Spider):
    name = "seek"
    allowed_domains = ["www.seek.com.au"]
    base_url = "https://www.seek.com.au/api/jobsearch/v5/me/search"
    jd_url = "https://www.seek.com.au/job/"
    remove_text = '(Information & Communication Technology)'

    def __init__(self, *args, **kwargs):
        super(SeekSpider, self).__init__(*args, **kwargs)

        # Initialize core components
        self.db = DatabaseManager(config)
        self.db.set_logger(self.logger)
        self.ai_client = AIClient(config)

        # Initialize scraped job IDs set
        self.scraped_job_ids = set()

        # Initialize search parameters
        self.search_params = {
            'siteKey': 'AU-Main',
            'sourcesystem': 'houston',
            'where': 'All Perth WA',
            'page': 1,
            'seekSelectAllPages': 'true',
            'classification': '6281',
            'subclassification': '',
            'include': 'seodata',
            'locale': 'en-AU',
        }

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

        # Get authentication token
        self._setup_auth()

    def _setup_auth(self):
        """Setup authentication token"""
        self.logger.info("Getting authorization token...")
        auth_token = get_auth_token(config.SEEK_USERNAME, config.SEEK_PASSWORD)

        if not auth_token:
            raise Exception("Failed to get authorization token")

        self.headers['Authorization'] = auth_token
        self.logger.info("Successfully obtained authorization token")

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
        """Parse individual job listing"""
        item = SeekspiderItem()

        # Basic job info
        item['job_id'] = data['id']
        self.scraped_job_ids.add(item['job_id'])
        item['url'] = self.jd_url + str(data['id'])
        item['job_title'] = data.get('title', '')
        item['posted_date'] = data.get('listingDate', '')

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

        # Get detailed job info
        self._enrich_job_details(item)

        return item

    def _enrich_job_details(self, item):
        """Get additional job details from job page"""
        try:
            response = requests.get(item['url'], headers=self.headers)
            soup = BeautifulSoup(response.text, 'lxml')

            # Extract location
            location = soup.find("span", attrs={"data-automation": "job-detail-location"})
            item['suburb'] = location.text if location else None

            # Extract job type
            job_type = soup.find("span", attrs={"data-automation": "job-detail-work-type"})
            if job_type and not item.get('work_type'):
                item['work_type'] = job_type.text

            # Extract salary
            salary = soup.find("span", attrs={"data-automation": "job-detail-salary"})
            if salary and not item.get('pay_range'):
                item['pay_range'] = salary.text

            # Extract job description
            job_details = soup.find("div", attrs={"data-automation": "jobAdDetails"})
            item['job_description'] = str(job_details) if job_details else None

        except Exception as e:
            self.logger.error(f"Error enriching job {item['job_id']}: {str(e)}")

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

        # Initialize analyzers
        tech_analyzer = TechStackAnalyzer(self.db, self.ai_client, self.logger)
        salary_normalizer = SalaryNormalizer(self.db, self.ai_client, self.logger)
        stats_analyzer = TechStatsAnalyzer(self.db, self.logger)

        # Run analysis
        tech_analyzer.process_all_jobs()
        salary_normalizer.process_all_jobs()
        stats_analyzer.process_all_jobs()

        self.logger.info("Post-processing complete")
