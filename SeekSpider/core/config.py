import os

from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

        # Database settings
        self.POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST')
        self.POSTGRESQL_PORT = int(os.getenv('POSTGRESQL_PORT'))
        self.POSTGRESQL_USER = os.getenv('POSTGRESQL_USER')
        self.POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD')
        self.POSTGRESQL_DATABASE = os.getenv('POSTGRESQL_DATABASE')
        self.POSTGRESQL_TABLE = os.getenv('POSTGRESQL_TABLE')

        # SEEK credentials
        self.SEEK_USERNAME = os.getenv('SEEK_USERNAME')
        self.SEEK_PASSWORD = os.getenv('SEEK_PASSWORD')

        # AI API settings
        self.AI_API_KEY = os.getenv('AI_API_KEY')
        self.AI_API_URL = os.getenv('AI_API_URL')
        self.AI_MODEL = os.getenv('AI_MODEL')

    def validate(self):
        required_fields = [
            'POSTGRESQL_HOST',
            'POSTGRESQL_PORT',
            'POSTGRESQL_USER',
            'POSTGRESQL_PASSWORD',
            'POSTGRESQL_DATABASE',
            'POSTGRESQL_TABLE',
            'SEEK_USERNAME',
            'SEEK_PASSWORD',
            'AI_API_KEY',
            'AI_API_URL',
            'AI_MODEL'
        ]

        missing_fields = []
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")


config = Config()
