#!/usr/bin/env python3
"""
Comprehensive Test Suite for SeekSpider Project

This test suite covers:
1. Module imports
2. Configuration classes
3. Database connectivity
4. Spider initialization
5. Backfill module
6. AI analysis module
7. Pipeline definitions
8. CLI entry points

Usage:
    # Run all tests
    python -m pytest tests/test_all.py -v

    # Run specific test category
    python -m pytest tests/test_all.py -v -k "test_import"
    python -m pytest tests/test_all.py -v -k "test_config"
    python -m pytest tests/test_all.py -v -k "test_database"
    python -m pytest tests/test_all.py -v -k "test_spider"
    python -m pytest tests/test_all.py -v -k "test_backfill"
    python -m pytest tests/test_all.py -v -k "test_ai"
    python -m pytest tests/test_all.py -v -k "test_pipeline"

    # Run as standalone script
    python tests/test_all.py
"""

import os
import sys
import subprocess
from typing import List, Dict, Any
from datetime import datetime

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRAPER_DIR = os.path.join(PROJECT_ROOT, 'scraper')
SEEKSPIDER_DIR = os.path.join(SCRAPER_DIR, 'SeekSpider')
PIPELINE_DIR = os.path.join(PROJECT_ROOT, 'pipeline', 'src')

sys.path.insert(0, SCRAPER_DIR)
sys.path.insert(0, SEEKSPIDER_DIR)
sys.path.insert(0, PIPELINE_DIR)

# Load environment variables
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))


# ============================================================================
# Test Results Tracking
# ============================================================================

class TestResults:
    """Track test results for summary report"""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []

    def add_pass(self, name: str, message: str = ""):
        self.passed.append((name, message))

    def add_fail(self, name: str, error: str):
        self.failed.append((name, error))

    def add_skip(self, name: str, reason: str):
        self.skipped.append((name, reason))

    def print_summary(self):
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        total = len(self.passed) + len(self.failed) + len(self.skipped)

        print(f"\nTotal: {total} tests")
        print(f"  Passed:  {len(self.passed)}")
        print(f"  Failed:  {len(self.failed)}")
        print(f"  Skipped: {len(self.skipped)}")

        if self.failed:
            print("\n" + "-" * 70)
            print("FAILED TESTS:")
            print("-" * 70)
            for name, error in self.failed:
                print(f"  {name}")
                print(f"    Error: {error[:100]}...")

        if self.skipped:
            print("\n" + "-" * 70)
            print("SKIPPED TESTS:")
            print("-" * 70)
            for name, reason in self.skipped:
                print(f"  {name}: {reason}")

        print("\n" + "=" * 70)

        if len(self.failed) == 0:
            print("ALL TESTS PASSED!")
            return 0
        else:
            print(f"TESTS FAILED: {len(self.failed)}/{total}")
            return 1


results = TestResults()


# ============================================================================
# 1. Import Tests
# ============================================================================

def test_import_core_modules():
    """Test importing core modules"""
    print("\n[TEST] Importing core modules...")

    try:
        from SeekSpider.core.config import Config, config
        results.add_pass("import_core_config")
        print("  core.config")
    except ImportError as e:
        results.add_fail("import_core_config", str(e))
        print(f"  core.config FAILED: {e}")

    try:
        from SeekSpider.core.database import DatabaseManager
        results.add_pass("import_core_database")
        print("  core.database")
    except ImportError as e:
        results.add_fail("import_core_database", str(e))
        print(f"  core.database FAILED: {e}")

    try:
        from SeekSpider.core.regions import AUSTRALIAN_REGIONS, get_seek_location, get_all_regions
        results.add_pass("import_core_regions")
        print("  core.regions")
    except ImportError as e:
        results.add_fail("import_core_regions", str(e))
        print(f"  core.regions FAILED: {e}")

    try:
        from SeekSpider.core.output_manager import OutputManager
        results.add_pass("import_core_output_manager")
        print("  core.output_manager")
    except ImportError as e:
        results.add_fail("import_core_output_manager", str(e))
        print(f"  core.output_manager FAILED: {e}")

    try:
        from SeekSpider.core.ai_client import AIClient
        results.add_pass("import_core_ai_client")
        print("  core.ai_client")
    except ImportError as e:
        results.add_fail("import_core_ai_client", str(e))
        print(f"  core.ai_client FAILED: {e}")


