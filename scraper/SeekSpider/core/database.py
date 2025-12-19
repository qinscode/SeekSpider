from contextlib import contextmanager

import psycopg2


class DatabaseManager:
    def __init__(self, config):

        self.config = config
        self.logger = None

    def set_logger(self, logger):
        self.logger = logger

    def log(self, level, msg):
        if self.logger:
            getattr(self.logger, level)(msg)

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = psycopg2.connect(
                host=self.config.POSTGRESQL_HOST,
                port=self.config.POSTGRESQL_PORT,
                user=self.config.POSTGRESQL_USER,
                password=self.config.POSTGRESQL_PASSWORD,
                database=self.config.POSTGRESQL_DATABASE
            )
            # Set timezone to Perth for all timestamp operations
            with conn.cursor() as cur:
                cur.execute("SET timezone = 'Australia/Perth'")
            self.log('debug', 'Database connection established (timezone: Australia/Perth)')
            yield conn
        except Exception as e:
            self.log('error', f'Database connection error: {str(e)}')
            raise
        finally:
            if conn:
                conn.close()
                self.log('debug', 'Database connection closed')

    @contextmanager
    def get_cursor(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                conn.commit()
            except Exception as e:
                self.log('error', f'Database operation error: {str(e)}')
                conn.rollback()
                raise
            finally:
                cursor.close()

    def execute_query(self, query, params=None):
        with self.get_cursor() as cur:
            try:
                cur.execute(query, params or ())
                return cur.fetchall()
            except Exception as e:
                self.log('error', f'Query execution error: {str(e)}')
                raise

    def execute_update(self, query, params=None):
        with self.get_cursor() as cur:
            try:
                cur.execute(query, params or ())
                return cur.rowcount
            except Exception as e:
                self.log('error', f'Update execution error: {str(e)}')
                raise

    def get_existing_job_ids(self):
        query = f'SELECT "Id" FROM "{self.config.POSTGRESQL_TABLE}"'
        results = self.execute_query(query)
        return {str(row[0]) for row in results}

    def insert_job(self, job_data):
        columns = ', '.join([f'"{k}"' for k in job_data.keys()])
        placeholders = ', '.join(['%s'] * len(job_data))
        query = f'''
            INSERT INTO "{self.config.POSTGRESQL_TABLE}" ({columns})
            VALUES ({placeholders})
        '''
        self.execute_update(query, list(job_data.values()))
        self.log('info', f'Inserted job with ID: {job_data.get("Id")}')

    def update_job(self, job_id, job_data):
        """
        Update a job record in the database.

        Args:
            job_id: The ID of the job to update
            job_data: Dictionary containing the fields to update

        Returns:
            Number of rows affected (0 if job already had description, 1 if updated)

        Note:
            UpdatedAt field is automatically set to current timestamp,
            do not include it in job_data.
            When updating JobDescription, only updates if current value is empty
            (prevents race conditions in concurrent execution).
        """
        set_clause = ', '.join([f'"{k}" = %s' for k in job_data.keys()])

        # Check if we're updating JobDescription
        if 'JobDescription' in job_data:
            # Add condition to only update if JobDescription is currently empty
            # This is an atomic check-and-set operation at the database level
            query = f'''
                UPDATE "{self.config.POSTGRESQL_TABLE}"
                SET {set_clause}, "UpdatedAt" = now()
                WHERE "Id" = %s
                AND ("JobDescription" IS NULL OR "JobDescription" = '' OR "JobDescription" = 'None')
            '''
        else:
            # For other updates, no special condition needed
            query = f'''
                UPDATE "{self.config.POSTGRESQL_TABLE}"
                SET {set_clause}, "UpdatedAt" = now()
                WHERE "Id" = %s
            '''

        affected = self.execute_update(query, list(job_data.values()) + [job_id])

        if 'JobDescription' in job_data and affected == 0:
            self.log('debug', f'Job {job_id} already has description, skipped update (race condition avoided)')
        else:
            self.log('info', f'Updated job {job_id}, affected rows: {affected}')

        return affected

    def mark_jobs_inactive(self, job_ids):
        if not job_ids:
            return 0

        query = f'''
            UPDATE "{self.config.POSTGRESQL_TABLE}"
            SET "IsActive" = FALSE, 
                "UpdatedAt" = now(),
                "ExpiryDate" = now()
            WHERE "Id" = ANY(%s::integer[])
            AND "IsActive" = TRUE
        '''
        job_ids_int = [int(job_id) for job_id in job_ids]
        affected = self.execute_update(query, (job_ids_int,))
        self.log('info', f'Marked {affected} jobs as inactive')
        return affected

    def get_unprocessed_jobs(self):
        query = f'''
            SELECT "Id", "JobDescription" 
            FROM "{self.config.POSTGRESQL_TABLE}" 
            WHERE "TechStack" IS NULL 
            AND "JobDescription" IS NOT NULL
        '''
        return self.execute_query(query)
