import scrapy
from scrapy import Request
from urllib.parse import urlencode
from scrapy.exceptions import CloseSpider
from SeekSpider.items import SeekspiderItem
from bs4 import BeautifulSoup
import requests

class SeekSpider(scrapy.Spider):
    name = "seek"
    allowed_domains = ["www.seek.com.au"]
    params = {
    'siteKey': 'AU-Main',
    'sourcesystem': 'houston',
    'where': 'All Sydney NSW',
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
                      'Version/17.4.1 Safari/605.1.15'
    }
    base_url = "https://www.seek.com.au/api/chalice-search/v4/search"
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
        total_pages = raw_data['totalPages']
        self.logger.info(f'Total Pages: {total_pages}')

        for data in raw_data['data']:
            yield self.parse_job(data)

        #  if there are more pages to scrape, keep going with current subclass
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
                print(f'len subclassification_dict: {len(self.subclassification_dict)}',not bool(self.subclassification_dict))
                self.logger.info('No more subclasses to scrape.')
                raise CloseSpider('Reached last page of results')

    def get_next_page_url(self):
        query_string = urlencode(self.params)
        return f"{self.base_url}?{query_string}"

    def parse_job(self, data):
        item = SeekspiderItem()
        item['job_id'] = data['id']
        item['area'] = data.get('area', data['location'])
        item['url'] = self.jd_url + str(data['id'])
        item['advertiser_id'] = data['advertiser']['id']
        item['job_title'] = data['title']
        item['business_name'] = data['advertiser']['description']
        suburb, job_type, work_type, pay_range, content = self.fetch_job_description(item['url'])

        item['suburb'] = suburb
        item['job_type'] = job_type
        item['work_type'] = work_type
        item['pay_range'] = pay_range
        item['job_description'] = content

        if 'advertDetails' in data:
            self.parse_advert_details(item, data['advertDetails'])

        return item

    def fetch_job_description(self, url):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.text, 'lxml')
        job_details_div = soup.select_one('div[data-automation="jobAdDetails"]')
        divs = soup.find_all('span', {'class': 'y735df0 _1iz8dgs4y _1iz8dgsr'})

        suburb = divs[0].get_text()
        job_type = divs[1].get_text().replace(self.remove_text, '')
        work_type= divs[2].get_text()
        pay_range = ''
        if len(divs) >= 4:
            pay_range = divs[3].get_text()
        content = ''
        for elem in job_details_div.recursiveChildGenerator():
            if isinstance(elem, str):
                content += elem.strip() + ' '

        return suburb,job_type,work_type,pay_range,content

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