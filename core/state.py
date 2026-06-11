"""Persistent state: per-strategy challenge books, positions, and de-dupe keys.

Each strategy runs its OWN isolated prop-firm challenge (its own balance, daily-loss
budget, max-loss floor and pass/fail status) instead of sharing one account. A bad
strategy can only blow up its own book - it cannot drag the others down. State is
plain JSON under state/ and is committed back to the repo by the GitHub Actions
workflow so it survives across the ephemeral cron runs.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List, Dict

from .models import Position

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")


@dataclass
class Book:
    """One strategy's isolated FundingPips challenge account."""
    strategy: str = ""
    account_size: float = 100000.0
    equity: float = 100000.0           # balance + open MTM
    balance: float = 100000.0          # realized only
    today_start_equity: float = 100000.0
    current_day: str = ""              # reset-day key (YYYY-MM-DD of FundingPips server day)
    daily_realized_pnl: float = 0.0
    peak_balance: float = 100000.0
    status: str = "active"             # active | passed | failed
    failed_reason: str = ""            # "daily loss" | "max loss" (when status == failed)
    resolved_at: str = ""              # ISO timestamp the book passed or failed
    sl_count: dict = field(default_factory=dict)   # strategy -> stop-losses taken today
    trades_total: int = 0
    wins: int = 0
    losses: int = 0
    phase: int = 1                     # 1 or 2 (FundingPips Phase 1 / Phase 2)
    phase1_start: str = ""             # ISO date Phase 1 started
    phase1_passed_at: str = ""         # ISO timestamp Phase 1 was passed
    phase2_start: str = ""             # ISO date Phase 2 started
    phase1_days: int = 0               # calendar days to pass Phase 1
    phase2_days: int = 0               # calendar days elapsed in Phase 2

    def to_dict(self):
        return asdict(self)


def _path(name: str) -> str:
    return os.path.join(STATE_DIR, name)


def load_books(strategy_names: List[str], account_size: float) -> Dict[str, Book]:
    """Load every strategy's book, creating a fresh one for any new strategy."""
    p = _path("books.json")
    raw = {}
    if os.path.exists(p):
        with open(p) as f:
            raw = json.load(f)
    books: Dict[str, Book] = {}
    for name in strategy_names:
        if name in raw:
            b = Book(**raw[name])
            b.account_size = account_size
            books[name] = b
        else:
            books[name] = Book(strategy=name, account_size=account_size,
                               equity=account_size, balance=account_size,
                               today_start_equity=account_size, peak_balance=account_size)
    return books


def save_books(books: Dict[str, Book]):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_path("books.json"), "w") as f:
        json.dump({k: v.to_dict() for k, v in books.items()}, f, indent=2)


def load_positions() -> List[Position]:
    p = _path("positions.json")
    if os.path.exists(p):
        with open(p) as f:
            return [Position(**d) for d in json.load(f)]
    return []


def save_positions(positions: List[Position]):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_path("positions.json"), "w") as f:
        json.dump([p.to_dict() for p in positions], f, indent=2)


def load_sent() -> set:
    p = _path("sent_signals.json")
    if os.path.exists(p):
        with open(p) as f:
            return set(json.load(f))
    return set()


def save_sent(keys: set):
    os.makedirs(STATE_DIR, exist_ok=True)
    # keep last 2000 to stop unbounded growth
    with open(_path("sent_signals.json"), "w") as f:
        json.dump(list(keys)[-2000:], f, indent=2)
