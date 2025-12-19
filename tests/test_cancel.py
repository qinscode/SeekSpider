#!/usr/bin/env python3
"""
Test script for cancel functionality

This script:
1. Starts a long-running spider task
2. Waits a few seconds
3. Cancels the task
4. Verifies the task was cancelled
"""

import asyncio
import httpx
import time
from datetime import datetime

API_BASE = "http://localhost:6059/api"


async def test_cancel():
    """Test the cancel functionality"""
    print("="*60)
    print("Testing Cancel Functionality")
    print("="*60)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    async with httpx.AsyncClient() as client:
        # Step 1: Start a long-running task
        print("Step 1: Starting a long-running spider task...")
        payload = {
            "params": {
                "region": "Perth",
                "classification": "6281",
                "run_post_processing": False,
                "concurrent_requests": 8,
                "download_delay": 2.0  # Slow it down
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
            print(f"✓ Started run #{run_id}\n")
        except Exception as e:
            print(f"✗ Failed to start run: {e}")
            return

        # Step 2: Wait a bit to let the task start executing
        print("Step 2: Waiting 5 seconds for task to start executing...")
        await asyncio.sleep(5)

        # Step 3: Check the task status
        print("Step 3: Checking task status...")
        try:
            response = await client.get(f"{API_BASE}/runs/{run_id}", timeout=5.0)
            response.raise_for_status()
            run_data = response.json()
            status_before = run_data.get("status")
            print(f"Status before cancel: {status_before}")

            if status_before != "running":
                print(f"⚠ Task is not running (status: {status_before}), test may not be valid")
        except Exception as e:
            print(f"✗ Failed to get run status: {e}")
            return

        # Step 4: Cancel the task
        print("\nStep 4: Cancelling the task...")
        try:
            response = await client.post(
                f"{API_BASE}/runs/{run_id}/cancel",
                timeout=10.0
            )
            response.raise_for_status()
            cancel_data = response.json()
            print(f"✓ Cancel request successful: {cancel_data.get('message')}")
        except Exception as e:
            print(f"✗ Failed to cancel run: {e}")
            return

        # Step 5: Wait and verify the task was cancelled
        print("\nStep 5: Waiting 10 seconds and verifying cancellation...")
        await asyncio.sleep(10)

        try:
            response = await client.get(f"{API_BASE}/runs/{run_id}", timeout=5.0)
            response.raise_for_status()
            run_data = response.json()
            status_after = run_data.get("status")
            print(f"Status after cancel: {status_after}")

            if status_after == "cancelled":
                print("\n✓ SUCCESS: Task was successfully cancelled!")
            elif status_after == "running":
                print("\n⚠ WARNING: Task is still running, cancellation may not have worked")
            else:
                print(f"\n⚠ Task status is '{status_after}' (expected 'cancelled')")

        except Exception as e:
            print(f"✗ Failed to verify cancellation: {e}")
            return

        # Summary
        print(f"\n{'='*60}")
        print("Test Summary:")
        print(f"{'='*60}")
        print(f"Run ID: {run_id}")
        print(f"Status before cancel: {status_before}")
        print(f"Status after cancel: {status_after}")
        print(f"Result: {'✓ PASS' if status_after == 'cancelled' else '✗ FAIL'}")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(test_cancel())