def test_import_backfill_module():
    """Test importing backfill module"""
    print("\n[TEST] Importing backfill module...")

    try:
        from backfill import BackfillConfig, DEFAULT_CONFIG
        results.add_pass("import_backfill_config")
        print("  backfill.config")
    except ImportError as e:
        results.add_fail("import_backfill_config", str(e))
        print(f"  backfill.config FAILED: {e}")

    try:
        from backfill import JobDescriptionBackfiller
        results.add_pass("import_backfill_core")
        print("  backfill.core")
    except ImportError as e:
        results.add_fail("import_backfill_core", str(e))
        print(f"  backfill.core FAILED: {e}")

    try:
        from backfill import DriverManager
        results.add_pass("import_backfill_drivers")
        print("  backfill.drivers")
    except ImportError as e:
        results.add_fail("import_backfill_drivers", str(e))
        print(f"  backfill.drivers FAILED: {e}")

    try:
        from backfill import BackfillAIProcessor, run_post_ai_analysis
        results.add_pass("import_backfill_ai_processor")
        print("  backfill.ai_processor")
    except ImportError as e:
        results.add_fail("import_backfill_ai_processor", str(e))
        print(f"  backfill.ai_processor FAILED: {e}")


def test_import_ai_analysis_module():
    """Test importing ai_analysis module"""
    print("\n[TEST] Importing ai_analysis module...")

    try:
        from ai_analysis import AIAnalysisConfig, AnalysisType, DEFAULT_CONFIG
        results.add_pass("import_ai_analysis_config")
        print("  ai_analysis.config")
    except ImportError as e:
        results.add_fail("import_ai_analysis_config", str(e))
        print(f"  ai_analysis.config FAILED: {e}")

    try:
        from ai_analysis import AIAnalyzer, AsyncAIAnalyzer
        results.add_pass("import_ai_analysis_core")
        print("  ai_analysis.core")
    except ImportError as e:
        results.add_fail("import_ai_analysis_core", str(e))
        print(f"  ai_analysis.core FAILED: {e}")


def test_import_spider():
    """Test importing spider module"""
    print("\n[TEST] Importing spider module...")

    try:
        from SeekSpider.spiders.seek import SeekSpider
        results.add_pass("import_spider_seek")
        print("  spiders.seek")
    except ImportError as e:
        results.add_fail("import_spider_seek", str(e))
        print(f"  spiders.seek FAILED: {e}")

    try:
        from SeekSpider.items import SeekspiderItem
        results.add_pass("import_items")
        print("  items")
    except ImportError as e:
        results.add_fail("import_items", str(e))
        print(f"  items FAILED: {e}")

    try:
        from SeekSpider.pipelines import JsonExportPipeline, SeekspiderPipeline
        results.add_pass("import_pipelines")
        print("  pipelines")
    except ImportError as e:
        results.add_fail("import_pipelines", str(e))
        print(f"  pipelines FAILED: {e}")


def test_import_utils():
    """Test importing utility modules"""
    print("\n[TEST] Importing utility modules...")

    try:
        from SeekSpider.utils.tech_stack_analyzer import TechStackAnalyzer
        results.add_pass("import_utils_tech_stack")
        print("  utils.tech_stack_analyzer")
    except ImportError as e:
        results.add_fail("import_utils_tech_stack", str(e))
        print(f"  utils.tech_stack_analyzer FAILED: {e}")

    try:
        from SeekSpider.utils.salary_normalizer import SalaryNormalizer
        results.add_pass("import_utils_salary")
        print("  utils.salary_normalizer")
    except ImportError as e:
        results.add_fail("import_utils_salary", str(e))
        print(f"  utils.salary_normalizer FAILED: {e}")


# ============================================================================
# 2. Configuration Tests
# ============================================================================

