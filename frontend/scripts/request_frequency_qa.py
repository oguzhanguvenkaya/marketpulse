#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from collections import Counter
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlsplit

import requests
from playwright.async_api import async_playwright


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


class ApiRequestCounter:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()

    def record(self, url: str) -> None:
        path = urlsplit(url).path
        if "/api/" not in path:
            return
        self._counts[path] += 1

    def snapshot(self) -> Counter[str]:
        return Counter(self._counts)

    @staticmethod
    def delta(before: Counter[str], after: Counter[str], endpoint: str) -> int:
        return max(0, after.get(endpoint, 0) - before.get(endpoint, 0))


def _first_seller_id(api_base_url: str, platform: str, timeout_seconds: int) -> Optional[str]:
    response = requests.get(
        f"{api_base_url.rstrip('/')}/api/sellers",
        params={"platform": platform, "limit": 1, "offset": 0},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    sellers = payload.get("sellers") if isinstance(payload, dict) else None
    if not sellers:
        return None
    seller_id = sellers[0].get("merchant_id")
    return str(seller_id) if seller_id else None


async def run_checks(args: argparse.Namespace) -> int:
    results: list[CheckResult] = []
    counter = ApiRequestCounter()
    frontend_base = args.frontend_url.rstrip("/")

    try:
        seller_id = _first_seller_id(args.api_base_url, args.platform, args.http_timeout)
    except Exception as exc:
        seller_id = None
        results.append(
            CheckResult(
                name="Seller seed id",
                passed=False,
                detail=f"Could not load seller id for seller detail test: {exc}",
            )
        )

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=not args.headed)
        context = await browser.new_context()
        page = await context.new_page()
        page.on("request", lambda request: counter.record(request.url))

        # 1) PriceMonitor initial + idle loop check
        await page.goto(f"{frontend_base}/price-monitor", wait_until="domcontentloaded")
        await page.wait_for_timeout(args.initial_wait_ms)
        pm_before_idle = counter.snapshot()
        await page.wait_for_timeout(args.idle_window_ms)
        pm_after_idle = counter.snapshot()

        pm_products_idle = counter.delta(
            pm_before_idle, pm_after_idle, "/api/price-monitor/products"
        )
        pm_brands_idle = counter.delta(
            pm_before_idle, pm_after_idle, "/api/price-monitor/brands"
        )
        pm_last_inactive_idle = counter.delta(
            pm_before_idle, pm_after_idle, "/api/price-monitor/last-inactive"
        )
        pm_pass = (
            pm_products_idle <= args.max_idle_repeats
            and pm_brands_idle <= args.max_idle_repeats
            and pm_last_inactive_idle <= args.max_idle_repeats
        )
        results.append(
            CheckResult(
                name="PriceMonitor idle loop",
                passed=pm_pass,
                detail=(
                    "idle deltas: "
                    f"products={pm_products_idle}, brands={pm_brands_idle}, "
                    f"last-inactive={pm_last_inactive_idle}, limit={args.max_idle_repeats}"
                ),
            )
        )

        # 2) PriceMonitor search debounce check
        search_input = page.locator("input[placeholder*='Search by SKU']").first
        search_before = counter.snapshot()
        if await search_input.count() == 0:
            results.append(
                CheckResult(
                    name="PriceMonitor debounce",
                    passed=False,
                    detail="Search input not found on /price-monitor",
                )
            )
        else:
            await search_input.click()
            await search_input.fill("")
            await search_input.type("smokecheck", delay=40)
            await page.wait_for_timeout(args.search_wait_ms)
            search_after = counter.snapshot()
            search_products_delta = counter.delta(
                search_before, search_after, "/api/price-monitor/products"
            )
            debounce_pass = search_products_delta <= args.max_search_products_calls
            results.append(
                CheckResult(
                    name="PriceMonitor debounce",
                    passed=debounce_pass,
                    detail=(
                        f"products delta after typing={search_products_delta}, "
                        f"limit={args.max_search_products_calls}"
                    ),
                )
            )

        # 3) Sellers idle loop check
        await page.goto(f"{frontend_base}/sellers", wait_until="domcontentloaded")
        await page.wait_for_timeout(args.initial_wait_ms)
        sellers_before_idle = counter.snapshot()
        await page.wait_for_timeout(args.idle_window_ms)
        sellers_after_idle = counter.snapshot()
        sellers_idle = counter.delta(sellers_before_idle, sellers_after_idle, "/api/sellers")
        results.append(
            CheckResult(
                name="Sellers idle loop",
                passed=sellers_idle <= args.max_idle_repeats,
                detail=f"idle /api/sellers delta={sellers_idle}, limit={args.max_idle_repeats}",
            )
        )

        # 4) SellerDetail idle loop check
        if seller_id:
            seller_products_endpoint = f"/api/sellers/{seller_id}/products"
            await page.goto(
                f"{frontend_base}/sellers/{seller_id}?platform={args.platform}",
                wait_until="domcontentloaded",
            )
            await page.wait_for_timeout(args.initial_wait_ms)
            detail_before_idle = counter.snapshot()
            await page.wait_for_timeout(args.idle_window_ms)
            detail_after_idle = counter.snapshot()
            detail_idle = counter.delta(detail_before_idle, detail_after_idle, seller_products_endpoint)
            results.append(
                CheckResult(
                    name="SellerDetail idle loop",
                    passed=detail_idle <= args.max_idle_repeats,
                    detail=f"idle {seller_products_endpoint} delta={detail_idle}, limit={args.max_idle_repeats}",
                )
            )
        else:
            results.append(
                CheckResult(
                    name="SellerDetail idle loop",
                    passed=False,
                    detail="Skipped: no seller id available from /api/sellers",
                )
            )

        await context.close()
        await browser.close()

    has_failure = any(not item.passed for item in results)
    for item in results:
        status = "PASS" if item.passed else "FAIL"
        print(f"[{status}] {item.name}: {item.detail}")

    return 1 if has_failure else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Frontend request-frequency QA checks (Playwright/Firefox).")
    parser.add_argument("--frontend-url", default="http://127.0.0.1:5173", help="Frontend app URL")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000", help="Backend API base URL")
    parser.add_argument("--platform", default="hepsiburada", choices=["hepsiburada", "trendyol"])
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument("--initial-wait-ms", type=int, default=3000, help="Initial settle wait per page")
    parser.add_argument("--idle-window-ms", type=int, default=5000, help="Idle window to detect loops")
    parser.add_argument("--search-wait-ms", type=int, default=1000, help="Wait after typing for debounce")
    parser.add_argument("--http-timeout", type=int, default=10, help="HTTP timeout for seed API call")
    parser.add_argument("--max-idle-repeats", type=int, default=1, help="Allowed idle repeats per endpoint")
    parser.add_argument(
        "--max-search-products-calls",
        type=int,
        default=2,
        help="Allowed /price-monitor/products calls after a rapid search typing burst",
    )
    args = parser.parse_args()
    return asyncio.run(run_checks(args))


if __name__ == "__main__":
    raise SystemExit(main())
