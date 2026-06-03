#!/usr/bin/env python3
"""Reset every strategy to a fresh, isolated $100k challenge and rebuild the dashboard.

Wipes positions, de-dupe keys and the equity curve, recreates one fresh ACTIVE book
per strategy, then regenerates reports/ and docs/status.json. No market data needed.
"""
from __future__ import annotations
import os
import json
import yaml

from core.risk import FundingPipsRules
from core.sessions import now_utc
from core.state import Book, save_books, save_positions, save_sent, STATE_DIR
from report import write_report
from dashboard import build_status

ROOT = os.path.dirname(os.path.abspath(__file__))


def main():
    with open(os.path.join(ROOT, "config.yaml")) as f:
        cfg = yaml.safe_load(f)
    rules = FundingPipsRules(cfg)
    now = now_utc()
    size = rules.account_size

    # fresh ACTIVE book per strategy
    books = {name: Book(strategy=name, account_size=size, equity=size, balance=size,
                        today_start_equity=size, peak_balance=size, status="active")
             for name in cfg["strategies"].keys()}

    # wipe ledgers
    save_positions([])
    save_sent(set())
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(os.path.join(STATE_DIR, "equity_curve.json"), "w") as f:
        json.dump([], f)
    # drop the legacy single-account file if present
    legacy = os.path.join(STATE_DIR, "account.json")
    if os.path.exists(legacy):
        os.remove(legacy)

    save_books(books)
    write_report(books, [], rules, now)
    build_status(books, [], rules, {}, cfg["instruments"], now)

    print(f"[reset] {len(books)} strategies -> fresh ${size:,.0f} challenges, "
          f"all ACTIVE, as of {now:%Y-%m-%d %H:%M UTC}")


if __name__ == "__main__":
    main()
