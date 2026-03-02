#!/usr/bin/env python3
"""API 集成测试脚本（chat/search only）"""

import sys

import requests

BASE_URL = "http://localhost:8000"


def test_health() -> None:
    print("=== Health Check ===")
    r = requests.get(f"{BASE_URL}/")
    print(f"  GET / -> {r.status_code}")
    assert r.status_code == 200

    r = requests.get(f"{BASE_URL}/health")
    print(f"  GET /health -> {r.status_code}")
    assert r.status_code == 200
    data = r.json()
    assert "services" in data
    print(f"  health.services: {data.get('services')}")
    print()


def test_search() -> None:
    print("=== Search ===")
    r = requests.post(
        f"{BASE_URL}/api/search",
        json={"query": "galay 协程", "k": 3},
    )
    print(f"  POST /api/search -> {r.status_code}")
    assert r.status_code == 200
    data = r.json()
    print(f"  Results: {len(data.get('results', []))} items")
    print()


def test_chat() -> None:
    print("=== Chat ===")
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": "Galay 框架的核心特性是什么？", "session_id": "test"},
    )
    print(f"  POST /api/chat -> {r.status_code}")
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    print(f"  Response preview: {data.get('response', '')[:100]}...")
    print()


def main() -> None:
    print(f"Testing Galay AI Service at {BASE_URL}\n")

    try:
        test_health()
        test_search()
        test_chat()
        print("All tests passed!")
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to {BASE_URL}. Is the server running?")
        sys.exit(1)
    except AssertionError as exc:
        print(f"TEST FAILED: {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
