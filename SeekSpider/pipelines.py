import psycopg2
from scrapy import signals

from SeekSpider.config import *


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
        
        # Load all job IDs into memory, regardless of their status
        try:
            self.cursor.execute(f'SELECT "Id" FROM "{POSTGRESQL_TABLE}"')
            self.existing_job_ids = set(str(row[0]) for row in self.cursor.fetchall())  # Convert IDs to strings
            spider.logger.info(f"Loaded {len(self.existing_job_ids)} existing job IDs")
        except Exception as e:
            spider.logger.error(f"Error loading existing job IDs: {str(e)}")
            self.existing_job_ids = set()

    def close_spider(self, spider):
        # Remove this method as we'll close the connection in spider_closed
        pass

    def process_item(self, item, spider):
        job_id = str(item.get('job_id'))  # Convert to string to ensure consistent type comparison
        
        # Check if the job ID already exists in memory
        if job_id in self.existing_job_ids:
            spider.logger.info(f"Job ID: {job_id} already exists. Updating instead of inserting.")
            
            # Update existing job
            update_sql = """
                UPDATE "{}" SET 
                    "JobTitle" = %s,
                    "BusinessName" = %s,
                    "WorkType" = %s,
                    "JobDescription" = %s,
                    "PayRange" = %s,
                    "Suburb" = %s,
                    "Area" = %s,
                    "Url" = %s,
                    "AdvertiserId" = %s,
                    "JobType" = %s,
                    "UpdatedAt" = now(),
                    "PostedDate" = %s,
                    "ExpiryDate" = NULL,
                    "IsActive" = TRUE
                WHERE "Id" = %s
            """.format(POSTGRESQL_TABLE)

            try:
                advertiser_id = item.get('advertiser_id')
                if advertiser_id == "":
                    advertiser_id = None

                params = (
                    item.get('job_title'),
                    item.get('business_name'),
                    item.get('work_type'),
                    item.get('job_description'),
                    item.get('pay_range'),
                    item.get('suburb'),
                    item.get('area'),
                    item.get('url'),
                    advertiser_id,
                    item.get('job_type'),
                    item.get('posted_date'),
                    job_id
                )

                self.cursor.execute(update_sql, params)
                self.connection.commit()
                spider.logger.info(f"Job ID: {job_id} updated successfully.")
                
            except Exception as e:
                self.connection.rollback()  # 回滚事务
                spider.logger.error(f"Error updating job {job_id}: {str(e)}")
                
            return item

        # Handle new job insertion
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
            advertiser_id = item.get('advertiser_id')
            if advertiser_id == "":
                advertiser_id = None

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
                advertiser_id,
                item.get('job_type'),
                item.get('posted_date')
            )

            self.cursor.execute(insert_sql, params)
            self.connection.commit()
            spider.logger.info(f"Job ID: {job_id} inserted successfully.")

            # Add the new job ID to the in-memory set
            self.existing_job_ids.add(job_id)
            
        except Exception as e:
            self.connection.rollback()  # 回滚事务
            spider.logger.error(f"Error inserting job {job_id}: {str(e)}")

        return item

    def spider_closed(self, spider):
        scraped_job_ids = spider.crawler.stats.get_value('scraped_job_ids', set())
        
        # 找出在数据库中但不在本次爬取中的职位ID（已过期的职位）
        invalid_job_ids = self.existing_job_ids - scraped_job_ids

        if invalid_job_ids:
            spider.logger.info(f"Found {len(invalid_job_ids)} jobs not in current scrape")
            sample_invalid_jobs = list(invalid_job_ids)[:10]
            spider.logger.info(f"Sample of jobs not in current scrape: {sample_invalid_jobs}")

            # 将不存在的职位标记为失效
            update_expired_sql = f'''
                UPDATE "{POSTGRESQL_TABLE}"
                SET "IsActive" = FALSE, 
                    "UpdatedAt" = now(),
                    "ExpiryDate" = now()
                WHERE "Id" = ANY(%s::integer[])
                AND "IsActive" = TRUE
            '''
            # Convert string IDs to integers before passing to SQL
            invalid_job_ids_int = [int(job_id) for job_id in invalid_job_ids]
            self.cursor.execute(update_expired_sql, (invalid_job_ids_int,))
            expired_rows = self.cursor.rowcount
            self.connection.commit()
            spider.logger.info(f"Updated {expired_rows} jobs to IsActive=False")
        else:
            spider.logger.info("No expired jobs found")

        # 关闭数据库连接
        self.cursor.close()
        self.connection.close()
        spider.logger.info("Database connection closed")
