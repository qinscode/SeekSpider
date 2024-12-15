import json
import time
import requests
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime
from SeekSpider.config import (
    POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_USER,
    POSTGRESQL_PASSWORD, POSTGRESQL_DATABASE,
    AI_API_KEY, AI_API_URL, AI_MODEL
)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY = 60  # Wait 60 seconds when quota exceeded

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
                        "role": "user",
                        "content": f"{prompt}\n\nInput text: {job_description}"
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

            # 解析响应
            response_json = response.json()
            print(f"Job {job_id} - Full API response: {response_json}")

            # 从响应中获取content
            response_text = response_json['choices'][0]['message']['content']
            print(f"Job {job_id} - Raw content: {response_text}")

            # 清理并解析响应
            tech_stack = clean_api_response(response_text)
            print(f"Job {job_id} - Parsed tech stack: {tech_stack}")

            # 添加token使用统计
            tokens = response_json['usage']
            print(f"Job {job_id} - Tokens used: {tokens}")

            # Validate that we got a list
            if not isinstance(tech_stack, list):
                print(f"Job {job_id} - Warning: Invalid response format. Got {type(tech_stack)}")
                return []

            return tech_stack

        except Exception as e:
            error_message = str(e)
            print(f"Job {job_id} - Error processing: {error_message}")
            if attempt < retries - 1:
                print(f"Job {job_id} - Retrying... ({attempt + 1}/{retries})")
                time.sleep(5)  # 简单错误的重试间隔短一些
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
            cur.execute("""
                SELECT "Id", "JobDescription" 
                FROM "Jobs" 
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

                    # Extract tech stack
                    tech_stack = extract_tech_stack(prompt, description, job_id)

                    # Update database
                    cur.execute("""
                        UPDATE "Jobs"
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