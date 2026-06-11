"""Write the running PnL report (markdown + json) into reports/.

Single OB strategy tracking Phase 1 → Phase 2 challenge progress.
"""
from __future__ import annotations
import os
import json
import datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(ROOT, "reports")

_BADGE = {"active": "ACTIVE", "passed": "PASSED", "failed": "FAILED"}


def write_report(books, positions, rules, now: dt.datetime):
    os.makedirs(REPORTS, exist_ok=True)
    closed = [p for p in positions if p.status == "closed"]
    open_ = [p for p in positions if p.status == "open"]

    book_rows = []
    for name, b in books.items():
        net = b.balance - b.account_size
        book_rows.append({
            "strategy": name,
            "status": b.status,
            "phase": b.phase,
            "phase1_days": b.phase1_days,
            "phase2_days": b.phase2_days,
            "failed_reason": b.failed_reason,
            "balance": round(b.balance, 2),
            "equity": round(b.equity, 2),
            "net_pnl": round(net, 2),
            "net_pnl_pct": round(net / b.account_size * 100, 2),
            "trades": b.trades_total,
            "wins": b.wins,
            "losses": b.losses,
            "win_rate": round(100 * b.wins / b.trades_total, 1) if b.trades_total else 0.0,
        })

    summary = {
        "updated": now.isoformat(),
        "model": "ob-phase-challenge",
        "account_size": rules.account_size,
        "phase1_target_pct": rules.profit_target_pct,
        "phase2_target_pct": rules.phase2_target_pct,
        "open_positions": len(open_),
        "books": book_rows,
    }
    with open(os.path.join(REPORTS, "report.json"), "w") as f:
        json.dump(summary, f, indent=2)

    book = book_rows[0] if book_rows else {}
    phase1 = book.get("phase1_days", 0)
    phase2 = book.get("phase2_days", 0)

    lines = [
        "# Azalyst OB Challenge — FundingPips",
        f"_updated {now:%Y-%m-%d %H:%M UTC}_",
        "",
        f"**Order Block (OB) Strategy** — ${rules.account_size:,.0f} challenge. "
        f"Phase 1: +{rules.profit_target_pct:g}% | Phase 2: +{rules.phase2_target_pct:g}%.",
        "",
    ]

    if phase1 > 0:
        lines.append(f"- Phase 1: **{phase1} days** to pass")
    if phase2 > 0:
        lines.append(f"- Phase 2: **{phase2} days** elapsed" + (" (PASSED)" if book.get("status") == "passed" else ""))
    lines.append(f"- Status: **{_BADGE.get(book.get('status','active'), 'ACTIVE')}**")
    lines.append(f"- Balance: ${book.get('balance', 0):,.0f} | Net PnL: ${book.get('net_pnl', 0):,.2f} ({book.get('net_pnl_pct', 0):+g}%)")
    lines.append(f"- Trades: {book.get('trades', 0)} | Win rate: {book.get('win_rate', 0)}%")

    if open_:
        lines += ["", "## Open positions",
                  "| Symbol | Side | Entry | Stop | Target | Lots | Risk |",
                  "|---|---|---|---|---|---|---|"]
        for p in open_:
            lines.append(f"| {p.symbol} | {p.side} | {p.entry:g} | "
                         f"{p.stop:g} | {p.target:g} | {p.lots:g} | ${p.risk_usd:,.0f} |")

    if closed:
        lines += ["", "## Recent closed trades (last 15)",
                  "| Closed | Symbol | Side | Exit | PnL | R |",
                  "|---|---|---|---|---|---|"]
        for p in closed[-15:]:
            ca = (p.closed_at or "")[:16].replace("T", " ")
            lines.append(f"| {ca} | {p.symbol} | {p.side} | "
                         f"{p.exit_reason} | ${p.pnl_usd:,.2f} | {p.r_multiple:+g}R |")

    with open(os.path.join(REPORTS, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