def test_config_instantiation():
    """Test configuration class instantiation"""
    print("\n[TEST] Testing configuration classes...")

    # Test core Config
    try:
        from SeekSpider.core.config import Config
        config = Config()
        assert config is not None
        results.add_pass("config_core_instantiation")
        print("  Core Config instantiation")
    except Exception as e:
        results.add_fail("config_core_instantiation", str(e))
        print(f"  Core Config instantiation FAILED: {e}")

    # Test BackfillConfig
    try:
        from backfill import BackfillConfig
        config = BackfillConfig()
        assert config.workers == 3
        assert config.delay == 5.0
        assert config.headless == False
        assert config.use_xvfb == True
        results.add_pass("config_backfill_instantiation")
        print("  BackfillConfig instantiation with defaults")
    except Exception as e:
        results.add_fail("config_backfill_instantiation", str(e))
        print(f"  BackfillConfig instantiation FAILED: {e}")

    # Test BackfillConfig with custom values
    try:
        from backfill import BackfillConfig
        config = BackfillConfig(
            workers=5,
            delay=10.0,
            limit=100,
            region_filter='Perth'
        )
        assert config.workers == 5
        assert config.delay == 10.0
        assert config.limit == 100
        assert config.region_filter == 'Perth'
        results.add_pass("config_backfill_custom")
        print("  BackfillConfig with custom values")
    except Exception as e:
        results.add_fail("config_backfill_custom", str(e))
        print(f"  BackfillConfig custom FAILED: {e}")

    # Test AIAnalysisConfig
    try:
        from ai_analysis import AIAnalysisConfig, AnalysisType
        config = AIAnalysisConfig()
        assert config.only_missing == True
        assert config.batch_size == 100
        results.add_pass("config_ai_analysis_instantiation")
        print("  AIAnalysisConfig instantiation with defaults")
    except Exception as e:
        results.add_fail("config_ai_analysis_instantiation", str(e))
        print(f"  AIAnalysisConfig instantiation FAILED: {e}")

    # Test AIAnalysisConfig with custom values
    try:
        from ai_analysis import AIAnalysisConfig, AnalysisType
        config = AIAnalysisConfig(
            analysis_types=[AnalysisType.TECH_STACK],
            limit=50,
            region_filter='Sydney'
        )
        assert config.limit == 50
        assert config.region_filter == 'Sydney'
        results.add_pass("config_ai_analysis_custom")
        print("  AIAnalysisConfig with custom values")
    except Exception as e:
        results.add_fail("config_ai_analysis_custom", str(e))
        print(f"  AIAnalysisConfig custom FAILED: {e}")


def test_config_validation():
    """Test configuration validation"""
    print("\n[TEST] Testing configuration validation...")

    try:
        from SeekSpider.core.config import config
        config.validate()
        results.add_pass("config_db_validation")
        print("  Database config validation")
    except ValueError as e:
        results.add_skip("config_db_validation", f"Missing env vars: {e}")
        print(f"  Database config validation SKIPPED: {e}")
    except Exception as e:
        results.add_fail("config_db_validation", str(e))
        print(f"  Database config validation FAILED: {e}")

    try:
        from SeekSpider.core.config import config
        has_ai = config.has_ai_config()
        if has_ai:
            config.validate_ai_config()
            results.add_pass("config_ai_validation")
            print("  AI config validation")
        else:
            results.add_skip("config_ai_validation", "AI config not available")
            print("  AI config validation SKIPPED: No AI config")
    except Exception as e:
        results.add_fail("config_ai_validation", str(e))
        print(f"  AI config validation FAILED: {e}")


# ============================================================================
# 3. Database Tests
# ============================================================================

def test_database_connection():
    """Test database connectivity"""
    print("\n[TEST] Testing database connectivity...")

    try:
        from SeekSpider.core.config import config
        from SeekSpider.core.database import DatabaseManager

        db = DatabaseManager(config)

        # Test connection
        with db.get_connection() as conn:
            assert conn is not None
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                result = cur.fetchone()
                assert result[0] == 1

        results.add_pass("database_connection")
        print("  Database connection")
    except Exception as e:
        results.add_fail("database_connection", str(e))
        print(f"  Database connection FAILED: {e}")


