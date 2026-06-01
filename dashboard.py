"""Build docs/status.json - the payload the GitHub Pages dashboard reads."""
from __future__ import annotations
import os
import json
import datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(ROOT, "docs")
STATE = os.path.join(ROOT, "state")
ACCOUNT_SIZE = 100000.0
MAX_DAILY = 5000.0
MAX_OVERALL = 10000.0
CHALLENGE_START = dt.date(2026, 6, 1)
CHALLENGE_END = dt.date(2026, 6, 30)


def _equity_curve(equity: float, now: dt.datetime) -> list:
    path = os.path.join(STATE, "equity_curve.json")
    curve = []
    if os.path.exists(path):
        try:
            with open(path) as f:
                curve = json.load(f)
        except Exception:
            curve = []
    stamp = now.strftime("%Y-%m-%dT%H:%M")
    if curve and curve[-1].get("t") == stamp:
        curve[-1]["e"] = round(equity, 2)
    else:
        curve.append({"t": stamp, "e": round(equity, 2)})
    curve = curve[-500:]
    with open(path, "w") as f:
        json.dump(curve, f)
    return curve


def build_status(acc, positions, prices: dict, instruments: dict, now: dt.datetime):
    os.makedirs(DOCS, exist_ok=True)
    open_ = [p for p in positions if p.status == "open"]
    closed = [p for p in positions if p.status == "closed"]

    by_strat = {}
    for p in closed:
        s = by_strat.setdefault(p.strategy, {"trades": 0, "wins": 0, "pnl": 0.0})
        s["trades"] += 1
        s["wins"] += 1 if p.pnl_usd >= 0 else 0
        s["pnl"] += p.pnl_usd

    daily_loss_used = max(0.0, acc.today_start_equity - acc.equity)
    overall_loss_used = max(0.0, ACCOUNT_SIZE - acc.equity)
    day_num = (now.date() - CHALLENGE_START).days + 1
    total_days = (CHALLENGE_END - CHALLENGE_START).days + 1

    # ticker tape: map configured instruments -> latest price we fetched this run
    tape = []
    for sym, cfg in instruments.items():
        px = prices.get(cfg["ticker"])
        if px is not None:
            tape.append({"sym": sym, "px": round(px, cfg.get("digits", 2))})

    status = {
        "updated": now.strftime("%Y-%m-%d %H:%M UTC"),
        "updated_iso": now.isoformat(),
        "status": acc.status,
        "challenge": {"day": max(1, day_num), "total": total_days,
                      "start": CHALLENGE_START.isoformat(), "end": CHALLENGE_END.isoformat()},
        "account": {
            "size": ACCOUNT_SIZE,
            "balance": round(acc.balance, 2),
            "equity": round(acc.equity, 2),
            "net_pnl": round(acc.balance - ACCOUNT_SIZE, 2),
            "net_pnl_pct": round((acc.balance - ACCOUNT_SIZE) / ACCOUNT_SIZE * 100, 2),
            "today_pnl": round(acc.daily_realized_pnl, 2),
            "peak_balance": round(acc.peak_balance, 2),
        },
        "objectives": {
            "daily": {"used": round(daily_loss_used, 2), "limit": MAX_DAILY,
                      "remaining": round(max(0.0, MAX_DAILY - daily_loss_used), 2),
                      "threshold": round(acc.today_start_equity - MAX_DAILY, 2)},
            "overall": {"used": round(overall_loss_used, 2), "limit": MAX_OVERALL,
                        "remaining": round(max(0.0, MAX_OVERALL - overall_loss_used), 2),
                        "threshold": ACCOUNT_SIZE - MAX_OVERALL},
        },
        "stats": {
            "trades": acc.trades_total, "wins": acc.wins, "losses": acc.losses,
            "win_rate": round(100 * acc.wins / acc.trades_total, 1) if acc.trades_total else 0.0,
            "open": len(open_),
        },
        "positions": [
            {"strategy": p.strategy, "symbol": p.symbol, "side": p.side,
             "entry": p.entry, "stop": p.stop, "target": p.target,
             "lots": round(p.lots, 4), "risk": round(p.risk_usd, 0),
             "be": p.be_moved, "opened": (p.opened_at or "")[:16].replace("T", " ")}
            for p in open_
        ],
        "closed": [
            {"strategy": p.strategy, "symbol": p.symbol, "side": p.side,
             "exit": p.exit_price, "reason": p.exit_reason,
             "pnl": round(p.pnl_usd, 2), "r": p.r_multiple,
             "closed": (p.closed_at or "")[:16].replace("T", " ")}
            for p in closed[-25:][::-1]
        ],
        "by_strategy": by_strat,
        "tape": tape,
        "equity_curve": _equity_curve(acc.equity, now),
    }
    with open(os.path.join(DOCS, "status.json"), "w") as f:
        json.dump(status, f, indent=2)
    return status
