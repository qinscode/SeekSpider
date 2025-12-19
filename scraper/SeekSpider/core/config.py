import os

from dotenv import load_dotenv


class Config:
    def __init__(self):
        load_dotenv()

        # Database settings - support both naming conventions
        self.POSTGRESQL_HOST = os.getenv('POSTGRESQL_HOST') or os.getenv('POSTGRES_HOST')
        port = os.getenv('POSTGRESQL_PORT') or os.getenv('POSTGRES_PORT') or '5432'
        self.POSTGRESQL_PORT = int(port)
        self.POSTGRESQL_USER = os.getenv('POSTGRESQL_USER') or os.getenv('POSTGRES_USER')
        self.POSTGRESQL_PASSWORD = os.getenv('POSTGRESQL_PASSWORD') or os.getenv('POSTGRES_PASSWORD')
        self.POSTGRESQL_DATABASE = os.getenv('POSTGRESQL_DATABASE') or os.getenv('POSTGRES_DB')
        self.POSTGRESQL_TABLE = os.getenv('POSTGRESQL_TABLE', 'seek_jobs')

        # AI API settings (for post-processing)
        # Support multiple API keys separated by comma
        ai_keys = os.getenv('AI_API_KEYS') or os.getenv('AI_API_KEY') or ''
        self.AI_API_KEYS = [k.strip() for k in ai_keys.split(',') if k.strip()]
        self.AI_API_URL = os.getenv('AI_API_URL')
        self.AI_MODEL = os.getenv('AI_MODEL')

    def validate(self):
        """Validate required configuration fields"""
        required_fields = [
            'POSTGRESQL_HOST',
            'POSTGRESQL_PORT',
            'POSTGRESQL_USER',
            'POSTGRESQL_PASSWORD',
            'POSTGRESQL_DATABASE',
            'POSTGRESQL_TABLE',
        ]

        missing_fields = []
        for field in required_fields:
            if not getattr(self, field):
                missing_fields.append(field)

        if missing_fields:
            raise ValueError(f"Missing required configuration: {', '.join(missing_fields)}")

    def validate_ai_config(self):
        """Validate AI configuration for post-processing"""
        missing_fields = []
        if not self.AI_API_KEYS:
            missing_fields.append('AI_API_KEYS')
        if not self.AI_API_URL:
            missing_fields.append('AI_API_URL')
        if not self.AI_MODEL:
            missing_fields.append('AI_MODEL')

        if missing_fields:
            raise ValueError(f"Missing AI configuration: {', '.join(missing_fields)}")

    def has_ai_config(self):
        """Check if AI configuration is available"""
        return bool(self.AI_API_KEYS) and self.AI_API_URL and self.AI_MODEL


config = Config()