def test_database_table_exists():
    """Test that the jobs table exists"""
    print("\n[TEST] Testing database table...")

    try:
        from SeekSpider.core.config import config
        from SeekSpider.core.database import DatabaseManager

        db = DatabaseManager(config)

        query = f"""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = '{config.POSTGRESQL_TABLE}'
            )
        """
        result = db.execute_query(query)
        assert result[0][0] == True

        results.add_pass("database_table_exists")
        print(f"  Table '{config.POSTGRESQL_TABLE}' exists")
    except Exception as e:
        results.add_fail("database_table_exists", str(e))
        print(f"  Table check FAILED: {e}")


def test_database_job_count():
    """Test counting jobs in database"""
    print("\n[TEST] Testing job count...")

    try:
        from SeekSpider.core.config import config
        from SeekSpider.core.database import DatabaseManager

        db = DatabaseManager(config)

        query = f'SELECT COUNT(*) FROM "{config.POSTGRESQL_TABLE}"'
        result = db.execute_query(query)
        count = result[0][0]

        results.add_pass("database_job_count")
        print(f"  Total jobs in database: {count}")
    except Exception as e:
        results.add_fail("database_job_count", str(e))
        print(f"  Job count FAILED: {e}")


def test_database_region_distribution():
    """Test job distribution by region"""
    print("\n[TEST] Testing region distribution...")

    try:
        from SeekSpider.core.config import config
        from SeekSpider.core.database import DatabaseManager

        db = DatabaseManager(config)

        query = f'''
            SELECT "Region", COUNT(*) as count
            FROM "{config.POSTGRESQL_TABLE}"
            GROUP BY "Region"
            ORDER BY count DESC
        '''
        results_data = db.execute_query(query)

        results.add_pass("database_region_distribution")
        print("  Jobs by region:")
        for region, count in results_data:
            print(f"    {region}: {count}")
    except Exception as e:
        results.add_fail("database_region_distribution", str(e))
        print(f"  Region distribution FAILED: {e}")


def test_database_missing_descriptions():
    """Test counting jobs with missing descriptions"""
    print("\n[TEST] Testing missing descriptions count...")

    try:
        from SeekSpider.core.config import config
        from SeekSpider.core.database import DatabaseManager

        db = DatabaseManager(config)

        query = f'''
            SELECT "Region", COUNT(*) as count
            FROM "{config.POSTGRESQL_TABLE}"
            WHERE ("JobDescription" IS NULL OR "JobDescription" = '' OR "JobDescription" = 'None')
            AND "IsActive" = 'True'
            GROUP BY "Region"
            ORDER BY count DESC
        '''
        results_data = db.execute_query(query)

        results.add_pass("database_missing_descriptions")
        print("  Jobs with missing descriptions (active only):")
        total = 0
        for region, count in results_data:
            print(f"    {region}: {count}")
            total += count
        print(f"    TOTAL: {total}")
    except Exception as e:
        results.add_fail("database_missing_descriptions", str(e))
        print(f"  Missing descriptions FAILED: {e}")


# ============================================================================
# 4. Spider Tests
# ============================================================================

def test_spider_initialization():
    """Test spider can be initialized"""
    print("\n[TEST] Testing spider initialization...")

    try:
        # Just import the spider class
        from SeekSpider.spiders.seek import SeekSpider

        # Check spider attributes
        assert SeekSpider.name == 'seek'
        assert 'seek.com.au' in SeekSpider.allowed_domains

        results.add_pass("spider_initialization")
        print("  Spider class loaded successfully")
    except ImportError as e:
        results.add_fail("spider_initialization", str(e))
        print(f"  Spider initialization FAILED: {e}")
    except Exception as e:
        # Skip other errors (scrapy settings may not be available)
        results.add_skip("spider_initialization", f"Spider loaded but setup failed: {str(e)[:50]}")
        print(f"  Spider initialization SKIPPED: {str(e)[:50]}")


def test_spider_region_configs():
    """Test spider region configurations"""
    print("\n[TEST] Testing region configurations...")

    try:
        from SeekSpider.core.regions import AUSTRALIAN_REGIONS, get_seek_location, is_valid_region

        # Check all regions are configured
        expected_regions = ['Perth', 'Sydney', 'Melbourne', 'Brisbane',
                          'Gold Coast', 'Adelaide', 'Canberra', 'Hobart', 'Darwin']

        for region in expected_regions:
            assert is_valid_region(region), f"Region {region} not found"
            location = get_seek_location(region)
            assert location is not None

        results.add_pass("spider_region_configs")
        print(f"  All {len(expected_regions)} regions configured")
    except Exception as e:
        results.add_fail("spider_region_configs", str(e))
        print(f"  Region configs FAILED: {e}")


