import json
import os
from datetime import datetime

from SeekSpider.core.ai_client import AIClient
from SeekSpider.core.config import config
from SeekSpider.core.database import DatabaseManager
from SeekSpider.core.logger import Logger


class TechStackAnalyzer:
    def __init__(self, db_manager, ai_client, logger):
        self.db = db_manager
        self.ai_client = ai_client
        self.logger = logger
        self.prompt = self._load_prompt()

    def _load_prompt(self):
        """Load the prompt template from file"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            prompt_path = os.path.join(current_dir, 'prompt.txt')

            with open(prompt_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except FileNotFoundError:
            self.logger.error(f"Prompt file not found at: {prompt_path}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading prompt: {str(e)}")
            raise

    def _clean_api_response(self, response_text):
        """Clean and parse API response"""
        try:
            # Try to find content between first [ and last ]
            start = response_text.find('[')
            end = response_text.rfind(']')

            if start != -1 and end != -1:
                json_str = response_text[start:end + 1]
                return json.loads(json_str)

            # If no array markers found, try direct parse
            return json.loads(response_text)
        except json.JSONDecodeError:
            self.logger.warning(f"Failed to parse response: {response_text}")
            return []

    def analyze_job(self, job_id, description):
        """Analyze a single job's tech stack"""
        try:
            self.logger.info(f"Analyzing job {job_id}")

            # Get AI analysis
            response = self.ai_client.analyze_text(self.prompt, description)
            if not response:
                self.logger.warning(f"No response from AI for job {job_id}")
                return

            # Parse tech stack from response
            tech_stack = self._clean_api_response(response)
            if not isinstance(tech_stack, list):
                self.logger.warning(f"Invalid response format for job {job_id}")
                return

            # Update database
            self.db.update_job(job_id, {
                "TechStack": json.dumps(tech_stack),
                "UpdatedAt": datetime.now()
            })

            self.logger.info(f"Successfully analyzed job {job_id}: {tech_stack}")
            return tech_stack

        except Exception as e:
            self.logger.error(f"Error analyzing job {job_id}: {str(e)}")
            return None

    def process_all_jobs(self):
        """Process all unprocessed jobs"""
        try:
            # Get unprocessed jobs
            jobs = self.db.get_unprocessed_jobs()
            total_jobs = len(jobs)
            self.logger.info(f"Found {total_jobs} jobs to process")

            processed = 0
            errors = 0

            # Process each job
            for job_id, description in jobs:
                try:
                    if self.analyze_job(job_id, description):
                        processed += 1
                    else:
                        errors += 1
                except Exception as e:
                    self.logger.error(f"Failed to process job {job_id}: {str(e)}")
                    errors += 1
                    continue

            # Log summary
            self.logger.info("\nProcessing Summary:")
            self.logger.info(f"Total jobs: {total_jobs}")
            self.logger.info(f"Successfully processed: {processed}")
            self.logger.info(f"Errors: {errors}")
            if total_jobs > 0:
                success_rate = ((total_jobs - errors) / total_jobs * 100)
                self.logger.info(f"Success rate: {success_rate:.2f}%")

        except Exception as e:
            self.logger.error(f"Critical error in process_all_jobs: {str(e)}")
            raise


def main():
    """Main entry point for tech stack analysis"""
    try:
        # Initialize components
        logger = Logger('tech_stack_analyzer')
        db = DatabaseManager(config)
        db.set_logger(logger)
        ai_client = AIClient(config)

        # Create analyzer and process jobs
        analyzer = TechStackAnalyzer(db, ai_client, logger)
        analyzer.process_all_jobs()

    except Exception as e:
        logger.error(f"Failed to run tech stack analysis: {str(e)}")
        raise


if __name__ == "__main__":
    main()
