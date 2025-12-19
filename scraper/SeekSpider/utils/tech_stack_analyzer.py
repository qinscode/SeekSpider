import json
import os
import sys
import time
from datetime import datetime
from functools import wraps

# Add parent directory to path for relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_client import AIClient
from core.config import config
from core.database import DatabaseManager
from core.logger import Logger

def retry_on_db_error(max_retries=3, delay=5):
    """
    Database operation retry decorator.

    Args:
        max_retries (int): Maximum number of retries
        delay (int): Delay between retries in seconds
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if "Cannot allocate memory" in str(e) or "connection" in str(e).lower():
                        self = args[0]  # Get class instance
                        self.logger.warning(
                            f"Database operation failed (attempt {retries}/{max_retries}): {str(e)}"
                            f"\nRetrying in {delay} seconds..."
                        )
                        if retries < max_retries:
                            time.sleep(delay)
                            continue
                    raise
            raise Exception(f"Failed after {max_retries} retries")
        return wrapper
    return decorator

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

    @retry_on_db_error()
    def analyze_job(self, job_id, description):
        """Analyze a single job's tech stack"""
        try:
            # Add description preview to log
            desc_preview = (description[:50] + '...') if len(description) > 50 else description
            self.logger.info(f"Analyzing job {job_id} - Description: {desc_preview}")

            # Get AI analysis
            response = self.ai_client.analyze_text(self.prompt, description)
            if not response:
                self.logger.warning(f"No response from AI for job {job_id}")
                return None

            # Parse tech stack from response
            tech_stack = self._clean_api_response(response)
            if not isinstance(tech_stack, list):
                self.logger.warning(f"Invalid response format for job {job_id}")
                return None

            # Only update database if tech_stack is not empty
            if not tech_stack or len(tech_stack) == 0:
                self.logger.info(f"No tech stack found for job {job_id}, skipping database update")
                return None

            # Update database with valid tech stack
            self.db.update_job(job_id, {
                "TechStack": json.dumps(tech_stack)
            })

            self.logger.info(f"Successfully analyzed job {job_id}: {tech_stack}")
            return tech_stack

        except Exception as e:
            self.logger.error(f"Error analyzing job {job_id} - Description: {desc_preview}: {str(e)}")
            raise  # Let decorator catch exception and retry

    @retry_on_db_error()
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
