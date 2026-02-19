#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

from redis import Redis
from sqlalchemy import create_engine, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402


def check_database(timeout_seconds: int) -> Tuple[bool, str]:
    engine = None
    try:
        database_url = settings.require_database_url()
        connect_args = {}
        if database_url.startswith("postgresql"):
            connect_args = {"connect_timeout": timeout_seconds}

        engine = create_engine(database_url, pool_pre_ping=True, connect_args=connect_args)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "database reachable"
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"
    finally:
        if engine is not None:
            engine.dispose()


def check_queue(timeout_seconds: int) -> Tuple[bool, str]:
    client = None
    try:
        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=timeout_seconds,
            socket_timeout=timeout_seconds,
        )
        client.ping()
        return True, "queue reachable"
    except Exception as exc:
        return False, f"{exc.__class__.__name__}: {exc}"
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime preflight checks for DB and queue.")
    parser.add_argument("--timeout", type=int, default=2, help="Connection timeout in seconds (default: 2)")
    args = parser.parse_args()

    db_ok, db_msg = check_database(args.timeout)
    queue_ok, queue_msg = check_queue(args.timeout)

    print(f"[{'PASS' if db_ok else 'FAIL'}] database: {db_msg}")
    print(f"[{'PASS' if queue_ok else 'FAIL'}] queue: {queue_msg}")

    if db_ok and queue_ok:
        print("Preflight result: PASS")
        return 0

    print("Preflight result: FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
