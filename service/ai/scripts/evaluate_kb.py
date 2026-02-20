#!/usr/bin/env python3
"""Evaluate retrieval/chat quality with a simple benchmark case set."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests


def load_cases(path: Path) -> List[Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("Case file must be a JSON array")
    return raw


def post_json(url: str, payload: Dict[str, Any], timeout: float) -> Tuple[int, Dict[str, Any]]:
    resp = requests.post(url, json=payload, timeout=timeout)
    try:
        data = resp.json()
    except ValueError:
        data = {"_raw": resp.text}
    return resp.status_code, data


def norm(s: str) -> str:
    return s.strip().lower()


def keywords_pass(answer: str, keywords: List[str]) -> Tuple[bool, int]:
    if not keywords:
        return True, 0
    answer_norm = norm(answer)
    hit = sum(1 for kw in keywords if norm(kw) in answer_norm)
    need = max(1, math.ceil(len(keywords) * 0.6))
    return hit >= need, hit


def match_project(expect: List[str], candidates: List[str]) -> bool:
    if not expect:
        return True
    expected = {norm(x) for x in expect}
    actual = {norm(x) for x in candidates if x}
    return not expected.isdisjoint(actual)


def match_file_contains(expect: List[str], candidates: List[str]) -> bool:
    if not expect:
        return True
    lower_candidates = [norm(x) for x in candidates if x]
    for e in expect:
        target = norm(e)
        for c in lower_candidates:
            if target in c:
                return True
    return False


def evaluate_search(base_url: str, case: Dict[str, Any], top_k: int, timeout: float) -> Dict[str, Any]:
    status, data = post_json(
        f"{base_url}/api/search",
        {"query": case["query"], "k": top_k},
        timeout=timeout,
    )
    if status != 200:
        return {"ok": False, "reason": f"HTTP {status}", "status": status}

    results = data.get("results", [])
    projects = [r.get("metadata", {}).get("project", "") for r in results]
    sources = [
        r.get("metadata", {}).get("source", "") or r.get("metadata", {}).get("file_name", "")
        for r in results
    ]

    expect_projects = case.get("search_expected_projects", [])
    expect_files = case.get("search_expected_files", [])
    project_ok = match_project(expect_projects, projects)
    file_ok = match_file_contains(expect_files, sources)
    ok = project_ok and file_ok

    return {
        "ok": ok,
        "status": status,
        "result_count": len(results),
        "project_ok": project_ok,
        "file_ok": file_ok,
        "projects": projects[:top_k],
        "sources": sources[:top_k],
    }


def evaluate_chat(base_url: str, case: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    status, data = post_json(
        f"{base_url}/api/chat",
        {
            "message": case["query"],
            "session_id": f"eval-{case['id']}",
            "use_memory": False,
        },
        timeout=timeout,
    )
    if status != 200:
        return {"ok": False, "reason": f"HTTP {status}", "status": status}

    answer = data.get("response", "")
    sources = data.get("sources", [])
    source_projects = [s.get("project", "") for s in sources]

    kw_ok, kw_hit = keywords_pass(answer, case.get("chat_expected_keywords", []))
    project_ok = match_project(case.get("chat_expected_projects", []), source_projects)
    ok = kw_ok and project_ok

    return {
        "ok": ok,
        "status": status,
        "keyword_ok": kw_ok,
        "keyword_hit": kw_hit,
        "source_project_ok": project_ok,
        "source_projects": source_projects,
        "answer_preview": answer[:120],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Galay AI knowledge base quality")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="AI service base URL")
    parser.add_argument(
        "--cases",
        default="eval/benchmark_cases.json",
        help="Benchmark case JSON file path (relative to service/ai)",
    )
    parser.add_argument("--mode", choices=["search", "chat", "all"], default="all")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--min-pass-rate", type=float, default=0.7)
    args = parser.parse_args()

    ai_dir = Path(__file__).resolve().parent.parent
    cases_path = (ai_dir / args.cases).resolve()
    cases = load_cases(cases_path)

    print(f"[INFO] Base URL: {args.base_url}")
    print(f"[INFO] Cases: {cases_path}")
    print(f"[INFO] Mode: {args.mode}")
    print(f"[INFO] Total cases: {len(cases)}")

    passed = 0
    total = 0
    rows: List[Dict[str, Any]] = []

    for case in cases:
        case_result: Dict[str, Any] = {"id": case["id"], "query": case["query"]}
        search_ok = True
        chat_ok = True

        if args.mode in {"search", "all"}:
            search_result = evaluate_search(args.base_url, case, args.top_k, args.timeout)
            case_result["search"] = search_result
            search_ok = search_result.get("ok", False)
        if args.mode in {"chat", "all"}:
            chat_result = evaluate_chat(args.base_url, case, args.timeout)
            case_result["chat"] = chat_result
            chat_ok = chat_result.get("ok", False)

        case_pass = search_ok and chat_ok
        case_result["pass"] = case_pass
        rows.append(case_result)

        total += 1
        if case_pass:
            passed += 1

        print(f"[{'PASS' if case_pass else 'FAIL'}] {case['id']} - {case['query']}")
        if not case_pass:
            if "search" in case_result:
                print(f"  search: {case_result['search']}")
            if "chat" in case_result:
                print(f"  chat: {case_result['chat']}")

    pass_rate = passed / total if total else 0.0
    summary = {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(pass_rate, 4),
        "min_pass_rate": args.min_pass_rate,
    }

    print("\n=== Summary ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    output_path = ai_dir / "eval" / "last_eval_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"summary": summary, "cases": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INFO] Report written to: {output_path}")

    if pass_rate < args.min_pass_rate:
        sys.exit(1)


if __name__ == "__main__":
    main()
