import json
import os
from datetime import datetime

from SeekSpider.core.ai_client import AIClient
from SeekSpider.core.config import config
from SeekSpider.core.database import DatabaseManager
from SeekSpider.core.logger import Logger


class SalaryNormalizer:
    def __init__(self, db_manager, ai_client, logger):
        self.db = db_manager
        self.ai_client = ai_client
        self.logger = logger
        self.prompt = self._load_prompt()

    def _load_prompt(self):
        """Load the salary normalization prompt"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, 'salary_prompt.txt')

            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            self.logger.error(f"Salary prompt file not found at: {prompt_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading salary prompt: {str(e)}")
            raise

    def _parse_salary_range(self, response_text):
        """Parse salary range from AI response"""
        try:
            # Try to find array in response
            start = response_text.find('[')
            end = response_text.rfind(']')

            if start != -1 and end != -1:
                json_str = response_text[start:end + 1]
                salary_range = json.loads(json_str)

                # Validate format
                if (isinstance(salary_range, list) and
                        len(salary_range) == 2 and
                        all(isinstance(x, (int, float)) for x in salary_range)):
                    return salary_range

            self.logger.warning(f"Invalid salary format: {response_text}")
            return [0, 0]

        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse salary response: {response_text}")
            return [0, 0]
        except Exception as e:
            self.logger.error(f"Error parsing salary range: {str(e)}")
            return [0, 0]

    def normalize_salary(self, job_id, pay_range):
        """Normalize a single job's salary range"""
        try:
            if not pay_range:
                self.logger.debug(f"No salary info for job {job_id}")
                return [0, 0]

            self.logger.info(f"Normalizing salary for job {job_id}: {pay_range}")

            # Get AI analysis
            response = self.ai_client.analyze_text(self.prompt, pay_range)
            if not response:
                self.logger.warning(f"No AI response for job {job_id}")
                return [0, 0]

            # Parse salary range
            salary_range = self._parse_salary_range(response)

            # Update database
            self.db.update_job(job_id, {
                "MinSalary": salary_range[0],
                "MaxSalary": salary_range[1],
                "UpdatedAt": datetime.now()
            })

            self.logger.info(
                f"Normalized salary for job {job_id}: {salary_range}"
            )
            return salary_range

        except Exception as e:
            self.logger.error(f"Error normalizing salary for job {job_id}: {str(e)}")
            return [0, 0]

    def process_all_jobs(self):
        """Process all jobs needing salary normalization"""
        try:
            # Get jobs needing processing
            query = f'''
                SELECT "Id", "PayRange"
                FROM "{self.db.config.POSTGRESQL_TABLE}" 
                WHERE ("MinSalary" IS NULL OR "MaxSalary" IS NULL)
                AND "PayRange" IS NOT NULL
            '''
            jobs = self.db.execute_query(query)

            total_jobs = len(jobs)
            self.logger.info(f"Found {total_jobs} jobs needing salary normalization")

            processed = 0
            errors = 0

            # Process each job
            for job_id, pay_range in jobs:
                try:
                    salary_range = self.normalize_salary(job_id, pay_range)
                    if salary_range[0] > 0 or salary_range[1] > 0:
                        processed += 1
                    else:
                        errors += 1
                except Exception as e:
                    self.logger.error(f"Failed to process job {job_id}: {str(e)}")
                    errors += 1
                    continue

            # Log summary
            self.logger.info("\nSalary Normalization Summary:")
            self.logger.info(f"Total jobs: {total_jobs}")
            self.logger.info(f"Successfully processed: {processed}")
            self.logger.info(f"Errors: {errors}")
            if total_jobs > 0:
                success_rate = ((total_jobs - errors) / total_jobs * 100)
                self.logger.info(f"Success rate: {success_rate:.2f}%")

        except Exception as e:
            self.logger.error(f"Critical error in salary normalization: {str(e)}")
            raise


def main():
    """Main entry point for salary normalization"""
    try:
        # Initialize components
        logger = Logger('salary_normalizer')
        db = DatabaseManager(config)
        db.set_logger(logger)
        ai_client = AIClient(config)

        # Create normalizer and process jobs
        normalizer = SalaryNormalizer(db, ai_client, logger)
        normalizer.process_all_jobs()

    except Exception as e:
        logger.error(f"Failed to run salary normalization: {str(e)}")
        raise


if __name__ == "__main__":
    main()