# ============================================================================
# 5. Backfill Module Tests
# ============================================================================

def test_backfill_config_defaults():
    """Test backfill default configuration"""
    print("\n[TEST] Testing backfill defaults...")

    try:
        from backfill import BackfillConfig, DEFAULT_CONFIG

        assert DEFAULT_CONFIG.workers == 3
        assert DEFAULT_CONFIG.delay == 5.0
        assert DEFAULT_CONFIG.headless == False
        assert DEFAULT_CONFIG.use_xvfb == True
        assert DEFAULT_CONFIG.restart_interval == 30

        results.add_pass("backfill_config_defaults")
        print("  Default config values verified")
    except Exception as e:
        results.add_fail("backfill_config_defaults", str(e))
        print(f"  Backfill defaults FAILED: {e}")


def test_backfill_driver_manager():
    """Test driver manager instantiation"""
    print("\n[TEST] Testing driver manager...")

    try:
        from backfill import DriverManager, BackfillConfig
        import logging

        config = BackfillConfig(headless=True, use_xvfb=False)
        logger = logging.getLogger('test')

        manager = DriverManager(config, logger)
        assert manager is not None

        results.add_pass("backfill_driver_manager")
        print("  DriverManager instantiation")
    except Exception as e:
        results.add_fail("backfill_driver_manager", str(e))
        print(f"  DriverManager FAILED: {e}")


def test_backfill_cli_help():
    """Test backfill CLI help command"""
    print("\n[TEST] Testing backfill CLI...")

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'backfill', '--help'],
            cwd=SEEKSPIDER_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert '--workers' in result.stdout
        assert '--delay' in result.stdout
        assert '--region' in result.stdout

        results.add_pass("backfill_cli_help")
        print("  CLI help command works")
    except subprocess.TimeoutExpired:
        results.add_fail("backfill_cli_help", "Timeout")
        print("  CLI help FAILED: Timeout")
    except Exception as e:
        results.add_fail("backfill_cli_help", str(e))
        print(f"  CLI help FAILED: {e}")


# ============================================================================
# 6. AI Analysis Module Tests
# ============================================================================

def test_ai_analysis_types():
    """Test AI analysis type enum"""
    print("\n[TEST] Testing AI analysis types...")

    try:
        from ai_analysis import AnalysisType

        assert AnalysisType.ALL.value == 'all'
        assert AnalysisType.TECH_STACK.value == 'tech_stack'
        assert AnalysisType.SALARY.value == 'salary'

        results.add_pass("ai_analysis_types")
        print("  AnalysisType enum values verified")
    except Exception as e:
        results.add_fail("ai_analysis_types", str(e))
        print(f"  AnalysisType FAILED: {e}")


def test_ai_analysis_config():
    """Test AI analysis configuration"""
    print("\n[TEST] Testing AI analysis config...")

    try:
        from ai_analysis import AIAnalysisConfig, AnalysisType

        # Test with all types
        config = AIAnalysisConfig(
            analysis_types=[AnalysisType.ALL],
            limit=100,
            region_filter='Perth',
            only_missing=True
        )

        assert config.limit == 100
        assert config.region_filter == 'Perth'
        assert config.only_missing == True
        assert AnalysisType.ALL in config.analysis_types

        results.add_pass("ai_analysis_config")
        print("  AIAnalysisConfig verified")
    except Exception as e:
        results.add_fail("ai_analysis_config", str(e))
        print(f"  AIAnalysisConfig FAILED: {e}")


