"""
AI Analysis module configuration.
"""

from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class AnalysisType(Enum):
    """Types of AI analysis available"""
    TECH_STACK = "tech_stack"
    SALARY = "salary"
    ALL = "all"


@dataclass
class AIAnalysisConfig:
    """Configuration for AI analysis"""

    # Analysis types to run
    analysis_types: List[AnalysisType] = None  # None means ALL

    # Processing options
    batch_size: int = 100  # Process jobs in batches
    limit: Optional[int] = None  # Max jobs to process (None = no limit)

    # Filtering
    region_filter: Optional[str] = None  # Filter by region
    only_missing: bool = True  # Only process jobs missing analysis

    # Output
    region: Optional[str] = None  # Region for output organization

    def __post_init__(self):
        if self.analysis_types is None:
            self.analysis_types = [AnalysisType.ALL]

    def should_run_tech_stack(self) -> bool:
        return AnalysisType.ALL in self.analysis_types or AnalysisType.TECH_STACK in self.analysis_types

    def should_run_salary(self) -> bool:
        return AnalysisType.ALL in self.analysis_types or AnalysisType.SALARY in self.analysis_types


# Default configuration
DEFAULT_CONFIG = AIAnalysisConfig()
