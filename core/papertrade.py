"""Paper-trade execution: open positions and resolve them bar-by-bar.

Fills are conservative: if a single bar touches both the stop and the target, the
stop is assumed hit first. Break-even moves (Ethereum Blueprint) are modelled; the
remaining strategies use plain stop/target exits.
"""
from __future__ import annotations
import time
import pandas as pd
from .models import Signal, Position


def _uid(sig: Signal) -> str:
    return f"{sig.strategy}-{sig.symbol}-{int(time.time()*1000)}"


def open_position(sig: Signal, units: float, lots: float, risk_usd: float,
                  now_iso: str) -> Position:
    return Position(
        id=_uid(sig), strategy=sig.strategy, symbol=sig.symbol, side=sig.side,
        entry=sig.entry, stop=sig.stop, target=sig.target, units=units, lots=lots,
        risk_usd=risk_usd, opened_at=now_iso, interval=sig.interval,
        initial_stop=sig.stop, status="open",
    )


def worst_case_loss(pos: Position) -> float:
    """USD still at risk if the stop is hit (0 once moved to break-even)."""
    return 0.0 if (pos.be_moved and abs(pos.stop - pos.entry) < 1e-9) else pos.risk_usd


def update_position(pos: Position, df: pd.DataFrame, value_per_point: float,
                    use_breakeven: bool = False) -> float:
    """Resolve an open position against bars that printed after entry.

    Returns realized PnL (0.0 if it is still open). Mutates pos in place.
    """
    if pos.status != "open" or df is None or df.empty:
        return 0.0
    opened = pd.Timestamp(pos.opened_at)
    bars = df[df.index > opened]
    if bars.empty:
        return 0.0

    dirn = 1 if pos.side == "BUY" else -1
    r = abs(pos.entry - pos.initial_stop)

    for ts, row in bars.iterrows():
        hi, lo = float(row["high"]), float(row["low"])

        if use_breakeven and not pos.be_moved and r > 0:
            if dirn == 1 and hi >= pos.entry + r:
                pos.stop, pos.be_moved = pos.entry, True
            elif dirn == -1 and lo <= pos.entry - r:
                pos.stop, pos.be_moved = pos.entry, True

        hit_sl = (lo <= pos.stop) if dirn == 1 else (hi >= pos.stop)
        hit_tp = (hi >= pos.target) if dirn == 1 else (lo <= pos.target)

        exit_price = reason = None
        if hit_sl and hit_tp:
            exit_price, reason = pos.stop, ("be" if pos.be_moved and abs(pos.stop - pos.entry) < 1e-9 else "sl")
        elif hit_sl:
            exit_price, reason = pos.stop, ("be" if pos.be_moved and abs(pos.stop - pos.entry) < 1e-9 else "sl")
        elif hit_tp:
            exit_price, reason = pos.target, "tp"

        if exit_price is not None:
            pnl = (exit_price - pos.entry) * dirn * pos.units * value_per_point
            pos.status = "closed"
            pos.exit_price = float(exit_price)
            pos.closed_at = ts.isoformat()
            pos.pnl_usd = round(pnl, 2)
            pos.r_multiple = round(pnl / pos.risk_usd, 2) if pos.risk_usd else 0.0
            pos.exit_reason = reason
            return pos.pnl_usd
    return 0.0


def mark_to_market(pos: Position, last_price: float, value_per_point: float) -> float:
    """Unrealized PnL for an open position at the latest price."""
    if pos.status != "open":
        return 0.0
    dirn = 1 if pos.side == "BUY" else -1
    return (last_price - pos.entry) * dirn * pos.units * value_per_point
