import json
import os
import re
import sys
from datetime import datetime

# Add parent directory to path for relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ai_client import AIClient, AIKeysExhaustedError
from core.config import config
from core.database import DatabaseManager
from core.logger import Logger


HOURLY_FACTOR = 1976  # 7.6h x 5d x 52w
DAILY_FACTOR = 260    # 5d x 52w

_HOURLY_RE = re.compile(r'per\s*hour|/\s*h(?:ou)?r\b|\bp\.?\s?h\.?(?=\s|$|[,;)+])|\bhourly\b', re.I)
_DAILY_RE = re.compile(r'per\s*day|/\s*day\b|\bp\.?\s?d\.?(?=\s|$|[,;)+])|\bdaily\b|\ba\s+day\b', re.I)
# Anything that makes the text ambiguous: annual/weekly/monthly figures, "k" amounts, alternatives
_AMBIGUOUS_RE = re.compile(
    r'\bOR\b|\d\s*k\b|\bp\.?a\.?\b|per\s*(?:annum|year|week|month|fortnight)|annual|salary|package|pkg|\bweek|\bmonth',
    re.I,
)


def rule_based_salary(pay_range):
    """
    Deterministic annualisation for unambiguous hourly/daily PayRange text.

    Returns [min, max] (annual AUD) or None when the text is not a clear
    hourly-only / daily-only figure. Used to cross-check the AI result:
    LLMs occasionally apply the wrong multiplier (e.g. x520 for a day rate).
    """
    if not pay_range:
        return None
    text = str(pay_range)
    if _AMBIGUOUS_RE.search(text):
        return None
    hourly = bool(_HOURLY_RE.search(text))
    daily = bool(_DAILY_RE.search(text))
    if hourly == daily:  # neither, or both (e.g. "$200/hr, 7.5 hours per day")
        return None

    cleaned = re.sub(r'\d+(?:\.\d+)?\s*%', ' ', text)                              # 12% super
    cleaned = re.sub(r'\d+(?:\.\d+)?\s*(?:hours?|hrs?|days?|months?|weeks?|years?)\b', ' ', cleaned, flags=re.I)
    nums = [float(n.replace(',', '')) for n in re.findall(r'\d[\d,]*(?:\.\d+)?', cleaned)]
    factor = HOURLY_FACTOR if hourly else DAILY_FACTOR
    lo, hi = (10, 1000) if hourly else (50, 5000)
    # Drop numbers that cannot be a rate (e.g. the "12" in "12M Contract")
    nums = [n for n in nums if lo <= n <= hi]
    if len(nums) not in (1, 2):
        return None
    low, high = min(nums), max(nums)
    return [int(round(low * factor)), int(round(high * factor))]


