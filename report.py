"""Write the running PnL report (markdown + json) into reports/."""
from __future__ import annotations
import os
import json
import datetime as dt

ROOT = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(ROOT, "reports")


def write_report(acc, positions, now: dt.datetime):
    os.makedirs(REPORTS, exist_ok=True)
    closed = [p for p in positions if p.status == "closed"]
    open_ = [p for p in positions if p.status == "open"]

    by_strat = {}
    for p in closed:
        s = by_strat.setdefault(p.strategy, {"trades": 0, "wins": 0, "pnl": 0.0})
        s["trades"] += 1
        s["wins"] += 1 if p.pnl_usd >= 0 else 0
        s["pnl"] += p.pnl_usd

    summary = {
        "updated": now.isoformat(),
        "status": acc.status,
        "balance": round(acc.balance, 2),
        "equity": round(acc.equity, 2),
        "net_pnl": round(acc.balance - acc.account_size, 2),
        "today_pnl": round(acc.daily_realized_pnl, 2),
        "trades_total": acc.trades_total,
        "wins": acc.wins,
        "losses": acc.losses,
        "win_rate": round(100 * acc.wins / acc.trades_total, 1) if acc.trades_total else 0.0,
        "open_positions": len(open_),
        "by_strategy": by_strat,
    }
    with open(os.path.join(REPORTS, "report.json"), "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Azalyst FundingPips - Paper PnL",
        f"_updated {now:%Y-%m-%d %H:%M UTC}_  |  status: **{acc.status}**",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Balance | ${acc.balance:,.2f} |",
        f"| Equity (incl. open) | ${acc.equity:,.2f} |",
        f"| Net PnL | ${acc.balance - acc.account_size:,.2f} |",
        f"| Today PnL | ${acc.daily_realized_pnl:,.2f} |",
        f"| Trades | {acc.trades_total}  (W {acc.wins} / L {acc.losses}) |",
        f"| Win rate | {summary['win_rate']}% |",
        f"| Open positions | {len(open_)} |",
        "",
        "## By strategy",
        "| Strategy | Trades | Win% | PnL |",
        "|---|---|---|---|",
    ]
    for s, v in sorted(by_strat.items()):
        wr = round(100 * v["wins"] / v["trades"], 0) if v["trades"] else 0
        lines.append(f"| {s} | {v['trades']} | {wr:g}% | ${v['pnl']:,.2f} |")

    if open_:
        lines += ["", "## Open positions",
                  "| Strategy | Symbol | Side | Entry | Stop | Target | Lots | Risk |",
                  "|---|---|---|---|---|---|---|---|"]
        for p in open_:
            lines.append(f"| {p.strategy} | {p.symbol} | {p.side} | {p.entry:g} | "
                         f"{p.stop:g} | {p.target:g} | {p.lots:g} | ${p.risk_usd:,.0f} |")

    if closed:
        lines += ["", "## Recent closed trades (last 15)",
                  "| Closed | Strategy | Symbol | Side | Exit | PnL | R |",
                  "|---|---|---|---|---|---|---|"]
        for p in closed[-15:]:
            ca = (p.closed_at or "")[:16].replace("T", " ")
            lines.append(f"| {ca} | {p.strategy} | {p.symbol} | {p.side} | "
                         f"{p.exit_reason} | ${p.pnl_usd:,.2f} | {p.r_multiple:+g}R |")

    with open(os.path.join(REPORTS, "report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
