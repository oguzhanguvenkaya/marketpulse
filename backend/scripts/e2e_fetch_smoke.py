#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from typing import Any, Dict

import requests

TERMINAL_STATUSES = {"completed", "stopped", "failed"}


def _build_headers(api_key: str | None) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if api_key:
        headers["X-API-Key"] = api_key
    return headers


def _ensure_seed_product_if_needed(
    base_url: str,
    platform: str,
    headers: Dict[str, str],
    timeout_seconds: int,
    seed_if_empty: bool,
) -> None:
    list_response = requests.get(
        f"{base_url}/api/price-monitor/products",
        params={"platform": platform, "limit": 1, "offset": 0},
        timeout=timeout_seconds,
    )
    list_response.raise_for_status()
    payload = list_response.json()
    total = int(payload.get("total", 0) or 0)

    if total > 0 or not seed_if_empty:
        print(f"Seed check: total products for {platform} = {total}, seed skipped")
        return

    sku = f"SMOKE-{int(time.time())}"
    seed_payload = {
        "platform": platform,
        "products": [
            {
                "sku": sku,
                "productName": "Smoke Test Product",
                "price": 999999,
            }
        ],
    }
    seed_response = requests.post(
        f"{base_url}/api/price-monitor/products",
        json=seed_payload,
        headers=headers,
        timeout=timeout_seconds,
    )
    if seed_response.status_code >= 400:
        raise RuntimeError(
            f"Seed product insert failed ({seed_response.status_code}): {seed_response.text}"
        )
    print(f"Seed check: added smoke SKU={sku} for platform={platform}")


def main() -> int:
    parser = argparse.ArgumentParser(description="E2E smoke runner for price-monitor fetch flow.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend API base URL")
    parser.add_argument(
        "--platform",
        default="hepsiburada",
        choices=["hepsiburada", "trendyol"],
        help="Target platform (default: hepsiburada)",
    )
    parser.add_argument(
        "--fetch-type",
        default="active",
        choices=["active", "last_inactive", "inactive"],
        help="Fetch type sent to /price-monitor/fetch",
    )
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Poll interval seconds (default: 2)")
    parser.add_argument("--timeout", type=int, default=180, help="Max total wait seconds (default: 180)")
    parser.add_argument(
        "--api-key",
        default=os.getenv("INTERNAL_API_KEY", ""),
        help="X-API-Key value (default: INTERNAL_API_KEY env)",
    )
    parser.add_argument(
        "--require-completed",
        action="store_true",
        help="Exit non-zero unless terminal status is exactly 'completed'",
    )
    parser.add_argument(
        "--seed-if-empty",
        dest="seed_if_empty",
        action="store_true",
        default=True,
        help="Add one smoke product if monitored product list is empty (default: enabled)",
    )
    parser.add_argument(
        "--no-seed-if-empty",
        dest="seed_if_empty",
        action="store_false",
        help="Do not auto-seed smoke product",
    )
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    headers = _build_headers(args.api_key.strip() if args.api_key else "")

    try:
        _ensure_seed_product_if_needed(
            base_url=base_url,
            platform=args.platform,
            headers=headers,
            timeout_seconds=max(2, args.timeout // 3),
            seed_if_empty=args.seed_if_empty,
        )
    except Exception as exc:
        print(f"Smoke setup failed: {exc}")
        return 1

    try:
        start_response = requests.post(
            f"{base_url}/api/price-monitor/fetch",
            params={"platform": args.platform, "fetch_type": args.fetch_type},
            headers=headers,
            timeout=max(5, min(args.timeout, 30)),
        )
    except Exception as exc:
        print(f"Fetch start request failed: {exc}")
        return 1

    if start_response.status_code >= 400:
        print(
            f"Fetch start failed ({start_response.status_code}): {start_response.text}"
        )
        return 1

    start_payload = start_response.json()
    task_id = start_payload.get("task_id")
    if not task_id:
        print(f"Fetch start response missing task_id: {start_payload}")
        return 1

    print(f"Fetch task started: task_id={task_id}, platform={args.platform}, fetch_type={args.fetch_type}")

    deadline = time.time() + args.timeout
    last_status_payload: Dict[str, Any] = {}

    while time.time() < deadline:
        try:
            status_response = requests.get(
                f"{base_url}/api/price-monitor/fetch/{task_id}",
                timeout=max(5, min(args.timeout, 30)),
            )
            status_response.raise_for_status()
            last_status_payload = status_response.json()
        except Exception as exc:
            print(f"Status poll failed: {exc}")
            return 1

        status = str(last_status_payload.get("status", "")).lower()
        completed = last_status_payload.get("completed_products")
        total = last_status_payload.get("total_products")
        failed = last_status_payload.get("failed_products")
        print(f"Task status={status} completed={completed}/{total} failed={failed}")

        if status in TERMINAL_STATUSES:
            print("Final task payload:")
            print(last_status_payload)
            if args.require_completed and status != "completed":
                print("Smoke result: FAIL (terminal status is not completed)")
                return 1
            print("Smoke result: PASS")
            return 0

        time.sleep(max(0.5, args.poll_interval))

    print("Smoke result: FAIL (timeout reached before terminal status)")
    if last_status_payload:
        print(last_status_payload)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
