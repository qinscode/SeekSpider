"""
Backfill module configuration and default parameters.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackfillConfig:
    """Configuration for job description backfill"""

    # Processing settings
    delay: float = 5.0  # Base delay between requests in seconds
    workers: int = 3  # Number of concurrent workers (1-5)
    limit: Optional[int] = None  # Maximum jobs to process (None = no limit)

    # Browser settings
    headless: bool = False  # Run browser in headless mode (False for better success)
    use_xvfb: bool = True  # Use virtual display (Xvfb)

    # Driver management
    restart_interval: int = 30  # Restart driver every N jobs (serial mode only)
    max_consecutive_failures: int = 3  # Max failures before driver restart
    max_job_retries: int = 2  # Max retries for a single job
    page_load_timeout: int = 60  # Page load timeout in seconds

    # Filtering
    region_filter: Optional[str] = None  # Filter jobs by region
    include_inactive: bool = False  # Include inactive jobs

    # AI settings
    enable_async_ai: bool = True  # Enable async AI analysis
    skip_ai_post: bool = False  # Skip AI analysis after backfill

    # Output
    region: Optional[str] = None  # Region for output organization

    def validate(self):
        """Validate configuration values"""
        if self.workers < 1 or self.workers > 5:
            raise ValueError("workers must be between 1 and 5")
        if self.delay < 0.5 or self.delay > 30.0:
            raise ValueError("delay must be between 0.5 and 30.0")
        if self.restart_interval < 5 or self.restart_interval > 100:
            raise ValueError("restart_interval must be between 5 and 100")
        if self.limit is not None and self.limit < 1:
            raise ValueError("limit must be at least 1")


# Default configuration instance
DEFAULT_CONFIG = BackfillConfig()
