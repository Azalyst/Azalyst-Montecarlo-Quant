"""Rebel Funding ML Strategy.

Integrates the XGBoost model directly from the Rebel Funding repository.
"""
from __future__ import annotations
import sys
import pandas as pd
from pathlib import Path

# Connect directly to the Rebel Funding repository
REBEL_DIR = Path(r"c:\Users\Administrator\Documents\Rebel Funding")
if str(REBEL_DIR) not in sys.path:
    sys.path.insert(0, str(REBEL_DIR))

try:
    from strategy_analysis.signals.market_state import add_indicators
    from strategy_analysis.signals.strategy import make_signals
    from strategy_analysis.signals.inference_service import predict_batch
    from ea_bot.config_ea import STRATEGIES as REBEL_STRATEGIES
    REBEL_FOUND = True
except ImportError as e:
    REBEL_FOUND = False
    print(f"[rebel_funding] Failed to load Rebel Funding modules: {e}")

from core.models import Signal

NAME = "rebel_funding"

# Map Azalyst symbols to Rebel Funding format if needed
SYM_MAP = {
    "XAUUSD": "XAU_USD",
    "EURUSD": "EUR_USD",
    "GBPUSD": "GBP_USD",
    "NAS100": "USTEC_v",
    "SP500": "US500",
}

def generate(scfg, instruments, fetch, now):
    out = []
    if not REBEL_FOUND:
        return out

    interval = scfg.get("interval", "1h")
    
    for sym in scfg.get("instruments", []):
        inst = instruments[sym]
        df = fetch(inst, interval, bars=200)
        if df is None or len(df) < 50:
            continue

        # Format DataFrame to match Rebel Funding expectations
        df = df.copy()
        df["time"] = df.index
        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["open"] = df["open"].astype(float)

        try:
            # Add mathematical indicators needed for the ML model
            df_ind = add_indicators(df)
        except Exception as e:
            print(f"[rebel_funding] Indicator computation failed for {sym}: {e}")
            continue

        rebel_sym = SYM_MAP.get(sym, sym)
        strat_params = REBEL_STRATEGIES.get(rebel_sym, {
            "rule": "mom_breakout", 
            "params": {"thr": 0.1}, 
            "trail_mult": 3.0
        })

        kind = strat_params["rule"]
        params = strat_params.get("params", {})
        trail_mult = strat_params["trail_mult"]

        # Generate base signal masks
        L, S = make_signals(df_ind, kind, **params)
        
        # Get the latest bar
        bar_idx = len(df_ind) - 1
        if bar_idx < 0:
            continue

        direction = 1 if L.iloc[bar_idx] else (-1 if S.iloc[bar_idx] else 0)
        if direction == 0:
            continue  # No base signal today
            
        # We have a base signal! Evaluate it with the ML model
        recent = df_ind.tail(1).copy()
        try:
            preds = predict_batch(recent)
            p_win = float(preds["p_win"].iloc[-1])
            exp_r = float(preds["expected_r"].iloc[-1])
        except Exception as e:
            print(f"[rebel_funding] ML prediction failed for {sym}: {e}")
            continue

        # Machine Learning Thresholds (from Rebel Funding live_trader.py)
        if p_win < 0.6 or exp_r < 0.2:
            continue  # Filter out bad trades

        # Calculate exact Entry, SL, Target
        row = recent.iloc[-1]
        entry = float(row["close"])
        atr = float(row.get("atr14", 0))
        
        if atr <= 0:
            continue
            
        sl_dist = trail_mult * atr
        stop = entry - direction * sl_dist
        
        # FundingPips target logic: 1:2 RR
        target = entry + direction * (sl_dist * 2.0)

        bar_time = df.index[-1].isoformat()
        
        sig = Signal(
            NAME, sym, "BUY" if direction == 1 else "SELL", 
            round(entry, inst.digits),
            round(stop, inst.digits), 
            round(target, inst.digits), 
            interval, bar_time,
            note=f"ML Approved: P(Win)={p_win:.2%}, E(R)={exp_r:.2f}"
        )
        out.append(sig)

    return out
