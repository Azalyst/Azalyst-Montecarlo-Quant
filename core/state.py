"""Persistent state: account, open/closed positions, and de-dupe keys.

State is plain JSON under state/ and is committed back to the repo by the GitHub
Actions workflow so it survives across the ephemeral cron runs.
"""
from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import List

from .models import Position

STATE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state")


@dataclass
class AccountState:
    account_size: float = 100000.0
    equity: float = 100000.0           # balance + open MTM
    balance: float = 100000.0          # realized only
    today_start_equity: float = 100000.0
    current_day: str = ""              # reset-day key (YYYY-MM-DD of FundingPips server day)
    daily_realized_pnl: float = 0.0
    peak_balance: float = 100000.0
    status: str = "active"             # active | failed | passed
    sl_count: dict = field(default_factory=dict)   # strategy -> stop-losses taken today
    trades_total: int = 0
    wins: int = 0
    losses: int = 0

    def to_dict(self):
        return asdict(self)


def _path(name: str) -> str:
    return os.path.join(STATE_DIR, name)


def load_account() -> AccountState:
    p = _path("account.json")
    if os.path.exists(p):
        with open(p) as f:
            return AccountState(**json.load(f))
    return AccountState()


def save_account(acc: AccountState):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(_path("account.json"), "w") as f:
        json.dump(acc.to_dict(), f, indent=2)


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
