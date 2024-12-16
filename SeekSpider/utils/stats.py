import psycopg2
from collections import Counter
import re
from typing import List, Dict
from datetime import datetime
from SeekSpider.config import (
    POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_USER,
    POSTGRESQL_PASSWORD, POSTGRESQL_DATABASE
)

def log_message(message: str):
    """Print log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def connect_to_db() -> psycopg2.extensions.connection:
    """Connect to PostgreSQL database"""
    try:
        log_message("Connecting to database...")
        conn = psycopg2.connect(
            host=POSTGRESQL_HOST,
            port=POSTGRESQL_PORT,
            user=POSTGRESQL_USER,
            password=POSTGRESQL_PASSWORD,
            database=POSTGRESQL_DATABASE
        )
        log_message("Database connection successful")
        return conn
    except Exception as e:
        log_message(f"Database connection error: {e}")
        raise

def normalize_tech_name(tech: str) -> str:
    """Normalize technology stack names"""
    # Remove whitespace
    tech = tech.strip()

    # List of invalid or meaningless technology names to filter out
    filter_list = {
        '',  # empty string
        ' ',  # space
        'etc',
        'etc.',
        'Etc',
        'Etc.',
        'others',
        'Others',
        'Other',
        'other',
        'and',
        'And',
        'more',
        'More',
        '-',
        '.',
        '...',
        'N/A',
        'n/a',
        'NA',
        'na',
        'None',
        'none',
        'null',
        'Null',
        'NULL',
        'Microsoft'
    }

    # Return None if tech name is in filter list
    if tech in filter_list:
        return None

    # Define technology stack aliases mapping
    tech_aliases = {
        'React.js': 'React',
        'ReactJS': 'React',
        'React.JS': 'React',
        'Microsoft 365': 'Office 365',
        'MS 365': 'Office 365',
        'Microsoft Office 365': 'Office 365',
        'Javascript': 'JavaScript',
        'javascript': 'JavaScript',
        'TypeScript': 'TypeScript',
        'typescript': 'TypeScript',
        'Vue.js': 'Vue',
        'VueJS': 'Vue',
        'Node.js': 'Node.js',
        'NodeJS': 'Node.js',
        'Nodejs': 'Node.js',
        'AWS': 'AWS',
        'Amazon AWS': 'AWS',
        'Amazon Web Services': 'AWS',
    }

    # Return normalized name
    return tech_aliases.get(tech, tech)

def get_tech_stack_data() -> List[str]:
    """Get TechStack text data from database and convert to array"""
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            log_message("Starting TechStack data query...")
            cur.execute("""
                SELECT unnest(string_to_array("TechStack", ',')) 
                FROM "Jobs" 
                WHERE "TechStack" IS NOT NULL
                    AND "TechStack" != ''
            """)
            # Clean and normalize data
            results = []
            skipped_count = 0
            for row in cur.fetchall():
                if row[0]:  # Ensure not None
                    tech = row[0].strip().strip('[]"\'')
                    if tech:  # Ensure not empty string
                        normalized_tech = normalize_tech_name(tech)
                        if normalized_tech:  # Ensure normalized result not None
                            results.append(normalized_tech)
                        else:
                            skipped_count += 1

            log_message(f"Successfully retrieved {len(results)} valid tech stack records")
            log_message(f"Filtered out {skipped_count} invalid records")
            return results
    finally:
        conn.close()
        log_message("Database connection closed")

def calculate_word_frequency() -> Dict[str, int]:
    """Calculate word frequency statistics"""
    log_message("Starting word frequency calculation...")
    tech_stacks = get_tech_stack_data()

    # Print first 10 sample records
    log_message("Data samples (first 10):")
    for i, tech in enumerate(tech_stacks[:10]):
        print(f"    {i + 1}. {tech}")

    word_freq = Counter(tech_stacks)
    log_message(f"Word frequency calculation complete, found {len(word_freq)} unique tech stacks")
    return dict(word_freq.most_common())

def save_word_frequency(word_freq: Dict[str, int]) -> None:
    """Save word frequency results to database (top 200 most common tech stacks only)"""
    conn = connect_to_db()
    try:
        with conn.cursor() as cur:
            log_message("Creating/updating word frequency table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tech_word_frequency (
                    word VARCHAR(255) PRIMARY KEY,
                    frequency INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Clear existing data
            log_message("Clearing existing word frequency data...")
            cur.execute("TRUNCATE TABLE tech_word_frequency")

            # Take only top 200 most common tech stacks
            top_200_techs = dict(list(word_freq.items())[:200])

            log_message(f"Starting to save top 200 most common tech stacks...")
            count = 0
            for word, freq in top_200_techs.items():
                cur.execute("""
                    INSERT INTO tech_word_frequency (word, frequency)
                    VALUES (%s, %s)
                """, (word, freq))
                count += 1
                if count % 20 == 0:  # Print progress every 20 records
                    log_message(f"Processed {count}/200 records")

            conn.commit()
            log_message(f"Successfully saved top 200 tech stack frequency data")
    finally:
        conn.close()

def main():
    """Main function"""
    try:
        log_message("Starting tech stack frequency analysis...")

        word_frequency = calculate_word_frequency()
        save_word_frequency(word_frequency)

        log_message("\nTop 20 most common tech stacks:")
        for i, (word, count) in enumerate(list(word_frequency.items())[:20], 1):
            print(f"{i:2d}. {word:<30} : {count:5d}")

        total_techs = len(word_frequency)
        log_message(f"\nAnalysis Summary:")
        log_message(f"- Found {total_techs} unique tech stacks")
        log_message(f"- Saved top 200 most common tech stacks to database")
        log_message(f"- Unsaved tech stacks: {max(0, total_techs - 200)}")

        log_message("Program execution completed")

    except Exception as e:
        log_message(f"Program execution error: {e}")
        raise

if __name__ == "__main__":
    main()
