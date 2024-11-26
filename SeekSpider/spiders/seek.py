import scrapy
from scrapy import Request
from urllib.parse import urlencode
from scrapy.exceptions import CloseSpider
from SeekSpider.items import SeekspiderItem
from bs4 import BeautifulSoup
import requests
from SeekSpider.settings_local import AUTHORIZATION

class SeekSpider(scrapy.Spider):
    name = "seek"
    allowed_domains = ["www.seek.com.au"]
    params = {
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
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                      'AppleWebKit/605.1.15 (KHTML, like Gecko) '
                      'Version/17.4.1 Safari/605.1.15',
        'Authorization': AUTHORIZATION
    }
    base_url = "https://www.seek.com.au/api/jobsearch/v5/me/search"
    jd_url = "https://www.seek.com.au/job/"
    remove_text = '(Information & Communication Technology)'

    subclassification_dict = {
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

    current_subclass = ''

    # Use Scrapy's logging system instead of printing to console
    custom_settings = {
        'LOG_LEVEL': 'INFO',
    }

    def __init__(self, *args, **kwargs):
        super(SeekSpider, self).__init__(*args, **kwargs)
        self.scraped_job_ids = set()

    def start_requests(self):
        self.current_subclass,_ = self.subclassification_dict.popitem()
        self.params['subclassification'] = self.current_subclass
        self.logger.info(f'Starting subclass: {self.current_subclass}')
        yield self.make_requests_from_url(self.base_url)

    def make_requests_from_url(self, url):
        query_string = urlencode(self.params)
        url = f"{url}?{query_string}"
        self.logger.info("Starting search request.")
        return Request(url, headers=self.headers, dont_filter=True, callback=self.parse)

    def parse(self, response):
        raw_data = response.json()
        
        # Get items_per_page from solMetadata.pageSize
        items_per_page = raw_data.get('solMetadata', {}).get('pageSize', 20)  # Default to 20 if not found
        total_count = raw_data.get('totalCount', 0)
        total_pages = (total_count + items_per_page - 1) // items_per_page  # Round up division
        
        self.logger.info(f'Total Count: {total_count}, Items Per Page: {items_per_page}, Total Pages: {total_pages}')

        for data in raw_data['data']:
            yield self.parse_job(data)

        # if there are more pages to scrape, keep going with current subclass
        if self.params['page'] < total_pages:
            self.params['page'] += 1
            next_page = self.get_next_page_url()
            self.logger.info(f'Next Page: {self.params["page"]}, URL: {next_page}')
            yield Request(next_page, headers=self.headers, dont_filter=True, callback=self.parse)

        # if there are no more pages to scrape, move to the next subclass or close
        else:
            # subclassification_dict is not empty, move to the next subclass
            if bool(self.subclassification_dict):
                self.current_subclass, _ = self.subclassification_dict.popitem()
                self.params['subclassification'] = self.current_subclass
                self.params['page'] = 1
                next_page = self.get_next_page_url()
                self.logger.info(f'Next Subclass: {self.current_subclass}, URL: {next_page}')
                yield Request(next_page, headers=self.headers, dont_filter=True, callback=self.parse)
                pass

            # if there are no more pages to scrape and no more subclasses, stop the spider
            else:
                self.logger.info('No more subclasses to scrape.')
                raise CloseSpider('Reached last page of results')

    def get_next_page_url(self):
        query_string = urlencode(self.params)
        return f"{self.base_url}?{query_string}"

    def parse_job(self, data):
        item = SeekspiderItem()
        item['job_id'] = data['id']
        self.scraped_job_ids.add(item['job_id'])

        x = data.get('locations')
        y = len(data['locations'])
        # Get location from the first location in locations array
        if data.get('locations') and len(data['locations']) > 0:
            item['area'] = data['locations'][0].get('label', '')
        else:
            item['area'] = ''
        
        item['url'] = self.jd_url + str(data['id'])
        
        # Get advertiser info
        if 'advertiser' in data:
            item['advertiser_id'] = data['advertiser'].get('id', '')
            item['business_name'] = data['advertiser'].get('description', '')
        
        item['job_title'] = data.get('title', '')
        item['posted_date'] = data.get('listingDate', '')
        
        # Get work type from workTypes array
        if data.get('workTypes') and len(data['workTypes']) > 0:
            item['work_type'] = data['workTypes'][0]
        else:
            item['work_type'] = ''
        
        # Get salary information
        item['pay_range'] = data.get('salaryLabel', '')
        
        # Get job description and other details from the job page
        suburb, job_type, work_type, pay_range, content = self.fetch_job_description(item['url'])
        item['suburb'] = suburb
        item['job_type'] = job_type
        # Only use work_type from job page if not already set
        if not item['work_type']:
            item['work_type'] = work_type
        # Only use pay_range from job page if not already set
        if not item['pay_range']:
            item['pay_range'] = pay_range
        item['job_description'] = str(content)

        return item

    def fetch_job_description(self, url):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'lxml')


        location = soup.find("span", attrs={"data-automation": "job-detail-location"})
        location_text = location.text if location else None

        classifications = soup.find("span", attrs={"data-automation": "job-detail-classifications"})
        classifications_text = classifications.text if classifications else None

        work_type = soup.find("span", attrs={"data-automation": "job-detail-work-type"})
        work_type_text = work_type.text if work_type else None

        salary = soup.find("span", attrs={"data-automation": "job-detail-salary"})
        salary_text = salary.text if salary else None

        job_details = soup.find("div", attrs={"data-automation": "jobAdDetails"})
        # content = []
        # full_content = ''
        # if job_details:
        #     for elem in job_details.recursiveChildGenerator():
        #         if isinstance(elem, str) and elem.strip():
        #             content.append(elem.strip())
        #
        #     # Join all non-empty strings with a single space
        #     full_content = ' '.join(content)
        #     print(full_content)
        # else:
        #     print("Job details not found")

        return location_text,classifications_text,work_type_text,salary_text,job_details

    def parse_advert_details(self, item, advert_details):
        details_mapping = {
            'suburb': 0,
            'job_type': 1,
            'work_type': 2,
            'pay_range': 3
        }
        for key, index in details_mapping.items():
            if len(advert_details) > index:
                item[key] = advert_details[index].get_text().replace(self.remove_text, '').strip()
            else:
                item[key] = ''

        # The pay range is optional, check if it exists
        if len(advert_details) >= 4:
            item['pay_range'] = advert_details[3].get_text()

    def close(self, reason):
        # This method is called when the spider is about to close
        self.crawler.stats.set_value('scraped_job_ids', self.scraped_job_ids)