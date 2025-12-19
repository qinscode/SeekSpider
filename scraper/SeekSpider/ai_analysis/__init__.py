"""
AI Analysis module for analyzing job descriptions.

This module provides tools for:
- Tech Stack analysis: Extract technologies from job descriptions
- Salary Normalization: Convert salary ranges to annual amounts

Usage:
    # As a module
    from ai_analysis import AIAnalyzer, AIAnalysisConfig, AnalysisType

    config = AIAnalysisConfig(
        analysis_types=[AnalysisType.ALL],
        region_filter='Sydney'
    )
    analyzer = AIAnalyzer(config)
    analyzer.run()

    # As a CLI command
    python -m ai_analysis --region Sydney --type all
"""

from .config import AIAnalysisConfig, AnalysisType, DEFAULT_CONFIG
from .core import AIAnalyzer, AsyncAIAnalyzer

__all__ = [
    'AIAnalyzer',
    'AsyncAIAnalyzer',
    'AIAnalysisConfig',
    'AnalysisType',
    'DEFAULT_CONFIG',
]

__version__ = '1.0.0'
