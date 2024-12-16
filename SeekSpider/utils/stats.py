import json
from collections import Counter

from SeekSpider.core.config import config
from SeekSpider.core.database import DatabaseManager
from SeekSpider.core.logger import Logger


class TechStatsAnalyzer:
    def __init__(self, db_manager, logger):
        self.db = db_manager
        self.logger = logger

    def _normalize_tech_name(self, tech):
        """Normalize technology stack names"""
        if not tech:
            return None

        # Remove whitespace
        tech = tech.strip()

        # Filter out invalid or meaningless names
        filter_list = {
            '', ' ', 'etc', 'etc.', 'Etc', 'Etc.',
            'others', 'Others', 'Other', 'other',
            'and', 'And', 'more', 'More',
            '-', '.', '...', 'N/A', 'n/a', 'NA', 'na',
            'None', 'none', 'null', 'Null', 'NULL',
            'Microsoft'
        }

        if tech in filter_list:
            return None

        # Technology aliases mapping
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
            '.NET': '.Net'
        }

        return tech_aliases.get(tech, tech)

    def _get_tech_stack_data(self):
        """Get and clean tech stack data from database"""
        try:
            query = f'''
                SELECT "Id", "TechStack"
                FROM "{self.db.config.POSTGRESQL_TABLE}"
                WHERE "TechStack" IS NOT NULL
                AND "TechStack" != ''
                AND "IsActive" = TRUE
            '''
            jobs = self.db.execute_query(query)

            tech_stacks = []
            skipped = 0

            for job_id, tech_stack in jobs:
                try:
                    # Parse JSON array
                    techs = json.loads(tech_stack)
                    if not isinstance(techs, list):
                        continue

                    # Normalize and filter each tech
                    for tech in techs:
                        normalized = self._normalize_tech_name(tech)
                        if normalized:
                            tech_stacks.append(normalized)
                        else:
                            skipped += 1

                except json.JSONDecodeError:
                    self.logger.warning(f"Invalid JSON in tech stack for job {job_id}")
                    continue

            self.logger.info(f"Processed {len(jobs)} jobs")
            self.logger.info(f"Found {len(tech_stacks)} valid technologies")
            self.logger.info(f"Skipped {skipped} invalid entries")

            return tech_stacks

        except Exception as e:
            self.logger.error(f"Error getting tech stack data: {str(e)}")
            raise

    def _calculate_frequencies(self, tech_stacks):
        """Calculate technology frequency statistics"""
        try:
            # Get word frequencies
            word_freq = Counter(tech_stacks)

            # Convert to sorted list of tuples
            freq_list = word_freq.most_common()

            self.logger.info(f"Found {len(freq_list)} unique technologies")
            return freq_list

        except Exception as e:
            self.logger.error(f"Error calculating frequencies: {str(e)}")
            raise

    def _save_frequencies(self, frequencies):
        """Save frequency results to database"""
        try:
            # Create/update frequency table
            create_table_query = '''
                CREATE TABLE IF NOT EXISTS tech_word_frequency (
                    word VARCHAR(255) PRIMARY KEY,
                    frequency INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            self.db.execute_update(create_table_query)

            # Clear existing data
            self.db.execute_update("TRUNCATE TABLE tech_word_frequency")

            # Insert new frequencies (top 200 only)
            for word, freq in frequencies[:200]:
                query = '''
                    INSERT INTO tech_word_frequency (word, frequency)
                    VALUES (%s, %s)
                '''
                self.db.execute_update(query, (word, freq))

            self.logger.info(f"Saved top 200 technology frequencies")

        except Exception as e:
            self.logger.error(f"Error saving frequencies: {str(e)}")
            raise

    def process_all_jobs(self):
        """Run complete technology stack analysis"""
        try:
            self.logger.info("Starting technology stack analysis...")

            # Get and clean data
            tech_stacks = self._get_tech_stack_data()

            # Calculate frequencies
            frequencies = self._calculate_frequencies(tech_stacks)

            # Save results
            self._save_frequencies(frequencies)

            # Log top technologies
            self.logger.info("\nTop 20 Technologies:")
            for i, (tech, count) in enumerate(frequencies[:20], 1):
                self.logger.info(f"{i:2d}. {tech:<30} : {count:5d}")

            self.logger.info("\nAnalysis complete")

        except Exception as e:
            self.logger.error(f"Critical error in tech stack analysis: {str(e)}")
            raise


def main():
    """Main entry point for technology stack analysis"""
    try:
        # Initialize components
        logger = Logger('tech_stats_analyzer')
        db = DatabaseManager(config)
        db.set_logger(logger)

        # Create analyzer and process jobs
        analyzer = TechStatsAnalyzer(db, logger)
        analyzer.process_all_jobs()

    except Exception as e:
        logger.error(f"Failed to run tech stack analysis: {str(e)}")
        raise


if __name__ == "__main__":
    main()
