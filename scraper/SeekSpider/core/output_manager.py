"""
Output management utilities for SeekSpider.

Handles:
- Directory structure by region
- Automatic archiving of old outputs
- Centralized output path management
"""

import os
import shutil
from datetime import datetime
from typing import Optional

# Default base output directory
DEFAULT_OUTPUT_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
    'output'
)

# Maximum number of folders before archiving
MAX_FOLDERS_BEFORE_ARCHIVE = 7


class OutputManager:
    """Manages output directories with region support and auto-archiving."""

    def __init__(self, output_type: str, region: Optional[str] = None, base_path: Optional[str] = None):
        """
        Initialize output manager.

        Args:
            output_type: Type of output ('seek_spider' or 'backfill_logs')
            region: Region name (e.g., 'Sydney', 'Perth'). If None, no region subdirectory.
            base_path: Base output path. Defaults to project_root/output
        """
        self.output_type = output_type
        self.region = region
        self.base_path = base_path or os.getenv('OUTPUT_PATH', DEFAULT_OUTPUT_BASE)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Build directory path
        self.type_dir = os.path.join(self.base_path, output_type)
        self.timestamp_dir = os.path.join(self.type_dir, self.timestamp)

        if region:
            self.output_dir = os.path.join(self.timestamp_dir, region.lower())
        else:
            self.output_dir = self.timestamp_dir

        self.archive_dir = os.path.join(self.base_path, 'archived', output_type)

    def setup(self) -> str:
        """
        Create output directory and run archiving if needed.

        Returns:
            Path to the output directory
        """
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Check and archive old directories
        self._archive_old_directories()

        return self.output_dir

    def get_file_path(self, filename: str) -> str:
        """Get full path for a file in the output directory."""
        return os.path.join(self.output_dir, filename)

    def _archive_old_directories(self):
        """Archive old directories if count exceeds threshold."""
        if not os.path.exists(self.type_dir):
            return

        # Get all timestamp directories (excluding 'archived')
        dirs = []
        for name in os.listdir(self.type_dir):
            dir_path = os.path.join(self.type_dir, name)
            if os.path.isdir(dir_path) and name != 'archived':
                # Get modification time
                mtime = os.path.getmtime(dir_path)
                dirs.append((name, dir_path, mtime))

        # Sort by modification time (oldest first)
        dirs.sort(key=lambda x: x[2])

        # Archive excess directories
        excess_count = len(dirs) - MAX_FOLDERS_BEFORE_ARCHIVE
        if excess_count > 0:
            os.makedirs(self.archive_dir, exist_ok=True)

            for name, dir_path, _ in dirs[:excess_count]:
                archive_path = os.path.join(self.archive_dir, name)

                # If already exists in archive, add suffix
                if os.path.exists(archive_path):
                    archive_path = f"{archive_path}_{int(datetime.now().timestamp())}"

                try:
                    shutil.move(dir_path, archive_path)
                    print(f"Archived: {dir_path} -> {archive_path}")
                except Exception as e:
                    print(f"Failed to archive {dir_path}: {e}")

    @classmethod
    def archive_all(cls, base_path: Optional[str] = None):
        """
        Run archiving for all output types.

        Args:
            base_path: Base output path. Defaults to project_root/output
        """
        base = base_path or os.getenv('OUTPUT_PATH', DEFAULT_OUTPUT_BASE)

        for output_type in ['seek_spider', 'backfill_logs']:
            manager = cls(output_type=output_type, base_path=base)
            manager._archive_old_directories()


def get_csv_file_path(region: Optional[str] = None, base_path: Optional[str] = None) -> str:
    """
    Get CSV file path for backfill logging.

    Args:
        region: Region name (optional)
        base_path: Base output path (optional)

    Returns:
        Full path to CSV file
    """
    manager = OutputManager('backfill_logs', region=region, base_path=base_path)
    manager.setup()
    return manager.get_file_path(f'backfill_{manager.timestamp}.csv')


def get_log_file_path(output_type: str, region: Optional[str] = None, base_path: Optional[str] = None) -> str:
    """
    Get log file path.

    Args:
        output_type: Type of output ('seek_spider' or 'backfill_logs')
        region: Region name (optional)
        base_path: Base output path (optional)

    Returns:
        Full path to log file
    """
    manager = OutputManager(output_type, region=region, base_path=base_path)
    manager.setup()

    if output_type == 'backfill_logs':
        return manager.get_file_path(f'backfill_{manager.timestamp}.log')
    else:
        return manager.get_file_path('spider.log')
