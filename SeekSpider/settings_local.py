import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST')
POSTGRESQL_PORT = int(os.getenv('POSTGRESQL_PORT'))
POSTGRESQL_USER = os.getenv('POSTGRESQL_USER')
POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD')
POSTGRESQL_DATABASE = os.getenv('POSTGRESQL_DATABASE')
POSTGRESQL_TABLE = os.getenv('POSTGRESQL_TABLE')

# SEEK credentials
SEEK_USERNAME = os.getenv('SEEK_USERNAME')
SEEK_PASSWORD = os.getenv('SEEK_PASSWORD')