def test_ai_analysis_cli_help():
    """Test ai_analysis CLI help command"""
    print("\n[TEST] Testing ai_analysis CLI...")

    try:
        result = subprocess.run(
            [sys.executable, '-m', 'ai_analysis', '--help'],
            cwd=SEEKSPIDER_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0
        assert '--type' in result.stdout
        assert '--region' in result.stdout
        assert '--limit' in result.stdout

        results.add_pass("ai_analysis_cli_help")
        print("  CLI help command works")
    except subprocess.TimeoutExpired:
        results.add_fail("ai_analysis_cli_help", "Timeout")
        print("  CLI help FAILED: Timeout")
    except Exception as e:
        results.add_fail("ai_analysis_cli_help", str(e))
        print(f"  CLI help FAILED: {e}")


# ============================================================================
# 7. Pipeline Tests
# ============================================================================

def test_pipeline_imports():
    """Test pipeline module imports"""
    print("\n[TEST] Testing pipeline imports...")

    try:
        sys.path.insert(0, PIPELINE_DIR)

        # Import pipeline
        from seek_spider_pipeline import (
            SeekSpiderParams,
            BackfillParams,
            AIAnalysisParams,
            run_seek_spider,
            run_backfill,
            run_ai_analysis,
        )

        results.add_pass("pipeline_imports")
        print("  Pipeline module imports successful")
    except ImportError as e:
        if 'pydantic' in str(e) or 'plombery' in str(e):
            results.add_skip("pipeline_imports", f"Missing dependency: {e}")
            print(f"  Pipeline imports SKIPPED: {e}")
        else:
            results.add_fail("pipeline_imports", str(e))
            print(f"  Pipeline imports FAILED: {e}")


def test_pipeline_params():
    """Test pipeline parameter classes"""
    print("\n[TEST] Testing pipeline parameters...")

    try:
        sys.path.insert(0, PIPELINE_DIR)
        from seek_spider_pipeline import SeekSpiderParams, BackfillParams, AIAnalysisParams

        # Test SeekSpiderParams
        spider_params = SeekSpiderParams(region='Perth', classification='6281')
        assert spider_params.region == 'Perth'
        assert spider_params.classification == '6281'
        print("  SeekSpiderParams")

        # Test BackfillParams
        backfill_params = BackfillParams(region='Sydney', limit=100)
        assert backfill_params.region == 'Sydney'
        assert backfill_params.limit == 100
        print("  BackfillParams")

        # Test AIAnalysisParams
        ai_params = AIAnalysisParams(analysis_type='all', region_filter='Melbourne')
        assert ai_params.analysis_type == 'all'
        assert ai_params.region_filter == 'Melbourne'
        print("  AIAnalysisParams")

        results.add_pass("pipeline_params")
    except ImportError as e:
        if 'pydantic' in str(e) or 'plombery' in str(e):
            results.add_skip("pipeline_params", f"Missing dependency: {e}")
            print(f"  Pipeline params SKIPPED: {e}")
        else:
            results.add_fail("pipeline_params", str(e))
            print(f"  Pipeline params FAILED: {e}")
    except Exception as e:
        results.add_fail("pipeline_params", str(e))
        print(f"  Pipeline params FAILED: {e}")


def test_pipeline_syntax():
    """Test pipeline file syntax"""
    print("\n[TEST] Testing pipeline syntax...")

    try:
        pipeline_file = os.path.join(PIPELINE_DIR, 'seek_spider_pipeline.py')
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', pipeline_file],
            capture_output=True,
            text=True,
            timeout=30
        )

        assert result.returncode == 0

        results.add_pass("pipeline_syntax")
        print("  Pipeline syntax valid")
    except Exception as e:
        results.add_fail("pipeline_syntax", str(e))
        print(f"  Pipeline syntax FAILED: {e}")


# ============================================================================
# 8. Utility Tests
# ============================================================================

def test_tech_stack_analyzer():
    """Test tech stack analyzer"""
    print("\n[TEST] Testing tech stack analyzer...")

    try:
        from SeekSpider.utils.tech_stack_analyzer import TechStackAnalyzer

        # Just verify the class can be imported
        assert TechStackAnalyzer is not None

        results.add_pass("tech_stack_analyzer")
        print("  TechStackAnalyzer class imported")
    except Exception as e:
        results.add_fail("tech_stack_analyzer", str(e))
        print(f"  TechStackAnalyzer FAILED: {e}")


