import psycopg2
from SeekSpider.settings_local import *
from scrapy import signals
from scrapy.exceptions import NotConfigured

class SeekspiderPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        # Create a pipeline instance
        instance = cls()
        # Connect the spider_closed signal
        crawler.signals.connect(instance.spider_closed, signal=signals.spider_closed)
        return instance

    def open_spider(self, spider):
        self.connection = psycopg2.connect(host=POSTGRESQL_HOST,
                                          user=POSTGRESQL_USER,
                                          password=POSTGRESQL_PASSWORD,
                                          database=POSTGRESQL_DATABASE,
                                          port=POSTGRESQL_PORT)
        self.cursor = self.connection.cursor()
        
        # Set all IsNew to False before starting the spider
        update_sql = f'UPDATE "{POSTGRESQL_TABLE}" SET "IsNew" = FALSE, "UpdatedAt" = now()'
        self.cursor.execute(update_sql)
        self.connection.commit()
        spider.logger.info("Set all existing jobs' IsNew to False")
        
        # Load all job IDs into memory
        self.cursor.execute(f'SELECT "Id" FROM "{POSTGRESQL_TABLE}"')
        self.existing_job_ids = set(row[0] for row in self.cursor.fetchall())

    def close_spider(self, spider):
        # Remove this method as we'll close the connection in spider_closed
        pass

    def process_item(self, item, spider):
        job_id = item.get('job_id')
        
        # Check if the job ID already exists in memory
        if job_id in self.existing_job_ids:
            print(f"Job ID: {job_id} already exists. Skipping insertion.")
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
                "IsNew",
                "PostedDate"
            ) 
            VALUES (
                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),now(),true,%s
            )
            """.format(POSTGRESQL_TABLE)

        try:
            params = (
                job_id,
                item.get('job_title'),
                item.get('business_name'),
                item.get('work_type'),
                item.get('job_description'),
                item.get('pay_range'),
                item.get('suburb'),
                item.get('area'),
                item.get('url'),
                advertiser_id,  # Use the modified advertiser_id
                item.get('job_type'),
                item.get('posted_date')
            )


            self.cursor.execute(insert_sql, params)
            self.connection.commit()
            print(f"Job ID: {job_id}. Job inserted successfully.")  # Print the generated UUID

            # Add the new job ID to the in-memory set
            self.existing_job_ids.add(job_id)
        except Exception as e:
            print(f"An error occurred: {e} for job {job_id}")

        return item

    def spider_closed(self, spider):
        scraped_job_ids = spider.crawler.stats.get_value('scraped_job_ids', set())
        
        # Find job IDs that are in the database but not in the scraped set
        invalid_job_ids = self.existing_job_ids - scraped_job_ids

        if invalid_job_ids:
            # Log the number of potentially invalid jobs
            spider.logger.info(f"Found {len(invalid_job_ids)} jobs not in current scrape")
            
            # Log the first 10 invalid job IDs (to avoid excessive logging)
            sample_invalid_jobs = list(invalid_job_ids)[:10]
            spider.logger.info(f"Sample of jobs not in current scrape: {sample_invalid_jobs}")

            # Only update jobs that are currently active
            update_sql = f"""
                UPDATE "{POSTGRESQL_TABLE}"
                SET "IsActive" = FALSE, 
                    "UpdatedAt" = now(),
                    "ExpiryDate" = now()
                WHERE "Id" = ANY(%s)
                AND "IsActive" = TRUE
            """
            self.cursor.execute(update_sql, (list(invalid_job_ids),))
            rows_affected = self.cursor.rowcount
            self.connection.commit()
            spider.logger.info(f"Updated {rows_affected} active jobs to IsActive=False")

            # Log the SQL query for debugging purposes
            spider.logger.debug(f"Executed SQL: {update_sql}")
            spider.logger.debug(f"With parameters: {list(invalid_job_ids)}")
        else:
            spider.logger.info("No invalid jobs found")

        # Close the connection after all operations are done
        self.cursor.close()
        self.connection.close()
        spider.logger.info("Database connection closed")
