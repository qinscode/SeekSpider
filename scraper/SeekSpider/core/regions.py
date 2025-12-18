"""
Australian regions configuration for SeekSpider.

This module defines the available Australian regions/cities for job scraping.
Each region has a name (used internally and stored in DB) and a Seek search location string.
"""

# Australian regions configuration
# Format: { 'region_name': 'seek_location_string' }
AUSTRALIAN_REGIONS = {
    # Western Australia
    'Perth': 'All Perth WA',

    # New South Wales
    'Sydney': 'All Sydney NSW',

    # Victoria
    'Melbourne': 'All Melbourne VIC',

    # Queensland
    'Brisbane': 'All Brisbane QLD',
    'Gold Coast': 'All Gold Coast QLD',

    # South Australia
    'Adelaide': 'All Adelaide SA',

    # Australian Capital Territory
    'Canberra': 'All Canberra ACT',

    # Tasmania
    'Hobart': 'All Hobart TAS',

    # Northern Territory
    'Darwin': 'All Darwin NT',
}

# Default region
DEFAULT_REGION = 'Perth'

# Get list of all region names
def get_all_regions():
    """Return list of all available region names."""
    return list(AUSTRALIAN_REGIONS.keys())

def get_seek_location(region: str) -> str:
    """Get the Seek search location string for a region."""
    return AUSTRALIAN_REGIONS.get(region, AUSTRALIAN_REGIONS[DEFAULT_REGION])

def is_valid_region(region: str) -> bool:
    """Check if a region name is valid."""
    return region in AUSTRALIAN_REGIONS
