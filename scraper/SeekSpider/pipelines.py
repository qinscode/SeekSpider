import json
import logging
import os
from datetime import datetime

import psycopg2
from scrapy import signals

from SeekSpider.core.config import config


class JsonExportPipeline:
    """Pipeline to export scraped items to JSON files and logs"""

    def open_spider(self, spider):
        # Create output directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Get output base path from environment or use default
        output_base = os.getenv('OUTPUT_PATH', os.path.join(os.path.dirname(__file__), '../../output'))
        self.output_dir = os.path.join(output_base, 'seek_spider', timestamp)

        os.makedirs(self.output_dir, exist_ok=True)

        # Initialize data file
        self.jobs_file = open(os.path.join(self.output_dir, 'jobs.jsonl'), 'w', encoding='utf-8')
        self.items_count = 0

        # Setup log file in the same directory
        self.log_file_path = os.path.join(self.output_dir, 'spider.log')
        self.file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        self.file_handler.setLevel(logging.INFO)
        self.file_handler.setFormatter(logging.Formatter(
            '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
        ))

        # Add file handler to spider's logger and root scrapy logger
        spider.logger.logger.addHandler(self.file_handler)
        logging.getLogger('scrapy').addHandler(self.file_handler)

        spider.logger.info(f"Output directory: {self.output_dir}")
        spider.logger.info(f"Log file: {self.log_file_path}")

    def close_spider(self, spider):
        self.jobs_file.close()

        # Write summary
        summary = {
            'total_items': self.items_count,
            'timestamp': datetime.now().isoformat(),
            'output_dir': self.output_dir,
            'log_file': self.log_file_path
        }

        with open(os.path.join(self.output_dir, 'summary.json'), 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)

        spider.logger.info(f"Exported {self.items_count} items to {self.output_dir}")

        # Remove and close file handler
        spider.logger.logger.removeHandler(self.file_handler)
        logging.getLogger('scrapy').removeHandler(self.file_handler)
        self.file_handler.close()

    def process_item(self, item, spider):
        # Convert item to dict and write as JSON line
        item_dict = dict(item)

        # Remove HTML content for file export (keep it smaller)
        export_dict = {
            'job_id': item_dict.get('job_id'),
            'job_title': item_dict.get('job_title'),
            'business_name': item_dict.get('business_name'),
            'work_type': item_dict.get('work_type'),
            'job_type': item_dict.get('job_type'),
            'pay_range': item_dict.get('pay_range'),
            'suburb': item_dict.get('suburb'),
            'area': item_dict.get('area'),
            'url': item_dict.get('url'),
            'advertiser_id': item_dict.get('advertiser_id'),
            'posted_date': item_dict.get('posted_date'),
            'scraped_at': datetime.now().isoformat()
        }

        line = json.dumps(export_dict, ensure_ascii=False)
        self.jobs_file.write(line + '\n')
        self.items_count += 1

        return item


class SeekspiderPipeline(object):

    @classmethod
    def from_crawler(cls, crawler):
        # Create a pipeline instance
        instance = cls()
        # Connect the spider_closed signal
        crawler.signals.connect(instance.spider_closed, signal=signals.spider_closed)
        return instance

    def open_spider(self, spider):
        self.connection = psycopg2.connect(
            host=config.POSTGRESQL_HOST,
            user=config.POSTGRESQL_USER,
            password=config.POSTGRESQL_PASSWORD,
            database=config.POSTGRESQL_DATABASE,
            port=config.POSTGRESQL_PORT
        )
        self.cursor = self.connection.cursor()

        # Load all job IDs into memory, regardless of their status
        try:
            self.cursor.execute(f'SELECT "Id" FROM "{config.POSTGRESQL_TABLE}"')
            self.existing_job_ids = set(str(row[0]) for row in self.cursor.fetchall())
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
            """.format(config.POSTGRESQL_TABLE)

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
                # spider.logger.info(f"Job ID: {job_id} updated successfully.")

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
            """.format(config.POSTGRESQL_TABLE)

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
                UPDATE "{config.POSTGRESQL_TABLE}"
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
