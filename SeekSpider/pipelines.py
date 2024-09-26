import psycopg2
from SeekSpider.settings_local import *

class SeekspiderPipeline(object):

    def open_spider(self, spider):
        self.connection = psycopg2.connect(host=MYSQL_HOST,
                                          user=MYSQL_USER,
                                          password=MYSQL_PASSWORD,
                                          database=MYSQL_DATABASE,
                                          port=MYSQL_PORT)
        self.cursor = self.connection.cursor()

    def close_spider(self, spider):
        self.connection.close()

    def process_item(self, item, spider):
        # Check if the job ID already exists in the database
        check_sql = """
            SELECT 1 FROM "{}" WHERE "Id" = %s
        """.format(MYSQL_TABLE)
        
        self.cursor.execute(check_sql, (item.get('job_id'),))
        if self.cursor.fetchone():
            print(f"Job ID: {item.get('job_id')} already exists. Skipping insertion.")
            return item

        # Handle empty AdvertiserId
        advertiser_id = item.get('advertiser_id')
        if advertiser_id == "":
            advertiser_id = None

        insert_sql = """
            INSERT INTO "{}" (
                "Id", 
                "JobTitle", 
                "BusinessName", 
                "WorkType", 
                "JobDescription", 
                "PayRange", 
                "Suburb", 
                "Area", 
                "Url", 
                "AdvertiserId", 
                "JobType",
                "CreatedAt",
                "UpdatedAt",
                "IsNew"
            ) 
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now(),true
            )
            """.format(MYSQL_TABLE)

        try:
            params = (
                item.get('job_id'),
                item.get('job_title'),
                item.get('business_name'),
                item.get('work_type'),
                item.get('job_description'),
                item.get('pay_range'),
                item.get('suburb'),
                item.get('area'),
                item.get('url'),
                advertiser_id,  # Use the modified advertiser_id
                item.get('job_type')
            )
            self.cursor.execute(insert_sql, params)
            self.connection.commit()
            print(f"Job ID: {item.get('job_id')}. Job inserted successfully.")  # Print the generated UUID
        except Exception as e:
            print(f"An error occurred: {e} for job {item.get('job_id')}")

        return item
