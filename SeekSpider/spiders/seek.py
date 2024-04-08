import logging

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
        "page": 1,
        "siteKey": "AU-Main",
        "sourcesystem": "houston",
        "userqueryid": "edf6496d865cb30078d4541fda40da4f-6828311",
        "userid": "7414413c-ae74-4fdc-8aa2-23eea861b700",
        "usersessionid": "7414413c-ae74-4fdc-8aa2-23eea861b700",
        "eventCaptureSessionId": "7414413c-ae74-4fdc-8aa2-23eea861b700",
        "where": "All Perth WA",
        "seekSelectAllPages": True,
        "classification": 6281,
        "hadPremiumListings": False,
        "locale": "en-AU",
        "seekerId": "44477194",
        "solId": "e16ff4bb-a139-4834-90f1-da38740b8d10"
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) '
                      'Version/17.4.1 Safari/605.1.15'
    }
    base_url = "https://www.seek.com.au/api/chalice-search/v4/search"
    jd_url = "https://www.seek.com.au/job/"
    remove_text = '(Information & Communication Technology)'

    def start_requests(self):
        query_string = urlencode(self.params, doseq=True)

        url = f"{self.base_url}?{query_string}"

        self.logger.info("SPIDER SETUP COMPLETED.")
        yield Request(
            url=url, headers=self.headers, dont_filter=True, callback=self.parse
        )

    # 出于效率考虑，先不用异步实现，否则有被封杀的风险
    def parse(self, response):
        query_string = urlencode(self.params, doseq=True)
        current_url = f"CURRENT URL: {self.base_url}?{query_string}"

        logging.info(f'CURRENT PAGE:{self.params["page"]}, CURRENT URL: {current_url}')

        current_page = self.params['page']
        seekItem = SeekspiderItem()

        raw_data = json.loads(response.text)
        if 'current_page' in raw_data:
            current_page = raw_data['currentPage']
        totalPages = raw_data['totalPages']
        jobs_quantity = len(raw_data['data'])

        count = 1
        for data in raw_data['data']:
            print(f'Job ID: {data["id"]}, now doing the {count} job of {jobs_quantity}')
            seekItem['job_id'] = data['id']
            if 'area' not in data:
                seekItem['area'] = data['location']
            else:
                seekItem['area'] = data['area']
            seekItem['url'] = self.jd_url + str(data['id'])
            seekItem['advertiser_id'] = data['advertiser']['id']
            seekItem['job_title'] = data['title']
            seekItem['business_name'] = data['advertiser']['description']

            response = requests.get(seekItem['url'])

            soup = BeautifulSoup(response.text, 'lxml')
            job_details_div = soup.select_one('div[data-automation="jobAdDetails"]')
            divs = soup.find_all('span', {'class': 'y735df0 _1iz8dgs4y _1iz8dgsr'})

            # print(f"Current Page: {current_page}, Total Page: {totalPages - 1},"
            #       f" this is the {count} job of this page: {seekItem['job_title']}")
            # for div in divs:
            # self.logger.info(div.getText())
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

        if current_page <= totalPages-1:

            self.params['page'] += 1
            query_string = urlencode(self.params, doseq=True)
            next_url = f"{self.base_url}?{query_string}"

            logging.info(f'NEXT PAGE:{self.params["page"]}, NEXT URL: {next_url}')
            yield Request(url=next_url, headers=self.headers, dont_filter=True, callback=self.parse)
        else:

            raise CloseSpider(reason=f'Has reached end of {totalPages - 1}, the program will exit :)')
