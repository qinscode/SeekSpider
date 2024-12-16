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
    """Load the prompt from prompt.txt file"""
    # Get the directory of the current file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(current_dir, 'prompt.txt')

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
        return []


def extract_tech_stack(prompt, job_description, job_id, retries=MAX_RETRIES):
    """Extract technology stack from job description using DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {AI_API_KEY}",
        "Content-Type": "application/json"
    }

    for attempt in range(retries):
        try:
            payload = {
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": f"{prompt}"

                    },
                    {
                        "role": "user",
                        "content": f"Extract the technology stack from the following job description:\n\n {job_description}"
                    }
                ],
                "stream": False,
                "response_format": {"type": "text"}
            }

            print(f"\nJob {job_id} - Calling DeepSeek API...")
            response = requests.post(AI_API_URL, json=payload, headers=headers)

            if response.status_code != 200:
                print(f"Job {job_id} - API error: {response.status_code} - {response.text}")
                if response.status_code == 429:  # Rate limit
                    if attempt < retries - 1:
                        print(
                            f"Job {job_id} - Rate limited. Waiting {RETRY_DELAY} seconds before retry {attempt + 1}/{retries}")
                        time.sleep(RETRY_DELAY)
                        continue
                return []

            response_json = response.json()
            print(f"Job {job_id} - Full API response: {response_json}")

            response_text = response_json['choices'][0]['message']['content']
            print(f"Job {job_id} - Raw content: {response_text}")

            tech_stack = clean_api_response(response_text)
            print(f"Job {job_id} - Parsed tech stack: {tech_stack}")

            tokens = response_json['usage']
            print(f"Job {job_id} - Tokens used: {tokens}")

            if not isinstance(tech_stack, list):
                print(f"Job {job_id} - Warning: Invalid response format. Got {type(tech_stack)}")
                return []

            return tech_stack

        except Exception as e:
            error_message = str(e)
            print(f"Job {job_id} - Error processing: {error_message}")
            if attempt < retries - 1:
                print(f"Job {job_id} - Retrying... ({attempt + 1}/{retries})")
                time.sleep(5)
                continue
            return []

    return []


def main():
    # Initialize components
    prompt = load_prompt()
    conn = get_db_connection()

    processed_count = 0
    error_count = 0
    total_tokens = 0

    try:
        with conn.cursor() as cur:
            # Get all jobs that don't have tech stack processed
            cur.execute(f"""
                SELECT "Id", "JobDescription" 
                FROM "{POSTGRESQL_TABLE}" 
                WHERE "TechStack" IS NULL 
                AND "JobDescription" IS NOT NULL
            """)

            jobs = cur.fetchall()
            total_jobs = len(jobs)
            print(f"Found {total_jobs} jobs to process")

            for job_id, description in jobs:
                try:
                    processed_count += 1
                    print(f"\n[{processed_count}/{total_jobs}] Processing job {job_id}...")

                    tech_stack = extract_tech_stack(prompt, description, job_id)

                    cur.execute(f"""
                        UPDATE "{POSTGRESQL_TABLE}"
                        SET "TechStack" = %s,
                            "UpdatedAt" = %s
                        WHERE "Id" = %s
                    """, (json.dumps(tech_stack), datetime.now(), job_id))

                    conn.commit()
                    print(f"Job {job_id} - Database updated successfully")

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
        print(f"Total tokens used: {total_tokens}")
        conn.close()


if __name__ == "__main__":
    main()
