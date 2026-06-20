#!/usr/bin/env python3
"""
Azalyst Montecarlo — one tick of the live engine.

Run by GitHub Actions on a schedule (and locally for testing):

    python run.py                 # fetch gold -> advance challenge -> dashboard -> alerts
    python run.py --test-discord  # send a webhook connectivity test only
    python run.py --reset         # reset the challenge to a fresh Phase 1 account

Flow: load config + state -> fetch closed gold H1 bars -> compute signals ->
challenge.tick() -> persist state -> write dashboard feed -> Discord on events.
Idempotent: only newly-closed bars are processed, so extra ticks are harmless.
"""
from __future__ import annotations

import sys
import os
import json
import argparse

import yaml

from engine import data as D
from engine import indicators as I
from engine import challenge as CH
from engine import dashboard as DB
from engine.notify import Notifier

STATE_PATH = "state/challenge.json"
CONFIG_PATH = "config.yaml"


def load_cfg():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_state(cfg):
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[warn] state unreadable ({e}); starting fresh")
    return CH.fresh_state(cfg)


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-discord", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    cfg = load_cfg()
    notifier = Notifier(cfg)

    if args.test_discord:
        notifier.test()
        return

    if args.reset:
        state = CH.fresh_state(cfg)
        save_state(state)
        DB.write_status(state, cfg)
        print("Challenge reset to a fresh Phase 1 account.")
        return

    state = load_state(cfg)

    inst, strat = cfg["instrument"], cfg["strategy"]
    try:
        df = D.fetch_gold(inst["ticker"], inst["interval"], bars=400)
    except Exception as e:
        # a sustained data outage should skip the tick cleanly, not fail the Action
        print(f"[warn] gold fetch failed ({e}); skipping tick")
        DB.write_status(state, cfg)
        return
    if df is None or len(df) < 60:
        print(f"[warn] insufficient gold data ({0 if df is None else len(df)} bars); skipping tick")
        DB.write_status(state, cfg)
        return
    signals = I.compute_signals(df, strat["rule"], strat["params"],
                                atr_period=strat["atr_period"])

    state, events = CH.tick(state, signals, cfg)
    save_state(state)
    status = DB.write_status(state, cfg)

    for ev in events:
        notifier.event(ev, state)

    px = float(df["close"].iloc[-1])
    print(f"tick ok | phase={state['phase']} bal=${state['balance']:,.0f} "
          f"eq=${state['equity']:,.0f} gold={px:.2f} "
          f"pos={'yes' if state['position'] else 'flat'} events={len(events)}")
    for ev in events:
        print(f"  - [{ev.kind}] {ev.title} :: {ev.detail}")


if __name__ == "__main__":
    main()
