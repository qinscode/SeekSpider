import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST')
POSTGRESQL_PORT = int(os.getenv('POSTGRESQL_PORT'))
POSTGRESQL_USER = os.getenv('POSTGRESQL_USER')
POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD')
POSTGRESQL_DATABASE = os.getenv('POSTGRESQL_DATABASE')
POSTGRESQL_TABLE = os.getenv('POSTGRESQL_TABLE')

# SEEK Credentials
SEEK_USERNAME = os.getenv('SEEK_USERNAME')
SEEK_PASSWORD = os.getenv('SEEK_PASSWORD')

# AI API Configuration
AI_API_KEY = os.getenv('AI_API_KEY')
AI_API_URL = os.getenv('AI_API_URL')
AI_MODEL = os.getenv('AI_MODEL')