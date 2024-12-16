import os
import json
import time
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from SeekSpider.config import (
    POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_USER,
    POSTGRESQL_PASSWORD, POSTGRESQL_DATABASE, POSTGRESQL_TABLE,
    AI_API_KEY, AI_API_URL, AI_MODEL
)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 60  # Wait 60 seconds when quota exceeded


def load_prompt():
    """Load the prompt from salary_prompt.txt file"""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, 'salary_prompt.txt')
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found at: {prompt_path}")


def get_db_connection():
    """Create PostgreSQL database connection"""
    conn = psycopg2.connect(
        host=POSTGRESQL_HOST,
        port=POSTGRESQL_PORT,
        user=POSTGRESQL_USER,
        password=POSTGRESQL_PASSWORD,
        database=POSTGRESQL_DATABASE
    )
    return conn


def clean_api_response(response_text):
    """Clean and extract JSON array from API response"""
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
        # If still fails, try parsing each line to find valid JSON
        lines = response_text.strip().split('\n')
        for line in lines:
            try:
                if '[' in line and ']' in line:
                    return json.loads(line.strip())
            except json.JSONDecodeError:
                continue

        # If all attempts fail, return empty list
        return [0, 0]


def extract_salary_range(prompt, pay_range, job_id, retries=MAX_RETRIES):
    """Extract salary range using DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    pay_range = pay_range or "Null"
    for attempt in range(retries):
        try:
            payload = {
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": f"{prompt}\n\nInput text: {pay_range}"
                    }
                ],
                "stream": False,
                "response_format": {"type": "text"}
            }

            print(f"\nJob {job_id} - PayRange: {pay_range} - Pay ")
            print(f"Job {job_id} - Calling DeepSeek API...")
            response = requests.post(AI_API_URL, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"Job {job_id} - API error: {response.status_code} - {response.text}")
                if response.status_code == 429:  # Rate limit
                    if attempt < retries - 1:
                        print(
                            f"Job {job_id} - Rate limited. Waiting {RETRY_DELAY} seconds before retry {attempt + 1}/{retries}")
                        time.sleep(RETRY_DELAY)
                        continue
                return [0, 0]

            response_json = response.json()
            response_text = response_json['choices'][0]['message']['content']
            print(f"Job {job_id} - Raw API response: {response_text}")

            salary_range = clean_api_response(response_text)
            print(f"Job {job_id} - Parsed salary range: {salary_range}")

            # Validate response format
            if not isinstance(salary_range, list) or len(salary_range) != 2:
                print(f"Job {job_id} - Warning: Invalid response format. Expected [min, max], got: {salary_range}")
                return [0, 0]

            return salary_range

        except Exception as e:
            error_message = str(e)
            print(f"Job {job_id} - Error processing: {error_message}")
            if attempt < retries - 1:
                print(f"Job {job_id} - Retrying... ({attempt + 1}/{retries})")
                time.sleep(5)
                continue
            return [0, 0]

    return [0, 0]


def main():
    # Initialize components
    prompt = load_prompt()
    conn = get_db_connection()

    processed_count = 0
    error_count = 0

    try:
        with conn.cursor() as cur:
            # Get all jobs that don't have salary range processed
            cur.execute(f"""
                SELECT "Id", "PayRange"
                FROM "{POSTGRESQL_TABLE}" 
                WHERE ("MinSalary" IS NULL OR "MaxSalary" IS NULL)
                AND "PayRange" IS NOT NULL
            """)

            jobs = cur.fetchall()
            total_jobs = len(jobs)
            print(f"Found {total_jobs} jobs to process")

            for job_id, pay_range in jobs:
                try:
                    processed_count += 1
                    print(f"\n[{processed_count}/{total_jobs}] Processing job {job_id}...")

                    # Extract salary range
                    salary_range = extract_salary_range(prompt, pay_range, job_id)

                    # Ensure we have two numbers
                    min_salary, max_salary = salary_range if len(salary_range) == 2 else [0, 0]

                    # Update database
                    cur.execute(f"""
                        UPDATE "{POSTGRESQL_TABLE}"
                        SET "MinSalary" = %s,
                            "MaxSalary" = %s,
                            "UpdatedAt" = %s
                        WHERE "Id" = %s
                    """, (min_salary, max_salary, datetime.now(), job_id))

                    conn.commit()
                    print(f"Job {job_id} - Database updated successfully: Min={min_salary}, Max={max_salary}")

                except Exception as e:
                    error_count += 1
                    print(f"Job {job_id} - Error in main processing loop: {str(e)}")
                    conn.rollback()
                    continue

    except Exception as e:
        print(f"Critical error in main: {str(e)}")
        conn.rollback()
    finally:
        print(f"\nProcessing complete:")
        print(f"Total jobs: {total_jobs}")
        print(f"Processed: {processed_count}")
        print(f"Errors: {error_count}")
        if processed_count > 0:
            print(f"Success rate: {((processed_count - error_count) / processed_count * 100):.2f}%")
        conn.close()


if __name__ == "__main__":
    main()