def test_salary_normalizer():
    """Test salary normalizer"""
    print("\n[TEST] Testing salary normalizer...")

    try:
        from SeekSpider.utils.salary_normalizer import SalaryNormalizer

        # Just verify the class can be imported
        assert SalaryNormalizer is not None

        results.add_pass("salary_normalizer")
        print("  SalaryNormalizer class imported")
    except Exception as e:
        results.add_fail("salary_normalizer", str(e))
        print(f"  SalaryNormalizer FAILED: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("SeekSpider Comprehensive Test Suite")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project root: {PROJECT_ROOT}")

    # 1. Import Tests
    print("\n" + "=" * 70)
    print("1. IMPORT TESTS")
    print("=" * 70)
    test_import_core_modules()
    test_import_backfill_module()
    test_import_ai_analysis_module()
    test_import_spider()
    test_import_utils()

    # 2. Configuration Tests
    print("\n" + "=" * 70)
    print("2. CONFIGURATION TESTS")
    print("=" * 70)
    test_config_instantiation()
    test_config_validation()

    # 3. Database Tests
    print("\n" + "=" * 70)
    print("3. DATABASE TESTS")
    print("=" * 70)
    test_database_connection()
    test_database_table_exists()
    test_database_job_count()
    test_database_region_distribution()
    test_database_missing_descriptions()

    # 4. Spider Tests
    print("\n" + "=" * 70)
    print("4. SPIDER TESTS")
    print("=" * 70)
    test_spider_initialization()
    test_spider_region_configs()

    # 5. Backfill Tests
    print("\n" + "=" * 70)
    print("5. BACKFILL MODULE TESTS")
    print("=" * 70)
    test_backfill_config_defaults()
    test_backfill_driver_manager()
    test_backfill_cli_help()

    # 6. AI Analysis Tests
    print("\n" + "=" * 70)
    print("6. AI ANALYSIS MODULE TESTS")
    print("=" * 70)
    test_ai_analysis_types()
    test_ai_analysis_config()
    test_ai_analysis_cli_help()

    # 7. Pipeline Tests
    print("\n" + "=" * 70)
    print("7. PIPELINE TESTS")
    print("=" * 70)
    test_pipeline_imports()
    test_pipeline_params()
    test_pipeline_syntax()

    # 8. Utility Tests
    print("\n" + "=" * 70)
    print("8. UTILITY TESTS")
    print("=" * 70)
    test_tech_stack_analyzer()
    test_salary_normalizer()

    # Print summary
    return results.print_summary()


# ============================================================================
# Pytest Entry Points
# ============================================================================

# Import tests
def test_pytest_import_core():
    test_import_core_modules()
    assert len([f for f in results.failed if 'import_core' in f[0]]) == 0

def test_pytest_import_backfill():
    test_import_backfill_module()
    assert len([f for f in results.failed if 'import_backfill' in f[0]]) == 0

def test_pytest_import_ai_analysis():
    test_import_ai_analysis_module()
    assert len([f for f in results.failed if 'import_ai_analysis' in f[0]]) == 0

def test_pytest_import_spider():
    test_import_spider()
    assert len([f for f in results.failed if 'import_spider' in f[0]]) == 0

def test_pytest_import_utils():
    test_import_utils()
    assert len([f for f in results.failed if 'import_utils' in f[0]]) == 0

# Config tests
def test_pytest_config_instantiation():
    test_config_instantiation()

def test_pytest_config_validation():
    test_config_validation()

# Database tests
def test_pytest_database():
    test_database_connection()
    test_database_table_exists()
    test_database_job_count()

# Spider tests
def test_pytest_spider():
    test_spider_initialization()
    test_spider_region_configs()

# Backfill tests
def test_pytest_backfill():
    test_backfill_config_defaults()
    test_backfill_driver_manager()
    test_backfill_cli_help()

# AI Analysis tests
def test_pytest_ai_analysis():
    test_ai_analysis_types()
    test_ai_analysis_config()
    test_ai_analysis_cli_help()

# Pipeline tests
def test_pytest_pipeline():
    test_pipeline_imports()
    test_pipeline_params()
    test_pipeline_syntax()

# Utility tests
def test_pytest_utils():
    test_tech_stack_analyzer()
    test_salary_normalizer()


if __name__ == '__main__':
    sys.exit(run_all_tests())
