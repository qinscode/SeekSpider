import scrapy


class SeekspiderItem(scrapy.Item):
    job_id = scrapy.Field()
    job_title = scrapy.Field()
    business_name = scrapy.Field()
    work_type = scrapy.Field()
    job_description = scrapy.Field()
    pay_range = scrapy.Field()
    suburb = scrapy.Field()
    area = scrapy.Field()
    region = scrapy.Field()  # Australian region (e.g., Perth, Sydney, Melbourne)
    url = scrapy.Field()
    advertiser_id = scrapy.Field()
    job_type = scrapy.Field()
    posted_date = scrapy.Field()
