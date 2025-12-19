#!/usr/bin/env python3
"""
AI API Keys Availability Test Script

Tests SiliconFlow API keys for validity and shows account information.

Usage:
    python tests/test_ai_keys.py
"""

import os
import sys
import requests
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("AI_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
USER_INFO_URL = "https://api.siliconflow.cn/v1/user/info"
AI_MODEL = os.getenv("AI_MODEL", "deepseek-ai/DeepSeek-V2.5")
API_KEYS_STR = os.getenv("AI_API_KEY", "")

# Test message
TEST_MESSAGE = "Hello, please respond with 'OK' only."


def get_user_info(api_key: str) -> dict:
    """Get account information"""
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    try:
        response = requests.get(USER_INFO_URL, headers=headers, timeout=10)
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def test_single_key(api_key: str, key_index: int) -> dict:
    """Test a single API key for availability"""
    result = {
        "key_index": key_index,
        "key_preview": f"{api_key[:10]}...{api_key[-4:]}",
        "status": "unknown",
        "response_time_ms": None,
        "error": None,
        "model": AI_MODEL,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": AI_MODEL,
        "messages": [
            {"role": "user", "content": TEST_MESSAGE}
        ],
        "max_tokens": 10,
        "temperature": 0.1
    }

    try:
        start_time = datetime.now()
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        end_time = datetime.now()
        result["response_time_ms"] = int((end_time - start_time).total_seconds() * 1000)

        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                result["status"] = "valid"
                result["response"] = data["choices"][0]["message"]["content"][:50]
            else:
                result["status"] = "invalid_response"
                result["error"] = "No choices in response"
        elif response.status_code == 401:
            result["status"] = "invalid"
            result["error"] = "Authentication failed - Invalid API key"
        elif response.status_code == 403:
            result["status"] = "forbidden"
            result["error"] = "Access forbidden - Key may be disabled or rate limited"
        elif response.status_code == 429:
            result["status"] = "rate_limited"
            result["error"] = "Rate limit exceeded"
        else:
            result["status"] = "error"
            result["error"] = f"HTTP {response.status_code}: {response.text[:100]}"

    except requests.exceptions.Timeout:
        result["status"] = "timeout"
        result["error"] = "Request timed out (30s)"
    except requests.exceptions.ConnectionError as e:
        result["status"] = "connection_error"
        result["error"] = f"Connection error: {str(e)[:50]}"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)[:100]

    # Get account info (attempt regardless of API call success)
    result["user_info"] = get_user_info(api_key)

    return result


def print_result(result: dict):
    """Print test result"""
    status_icons = {
        "valid": "[OK]",
        "invalid": "[X]",
        "forbidden": "[!]",
        "rate_limited": "[~]",
        "timeout": "[T]",
        "connection_error": "[C]",
        "error": "[E]",
        "invalid_response": "[?]",
        "unknown": "[?]"
    }

    icon = status_icons.get(result["status"], "[?]")
    print(f"\n{'='*60}")
    print(f"Key #{result['key_index']}: {result['key_preview']}")
    print(f"{'='*60}")
    print(f"Status: {icon} {result['status'].upper()}")

    if result["response_time_ms"]:
        print(f"Response time: {result['response_time_ms']}ms")

    if result.get("response"):
        print(f"Response: {result['response']}")

    if result["error"]:
        print(f"Error: {result['error']}")

    # Display account info
    if result.get("user_info"):
        user_info = result["user_info"]
        if user_info.get("success"):
            data = user_info["data"].get("data", user_info["data"])
            print(f"\n--- Account Info ---")
            if "name" in data:
                print(f"Username: {data['name']}")
            if "balance" in data:
                print(f"Balance: ${data['balance']}")
            if "totalBalance" in data:
                print(f"Total balance: ${data['totalBalance']}")
            if "chargeBalance" in data:
                print(f"Charged balance: ${data['chargeBalance']}")
            if "giftBalance" in data:
                print(f"Gift balance: ${data['giftBalance']}")
            if "status" in data:
                print(f"Account status: {data['status']}")


def main():
    print("\n" + "="*60)
    print("       AI API Keys Availability Test")
    print("="*60)
    print(f"API URL: {API_URL}")
    print(f"Model: {AI_MODEL}")
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not API_KEYS_STR:
        print("\n[X] Error: AI_API_KEY environment variable not found")
        sys.exit(1)

    # Parse multiple keys
    api_keys = [k.strip() for k in API_KEYS_STR.split(",") if k.strip()]
    print(f"Found {len(api_keys)} API key(s)")

    results = []
    valid_count = 0

    for i, key in enumerate(api_keys):
        print(f"\nTesting Key #{i}...")
        result = test_single_key(key, i)
        results.append(result)
        print_result(result)

        if result["status"] == "valid":
            valid_count += 1

    # Summary
    print("\n" + "="*60)
    print("       Test Summary")
    print("="*60)
    print(f"Total: {len(api_keys)} key(s)")
    print(f"Valid: {valid_count}")
    print(f"Invalid: {len(api_keys) - valid_count}")

    if valid_count == len(api_keys):
        print("\n[OK] All API keys are valid!")
        return 0
    elif valid_count > 0:
        print(f"\n[!] Some API keys are valid ({valid_count}/{len(api_keys)})")
        return 1
    else:
        print("\n[X] All API keys are invalid!")
        return 2


if __name__ == "__main__":
    sys.exit(main())
