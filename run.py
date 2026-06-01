#!/usr/bin/env python3
"""Azalyst FundingPips Signal Engine - orchestrator.

One invocation = one cron tick:
  1. roll the FundingPips trading day (daily-loss reset)
  2. resolve open paper positions against fresh bars (SL/TP/break-even)
  3. mark equity, enforce max-loss / daily-loss status
  4. generate fresh signals from every enabled strategy
  5. risk-gate, size, open paper trades, and alert Discord
  6. persist state + write the PnL report

Usage:
  python run.py [--dry-run] [--test-discord] [--once]
"""
from __future__ import annotations
import os
import sys
import argparse
import yaml

try:                       # keep emoji/arrows printable on Windows consoles (cp1252)
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from core import data
from core.risk import FundingPipsRules
from core.sessions import now_utc
from core.state import (load_account, save_account, load_positions, save_positions,
                        load_sent, save_sent)
from core.notify import Notifier
from core import papertrade as pt
import strategies
from report import write_report

ROOT = os.path.dirname(os.path.abspath(__file__))
SL_REASONS = {"sl"}
EMA5_DAILY_SL_CAP = 3


def load_config():
    with open(os.path.join(ROOT, "config.yaml")) as f:
        return yaml.safe_load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print instead of posting to Discord")
    ap.add_argument("--test-discord", action="store_true", help="send a connectivity test and exit")
    args = ap.parse_args()

    cfg = load_config()
    rules = FundingPipsRules(cfg)
    instruments = cfg["instruments"]
    now = now_utc()

    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    notifier = Notifier(webhook, cfg["discord"]["user_id"], dry_run=args.dry_run)

    if args.test_discord:
        notifier.alert("Signal engine online",
                       f"Connectivity test OK. {now:%Y-%m-%d %H:%M UTC}. "
                       f"Account ${rules.account_size:,.0f}, risk {rules.risk_pct}%/trade.",
                       color=0x3498DB)
        return

    acc = load_account()
    acc.account_size = rules.account_size
    positions = load_positions()
    sent = load_sent()

    def fetch(inst, interval, bars=300):
        return data.fetch_ohlc(inst, interval, bars)

    # ---- 1. daily roll (FundingPips server day) ----
    day = rules.server_day(now)
    if acc.current_day != day:
        acc.current_day = day
        acc.today_start_equity = acc.equity
        acc.daily_realized_pnl = 0.0
        acc.sl_count = {}

    # ---- 2. resolve open positions ----
    open_positions = [p for p in positions if p.status == "open"]
    for pos in open_positions:
        inst = instruments[pos.symbol]
        df = fetch(inst, pos.interval, bars=300)
        use_be = pos.strategy in strategies.BREAKEVEN_STRATEGIES
        pnl = pt.update_position(pos, df, inst["value_per_point"], use_breakeven=use_be)
        if pos.status == "closed":
            acc.balance += pnl
            acc.daily_realized_pnl += pnl
            acc.trades_total += 1
            if pnl >= 0:
                acc.wins += 1
            else:
                acc.losses += 1
            if pos.exit_reason in SL_REASONS:
                acc.sl_count[pos.strategy] = acc.sl_count.get(pos.strategy, 0) + 1
            notifier.close(pos, acc)

    # ---- 3. mark equity + status ----
    open_positions = [p for p in positions if p.status == "open"]
    unrealized = 0.0
    for pos in open_positions:
        inst = instruments[pos.symbol]
        df = fetch(inst, pos.interval, bars=50)
        if df is not None and len(df):
            unrealized += pt.mark_to_market(pos, float(df["close"].iloc[-1]), inst["value_per_point"])
    acc.equity = round(acc.balance + unrealized, 2)
    acc.peak_balance = max(acc.peak_balance, acc.balance)

    if acc.status == "active" and acc.equity <= rules.overall_floor:
        acc.status = "failed"
        notifier.alert("MAX LOSS BREACHED - challenge failed",
                       f"Equity ${acc.equity:,.0f} hit the ${rules.overall_floor:,.0f} floor. "
                       f"No new trades will be opened.", color=0xE74C3C)

    daily_loss = max(0.0, acc.today_start_equity - acc.equity)
    if acc.status == "active" and daily_loss >= rules.max_daily_loss:
        notifier.alert("DAILY LOSS LIMIT HIT",
                       f"Down ${daily_loss:,.0f} today (limit ${rules.max_daily_loss:,.0f}). "
                       f"New trades paused until the daily reset.", color=0xE67E22)

    # ---- 4 + 5. generate, gate, size, open ----
    open_by_symbol = {}
    for p in open_positions:
        open_by_symbol.setdefault(p.symbol, []).append(p)

    new_signals = []
    for name, scfg in cfg["strategies"].items():
        if not scfg.get("enabled"):
            continue
        mod = strategies.REGISTRY.get(name)
        if not mod:
            continue
        try:
            new_signals += mod.generate(scfg, instruments, fetch, now)
        except Exception as e:
            print(f"[strategy {name}] error: {e}")

    for sig in new_signals:
        sig.rr = sig.compute_rr()
        key = sig.dedupe_key
        if key in sent:
            continue
        # no duplicate same strategy+symbol open; no conflicting opposite open
        existing = open_by_symbol.get(sig.symbol, [])
        if any(p.strategy == sig.strategy for p in existing):
            continue
        if any(p.side != sig.side for p in existing):
            continue
        # 5 EMA 3-SL daily rule
        if sig.strategy == "ema5" and acc.sl_count.get("ema5", 0) >= EMA5_DAILY_SL_CAP:
            continue

        inst = instruments[sig.symbol]
        units, lots = rules.size_position(sig.stop_distance, inst["value_per_point"], inst["lot_units"])
        if units <= 0:
            continue
        ok, reason = rules.validate_trade(sig, inst, units)
        if not ok:
            print(f"[skip] {sig.strategy} {sig.symbol} {sig.side}: {reason}")
            continue
        risk_usd = rules.risk_usd()

        worst_open = sum(pt.worst_case_loss(p) for p in positions if p.status == "open")
        ok, reason = rules.gate(acc, worst_open, risk_usd, now)
        if not ok:
            print(f"[gate] blocked {sig.strategy} {sig.symbol} {sig.side}: {reason}")
            continue

        pos = pt.open_position(sig, units, lots, risk_usd, now.isoformat())
        positions.append(pos)
        open_by_symbol.setdefault(sig.symbol, []).append(pos)
        sent.add(key)
        notifier.signal(sig, pos, acc)
        print(f"[open] {sig.strategy} {sig.symbol} {sig.side} @ {sig.entry:g} "
              f"SL {sig.stop:g} TP {sig.target:g} ({lots:g} lots)")

    # ---- 6. persist + report ----
    save_account(acc)
    save_positions(positions)
    save_sent(sent)
    write_report(acc, positions, now)
    print(f"[done] equity ${acc.equity:,.2f} | day PnL ${acc.daily_realized_pnl:,.2f} | "
          f"open {len([p for p in positions if p.status=='open'])} | status {acc.status}")


if __name__ == "__main__":
    main()
