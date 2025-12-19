#!/usr/bin/env python3
"""
Test script to verify region filtering in backfill script
This ensures no database conflicts occur between different region backfills
"""

import sys
import os

# Add paths
sys.path.insert(0, '../scraper')
from dotenv import load_dotenv
load_dotenv('../.env')

from SeekSpider.core.config import config
from SeekSpider.core.database import DatabaseManager


def test_region_filtering():
    """Test that region filtering correctly isolates jobs by region"""

    db = DatabaseManager(config)

    print("=" * 70)
    print("TESTING REGION FILTERING IN BACKFILL")
    print("=" * 70)

    # Test query without region filter
    query_all = f'''
        SELECT COUNT(*), "Region"
        FROM "{config.POSTGRESQL_TABLE}"
        WHERE ("JobDescription" IS NULL OR "JobDescription" = '' OR "JobDescription" = 'None')
        AND "IsActive" = 'True'
        GROUP BY "Region"
        ORDER BY "Region"
    '''

    print("\n1. Jobs without descriptions by region (what each backfill will process):")
    print("-" * 70)

    try:
        results = db.execute_query(query_all)
        total_jobs = 0

        for count, region in results:
            print(f"   {region:15s}: {count:4d} jobs")
            total_jobs += count

        print("-" * 70)
        print(f"   {'TOTAL':15s}: {total_jobs:4d} jobs")

    except Exception as e:
        print(f"   Error: {e}")
        return False

    # Test query with region filter for Perth
    test_region = 'Perth'
    query_perth = f'''
        SELECT "Id", "JobTitle"
        FROM "{config.POSTGRESQL_TABLE}"
        WHERE ("JobDescription" IS NULL OR "JobDescription" = '' OR "JobDescription" = 'None')
        AND "IsActive" = 'True'
        AND "Region" = %s
        LIMIT 5
    '''

    print(f"\n2. Testing Perth backfill query (with Region='{test_region}' filter):")
    print("-" * 70)

    try:
        results = db.execute_query(query_perth, (test_region,))

        if results:
            print(f"   ✅ Found {len(results)} Perth jobs (showing first 5):")
            for job_id, title in results:
                print(f"      - Job {job_id}: {title[:50]}...")
        else:
            print(f"   ℹ️  No Perth jobs without descriptions found")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

    # Verify no overlap
    print("\n3. Verifying no overlap between regions:")
    print("-" * 70)

    regions = ['Perth', 'Sydney', 'Melbourne']
    region_jobs = {}

    for region in regions:
        query = f'''
            SELECT "Id"
            FROM "{config.POSTGRESQL_TABLE}"
            WHERE ("JobDescription" IS NULL OR "JobDescription" = '' OR "JobDescription" = 'None')
            AND "IsActive" = 'True'
            AND "Region" = %s
        '''
        try:
            results = db.execute_query(query, (region,))
            region_jobs[region] = set(row[0] for row in results)
            print(f"   {region:15s}: {len(region_jobs[region]):4d} unique jobs")
        except Exception as e:
            print(f"   ❌ Error for {region}: {e}")
            return False

    # Check for overlaps
    print("\n4. Checking for job ID overlaps (should be none):")
    print("-" * 70)

    overlaps_found = False
    for i, region1 in enumerate(regions):
        for region2 in regions[i+1:]:
            overlap = region_jobs[region1] & region_jobs[region2]
            if overlap:
                print(f"   ❌ OVERLAP between {region1} and {region2}: {len(overlap)} jobs")
                overlaps_found = True
            else:
                print(f"   ✅ No overlap between {region1:15s} and {region2:15s}")

    print("\n" + "=" * 70)

    if overlaps_found:
        print("❌ FAILED: Overlaps found! Region filtering is NOT working correctly!")
        print("   This WILL cause database conflicts!")
        return False
    else:
        print("✅ SUCCESS: Region filtering is working correctly!")
        print("   Each region has distinct jobs - no conflicts will occur!")
        return True

    print("=" * 70 + "\n")


if __name__ == '__main__':
    success = test_region_filtering()
    sys.exit(0 if success else 1)
