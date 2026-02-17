#!/usr/bin/env python3
"""API 集成测试脚本"""

import json
import sys
import requests

BASE_URL = "http://localhost:8000"


def test_health():
    print("=== Health Check ===")
    r = requests.get(f"{BASE_URL}/")
    print(f"  GET / → {r.status_code}")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    print(f"  Response: {data}")

    r = requests.get(f"{BASE_URL}/health")
    print(f"  GET /health → {r.status_code}")
    assert r.status_code == 200
    print()


def test_search():
    print("=== Search ===")
    r = requests.post(
        f"{BASE_URL}/api/search",
        json={"query": "galay 协程", "k": 3},
    )
    print(f"  POST /api/search → {r.status_code}")
    data = r.json()
    print(f"  Results: {len(data.get('results', []))} items")
    if data.get("results"):
        print(f"  First result score: {data['results'][0]['score']}")
    print()


def test_chat():
    print("=== Chat ===")
    r = requests.post(
        f"{BASE_URL}/api/chat",
        json={"message": "Galay 框架的核心特性是什么？", "session_id": "test"},
    )
    print(f"  POST /api/chat → {r.status_code}")
    data = r.json()
    print(f"  Success: {data.get('success')}")
    print(f"  Response: {data.get('response', '')[:100]}...")
    print(f"  Sources: {len(data.get('sources', []))} items")
    print()


def test_stats():
    print("=== Stats ===")
    r = requests.get(f"{BASE_URL}/api/stats")
    print(f"  GET /api/stats → {r.status_code}")
    data = r.json()
    print(f"  Stats: {json.dumps(data.get('stats', {}), indent=2, ensure_ascii=False)}")
    print()


def test_clear_session():
    print("=== Clear Session ===")
    r = requests.delete(f"{BASE_URL}/api/session/test")
    print(f"  DELETE /api/session/test → {r.status_code}")
    data = r.json()
    print(f"  Response: {data}")
    print()


def main():
    print(f"Testing Galay AI Service at {BASE_URL}\n")

    try:
        test_health()
        test_search()
        test_chat()
        test_stats()
        test_clear_session()
        print("All tests passed!")
    except requests.ConnectionError:
        print(f"ERROR: Cannot connect to {BASE_URL}. Is the server running?")
        sys.exit(1)
    except AssertionError as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
