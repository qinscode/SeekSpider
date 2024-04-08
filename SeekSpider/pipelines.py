import pymysql
from SeekSpider.settings_local import *

class SeekspiderPipeline(object):

    def open_spider(self, spider):
        self.connection = pymysql.connect(host=MYSQL_HOST,
                                          user=MYSQL_USER,
                                          password=MYSQL_PASSWORD,
                                          db=MYSQL_DATABASE,
                                          charset='utf8mb4')
        self.cursor = self.connection.cursor()

    def close_spider(self, spider):
        self.connection.close()

    def process_item(self, item, spider):
        insert_sql = """
            INSERT INTO {} (
                job_id, 
                job_title, 
                business_name, 
                work_type, 
                job_description, 
                pay_range, 
                suburb, 
                area, 
                url, 
                advertiser_id, 
                job_type
            ) 
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
            )
            """.format(MYSQL_TABLE)

        try:
            self.cursor.execute(insert_sql, (
                item.get('job_id'),
                item.get('job_title'),
                item.get('business_name'),
                item.get('work_type'),
                item.get('job_description'),
                item.get('pay_range'),
                item.get('suburb'),
                item.get('area'),
                item.get('url'),
                item.get('advertiser_id'),
                item.get('job_type')
            ))
            self.connection.commit()
            print(f"Job {item.get('job_id')} was inserted successfully")
        except Exception as e:
            print(f"An error occurred: {e} for job {item.get('job_id')}")

        return item