class SalaryNormalizer:
    def __init__(self, db_manager, ai_client, logger):
        self.db = db_manager
        self.ai_client = ai_client
        self.logger = logger
        self.prompt = self._load_prompt()

    def _truncate_text(self, text, limit: int = 200):
        if text is None:
            return None
        text = str(text)
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def _set_zero_salary(
        self,
        job_id,
        reason: str = None,
        pay_range: str = None,
        ai_response: str = None,
        salary_range=None,
    ):
        """Persist zero salary to mark jobs with no usable salary info."""
        self.db.update_job(job_id, {
            "MinSalary": 0,
            "MaxSalary": 0
        })
        if reason:
            log_pay_range = self._truncate_text(pay_range)
            log_ai_response = self._truncate_text(ai_response)
            self.logger.info(
                f"Set salary to 0 for job {job_id}: reason={reason}, "
                f"pay_range={log_pay_range}, ai_response={log_ai_response}, parsed={salary_range}"
            )

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

    @staticmethod
    def _close(a, b, tol: float = 0.01):
        return all(abs(x - y) <= max(1, tol * y) for x, y in zip(a, b))

    def normalize_salary(self, job_id, pay_range):
        """Normalize a single job's salary range"""
        try:
            if not pay_range or str(pay_range).strip() == "":
                self.logger.debug(f"No salary info for job {job_id}")
                self._set_zero_salary(
                    job_id,
                    reason="empty PayRange",
                    pay_range=pay_range,
                    ai_response=None,
                    salary_range=[0, 0],
                )
                return [0, 0]

            # Get AI analysis
            response = self.ai_client.analyze_text(self.prompt, pay_range)
            if not response:
                self.logger.warning(f"No AI response for job {job_id}")
                return [0, 0]

            # Parse salary range
            salary_range = self._parse_salary_range(response)

            # Cross-check against the deterministic rule for clear hourly/daily rates
            rule_range = rule_based_salary(pay_range)
            if rule_range and not self._close(salary_range, rule_range):
                self.logger.warning(
                    f"AI salary {salary_range} disagrees with rule {rule_range} for job {job_id} "
                    f"(pay_range={self._truncate_text(pay_range)}); using rule-based value"
                )
                salary_range = rule_range

            # Only update database if we have valid salary (at least one non-zero value)
            if salary_range[0] <= 0 and salary_range[1] <= 0:
                self._set_zero_salary(
                    job_id,
                    reason="no usable salary in AI response",
                    pay_range=pay_range,
                    ai_response=response,
                    salary_range=salary_range,
                )
                return salary_range

            # Update database with valid salary
            self.db.update_job(job_id, {
                "MinSalary": int(salary_range[0]),
                "MaxSalary": int(salary_range[1])
            })

            return salary_range

        except AIKeysExhaustedError:
            raise  # Out of balance: let the caller stop the run
        except Exception as e:
            self.logger.error(f"Error normalizing salary for job {job_id}: {str(e)}")
            return [0, 0]

    def process_all_jobs(self):
        """Process all jobs needing salary normalization"""
        try:
            # First check database status
            debug_query = f'''
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN "PayRange" IS NULL THEN 1 END) as null_payrange,
                    COUNT(CASE WHEN "PayRange" = '' THEN 1 END) as empty_payrange,
                    COUNT(CASE WHEN "MinSalary" IS NULL THEN 1 END) as null_min_salary,
                    COUNT(CASE WHEN "MaxSalary" IS NULL THEN 1 END) as null_max_salary
                FROM "{self.db.config.POSTGRESQL_TABLE}"
            '''
            debug_result = self.db.execute_query(debug_query)
            self.logger.info("Database status:")
            self.logger.info(f"Total records: {debug_result[0][0]}")
            self.logger.info(f"Null PayRange: {debug_result[0][1]}")
            self.logger.info(f"Empty PayRange: {debug_result[0][2]}")
            self.logger.info(f"Null MinSalary: {debug_result[0][3]}")
            self.logger.info(f"Null MaxSalary: {debug_result[0][4]}")

            # First batch update jobs with empty PayRange
            batch_update_query = f'''
                UPDATE "{self.db.config.POSTGRESQL_TABLE}"
                SET 
                    "MinSalary" = 0,
                    "MaxSalary" = 0,
                    "UpdatedAt" = now()
                WHERE ("MinSalary" IS NULL OR "MaxSalary" IS NULL)
                AND ("PayRange" IS NULL OR TRIM("PayRange") = '')
            '''
            affected_rows = self.db.execute_update(batch_update_query)
            self.logger.info(f"Batch updated {affected_rows} jobs with empty PayRange to zero salary")

            # Then process jobs with salary information
            query = f'''
                SELECT "Id", "PayRange"
                FROM "{self.db.config.POSTGRESQL_TABLE}" 
                WHERE ("MinSalary" IS NULL OR "MaxSalary" IS NULL)
                AND "PayRange" IS NOT NULL
                AND TRIM("PayRange") != ''
            '''
            jobs = self.db.execute_query(query)

            total_jobs = len(jobs)
            self.logger.info(f"Found {total_jobs} jobs needing salary normalization")

            processed = 0
            errors = 0
            error_details = []

            # Process each job
            for job_id, pay_range in jobs:
                try:
                    salary_range = self.normalize_salary(job_id, pay_range)
                    if salary_range[0] > 0 or salary_range[1] > 0:
                        processed += 1
                    else:
                        errors += 1
                        error_details.append({
                            'job_id': job_id,
                            'pay_range': pay_range,
                            'result': 'Zero salary range'
                        })
                except AIKeysExhaustedError as e:
                    self.logger.error(f"Stopping salary normalization: {e}. Top up the AI account balance.")
                    break
                except Exception as e:
                    self.logger.error(f"Failed to process job {job_id}: {str(e)}")
                    errors += 1
                    error_details.append({
                        'job_id': job_id,
                        'pay_range': pay_range,
                        'error': str(e)
                    })
                    continue

            # Log summary
            self.logger.info("\nSalary Normalization Summary:")
            self.logger.info(f"Total jobs with empty PayRange: {affected_rows}")
            self.logger.info(f"Total jobs with PayRange: {total_jobs}")
            self.logger.info(f"Successfully processed: {processed}")
            self.logger.info(f"Errors: {errors}")
            if total_jobs > 0:
                success_rate = ((total_jobs - errors) / total_jobs * 100)
                self.logger.info(f"Success rate: {success_rate:.2f}%")
            
            if error_details:
                self.logger.info("\nError Details:")
                for detail in error_details:
                    self.logger.info(f"Job ID: {detail['job_id']}")
                    self.logger.info(f"Pay Range: {detail['pay_range']}")
                    if 'error' in detail:
                        self.logger.info(f"Error: {detail['error']}")
                    else:
                        self.logger.info(f"Result: {detail['result']}")
                    self.logger.info("---")

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
