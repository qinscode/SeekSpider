import scrapy
import json
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
        "where": "All Perth WA",
        "seekSelectAllPages": True,
        "classification": 6281,
        "hadPremiumListings": True,
        "include": "seodata",
        "locale": "en-AU",
        'url_page': 1
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                      'Version/17.4.1 Safari/605.1.15'
    }
    base_url = "https://www.seek.com.au/api/chalice-search/v4/search"
    query_string = urlencode(params, doseq=True)
    jd_url = "https://www.seek.com.au/job/"
    remove_text = '(Information & Communication Technology)'

    def start_requests(self):

        url = f"{self.base_url}?{self.query_string}"
        self.logger.info("Ready for the first page, the page number is %s", url)
        yield Request(
            url=url, headers=self.headers, dont_filter=True, callback=self.parse
        )

    def parse(self, response):
        current_page = self.params['url_page']
        seekItem = SeekspiderItem()

        raw_data = json.loads(response.text)
        if 'current_page' in raw_data:
            current_page = raw_data['currentPage']
        totalPages = raw_data['totalPages']

        count = 1
        for data in raw_data['data']:
            seekItem['job_id'] = data['id']
            seekItem['area'] = data['area']
            seekItem['url'] = self.jd_url + str(data['id'])
            seekItem['advertiser_id'] = data['advertiser']['id']
            seekItem['job_title'] = data['title']
            seekItem['business_name'] = data['advertiser']['description']

            response = requests.get(seekItem['url'])

            soup = BeautifulSoup(response.text, 'lxml')
            job_details_div = soup.select_one('div[data-automation="jobAdDetails"]')
            divs = soup.find_all('span', {'class': 'y735df0 _1iz8dgs4y _1iz8dgsr'})

            print(f"Current Page: {current_page}, Total Page: {totalPages - 1},"
                  f" this is the {count} job of this page: {seekItem['job_title']}")
            for div in divs:
                self.logger.info(div.getText())
            seekItem['suburb'] = divs[0].get_text()
            seekItem['job_type'] = divs[1].get_text().replace(self.remove_text, '')
            seekItem['work_type'] = divs[2].get_text()
            seekItem['pay_range'] = ''
            if len(divs) >= 4:
                seekItem['pay_range'] = divs[3].get_text()
            content = ''
            for elem in job_details_div.recursiveChildGenerator():
                if isinstance(elem, str):
                    content += elem.strip() + ' '

            content = content.strip()
            seekItem['job_description'] = content

            yield seekItem
            count += 1

        if current_page > totalPages - 1:
            raise CloseSpider(reason=f'Has reached end of {totalPages - 1}, the program will exit :)')
        self.params['url_page'] += 1
        next_url = f"{self.base_url}?{self.query_string}"
        yield Request(
            url=next_url, headers=self.headers, dont_filter=True, callback=self.parse
        )
