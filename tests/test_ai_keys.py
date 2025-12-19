#!/usr/bin/env python3
"""
AI API Keys 可用性测试脚本
测试 SiliconFlow API keys 是否有效，并查看账户信息
"""

import os
import sys
import requests
from dotenv import load_dotenv
from datetime import datetime

# 加载环境变量
load_dotenv()

# 配置
API_URL = os.getenv("AI_API_URL", "https://api.siliconflow.cn/v1/chat/completions")
USER_INFO_URL = "https://api.siliconflow.cn/v1/user/info"
AI_MODEL = os.getenv("AI_MODEL", "deepseek-ai/DeepSeek-V2.5")
API_KEYS_STR = os.getenv("AI_API_KEY", "")

# 测试消息
TEST_MESSAGE = "Hello, please respond with 'OK' only."


def get_user_info(api_key: str) -> dict:
    """获取账户信息"""
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
    """测试单个API key的可用性"""
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

    # 获取账户信息（无论API调用是否成功都尝试获取）
    result["user_info"] = get_user_info(api_key)

    return result


def print_result(result: dict):
    """打印测试结果"""
    status_icons = {
        "valid": "✅",
        "invalid": "❌",
        "forbidden": "🚫",
        "rate_limited": "⏳",
        "timeout": "⏱️",
        "connection_error": "🔌",
        "error": "⚠️",
        "invalid_response": "❓",
        "unknown": "❔"
    }

    icon = status_icons.get(result["status"], "❔")
    print(f"\n{'='*60}")
    print(f"Key #{result['key_index']}: {result['key_preview']}")
    print(f"{'='*60}")
    print(f"状态: {icon} {result['status'].upper()}")

    if result["response_time_ms"]:
        print(f"响应时间: {result['response_time_ms']}ms")

    if result.get("response"):
        print(f"响应内容: {result['response']}")

    if result["error"]:
        print(f"错误信息: {result['error']}")

    # 显示账户信息
    if result.get("user_info"):
        user_info = result["user_info"]
        if user_info.get("success"):
            data = user_info["data"].get("data", user_info["data"])
            print(f"\n--- 账户信息 ---")
            if "name" in data:
                print(f"用户名: {data['name']}")
            if "balance" in data:
                print(f"余额: ¥{data['balance']}")
            if "totalBalance" in data:
                print(f"总余额: ¥{data['totalBalance']}")
            if "chargeBalance" in data:
                print(f"充值余额: ¥{data['chargeBalance']}")
            if "giftBalance" in data:
                print(f"赠送余额: ¥{data['giftBalance']}")
            if "status" in data:
                print(f"账户状态: {data['status']}")


def main():
    print("\n" + "="*60)
    print("       AI API Keys 可用性测试")
    print("="*60)
    print(f"API URL: {API_URL}")
    print(f"Model: {AI_MODEL}")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if not API_KEYS_STR:
        print("\n❌ 错误: 未找到 AI_API_KEY 环境变量")
        sys.exit(1)

    # 解析多个keys
    api_keys = [k.strip() for k in API_KEYS_STR.split(",") if k.strip()]
    print(f"发现 {len(api_keys)} 个API keys")

    results = []
    valid_count = 0

    for i, key in enumerate(api_keys):
        print(f"\n正在测试 Key #{i}...")
        result = test_single_key(key, i)
        results.append(result)
        print_result(result)

        if result["status"] == "valid":
            valid_count += 1

    # 汇总
    print("\n" + "="*60)
    print("       测试汇总")
    print("="*60)
    print(f"总计: {len(api_keys)} 个keys")
    print(f"有效: {valid_count} 个")
    print(f"无效: {len(api_keys) - valid_count} 个")

    if valid_count == len(api_keys):
        print("\n✅ 所有API keys均可用!")
        return 0
    elif valid_count > 0:
        print(f"\n⚠️ 部分API keys可用 ({valid_count}/{len(api_keys)})")
        return 1
    else:
        print("\n❌ 所有API keys均不可用!")
        return 2


if __name__ == "__main__":
    sys.exit(main())
