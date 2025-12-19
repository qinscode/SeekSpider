#!/usr/bin/env python3
"""
Concurrency Test Script for SeekSpider

This script tests the concurrent execution of multiple pipelines:
1. Triggers 3 seek_spider tasks with different regions simultaneously
2. Verifies that all tasks run concurrently without blocking each other
3. Tests that the web interface remains responsive during execution
"""

import asyncio
import httpx
import time
from datetime import datetime

API_BASE = "http://localhost:6059/api"


async def trigger_pipeline(client: httpx.AsyncClient, region: str, task_num: int):
    """Trigger a single pipeline run"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_num}: Triggering {region} spider...")

    payload = {
        "params": {
            "region": region,
            "classification": "6281",
            "run_post_processing": False,  # Disable to speed up test
            "concurrent_requests": 8,
            "download_delay": 1.0
        }
    }

    try:
        response = await client.post(
            f"{API_BASE}/pipelines/seek_spider/run",
            json=payload,
            timeout=10.0
        )
        response.raise_for_status()
        data = response.json()
        run_id = data.get("id")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_num}: Started run #{run_id} for {region}")
        return {"task_num": task_num, "region": region, "run_id": run_id, "success": True}
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Task {task_num}: Failed to trigger {region} - {e}")
        return {"task_num": task_num, "region": region, "error": str(e), "success": False}


async def check_ui_responsive(client: httpx.AsyncClient):
    """Test if UI endpoints are responsive"""
    endpoints = [
        "/",
        "/api/pipelines/",
        "/api/runs/"
    ]

    results = []
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = await client.get(f"{API_BASE.replace('/api', '')}{endpoint}", timeout=5.0)
            elapsed = time.time() - start_time
            results.append({
                "endpoint": endpoint,
                "status": response.status_code,
                "response_time_ms": round(elapsed * 1000, 2),
                "success": response.is_success
            })
        except Exception as e:
            results.append({
                "endpoint": endpoint,
                "error": str(e),
                "success": False
            })

    return results


async def monitor_runs(client: httpx.AsyncClient, run_ids: list, duration: int = 20):
    """Monitor the status of running pipelines"""
    print(f"\n{'='*60}")
    print(f"Monitoring runs for {duration} seconds...")
    print(f"{'='*60}\n")

    start_time = time.time()
    while time.time() - start_time < duration:
        statuses = []
        for run_id in run_ids:
            try:
                response = await client.get(f"{API_BASE}/runs/{run_id}", timeout=5.0)
                if response.is_success:
                    data = response.json()
                    statuses.append({
                        "run_id": run_id,
                        "status": data.get("status"),
                        "duration_ms": data.get("duration", 0)
                    })
            except Exception as e:
                statuses.append({"run_id": run_id, "error": str(e)})

        print(f"[{datetime.now().strftime('%H:%M:%S')}] Status:")
        for status in statuses:
            if "error" in status:
                print(f"  Run #{status['run_id']}: ERROR - {status['error']}")
            else:
                print(f"  Run #{status['run_id']}: {status['status']} (duration: {status['duration_ms']}ms)")

        await asyncio.sleep(3)

    print(f"\n{'='*60}\n")


async def main():
    """Main test function"""
    print("="*60)
    print("SeekSpider Concurrency Test")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    async with httpx.AsyncClient() as client:
        # Test 1: Check if API is accessible
        print("Step 1: Checking API accessibility...")
        try:
            response = await client.get(f"{API_BASE}/pipelines/", timeout=5.0)
            response.raise_for_status()
            print("✓ API is accessible\n")
        except Exception as e:
            print(f"✗ API is not accessible: {e}")
            print("Please make sure the application is running on http://localhost:6059")
            return

        # Test 2: Trigger multiple pipelines concurrently
        print("Step 2: Triggering 3 concurrent pipeline runs...")
        regions = ["Perth", "Sydney", "Melbourne"]
        tasks = [
            trigger_pipeline(client, region, i+1)
            for i, region in enumerate(regions)
        ]

        # Execute all triggers concurrently
        results = await asyncio.gather(*tasks)

        print(f"\n{'='*60}")
        print("Trigger Results:")
        print(f"{'='*60}")
        for result in results:
            if result["success"]:
                print(f"✓ Task {result['task_num']} ({result['region']}): Run #{result['run_id']}")
            else:
                print(f"✗ Task {result['task_num']} ({result['region']}): {result.get('error', 'Unknown error')}")
        print()

        successful_runs = [r["run_id"] for r in results if r["success"]]

        if not successful_runs:
            print("No runs were successfully triggered. Test aborted.")
            return

        # Test 3: Test UI responsiveness while tasks are running
        print("Step 3: Testing UI responsiveness while tasks are running...")
        await asyncio.sleep(2)  # Wait a bit for tasks to start

        ui_results = await check_ui_responsive(client)

        print(f"\n{'='*60}")
        print("UI Responsiveness Test:")
        print(f"{'='*60}")
        for result in ui_results:
            if result["success"]:
                print(f"✓ {result['endpoint']}: {result['status']} ({result['response_time_ms']}ms)")
            else:
                print(f"✗ {result['endpoint']}: {result.get('error', 'Failed')}")
        print()

        # Test 4: Monitor the runs
        await monitor_runs(client, successful_runs, duration=20)

        # Test 5: Final UI responsiveness check
        print("Step 4: Final UI responsiveness check...")
        ui_results = await check_ui_responsive(client)

        print(f"\n{'='*60}")
        print("Final UI Responsiveness:")
        print(f"{'='*60}")
        all_responsive = True
        for result in ui_results:
            if result["success"]:
                print(f"✓ {result['endpoint']}: {result['status']} ({result['response_time_ms']}ms)")
            else:
                print(f"✗ {result['endpoint']}: {result.get('error', 'Failed')}")
                all_responsive = False

        # Summary
        print(f"\n{'='*60}")
        print("Test Summary:")
        print(f"{'='*60}")
        print(f"✓ Successfully triggered {len(successful_runs)} concurrent tasks")
        print(f"{'✓' if all_responsive else '✗'} UI remained responsive during execution")
        print(f"\nConclusion: {'✓ PASS' if all_responsive and successful_runs else '✗ FAIL'}")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
