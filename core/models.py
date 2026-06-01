"""Shared data models."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import hashlib


@dataclass
class Signal:
    """A trade signal produced by a strategy."""
    strategy: str
    symbol: str
    side: str            # "BUY" or "SELL"
    entry: float
    stop: float
    target: float
    interval: str
    setup_bar: str       # ISO timestamp of the bar that produced the setup (for dedupe)
    rr: float = 0.0
    note: str = ""

    @property
    def stop_distance(self) -> float:
        return abs(self.entry - self.stop)

    @property
    def dedupe_key(self) -> str:
        raw = f"{self.strategy}|{self.symbol}|{self.side}|{self.setup_bar}"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def compute_rr(self) -> float:
        risk = abs(self.entry - self.stop)
        reward = abs(self.target - self.entry)
        return round(reward / risk, 2) if risk > 0 else 0.0


@dataclass
class Position:
    """An open or closed paper position."""
    id: str
    strategy: str
    symbol: str
    side: str
    entry: float
    stop: float
    target: float
    units: float
    lots: float
    risk_usd: float
    opened_at: str
    interval: str
    initial_stop: float = 0.0      # for break-even / trailing reference
    be_moved: bool = False
    status: str = "open"           # open | closed
    exit_price: Optional[float] = None
    closed_at: Optional[str] = None
    pnl_usd: float = 0.0
    r_multiple: float = 0.0
    exit_reason: str = ""          # tp | sl | be | manual

    def to_dict(self) -> dict:
        return asdict(self)
