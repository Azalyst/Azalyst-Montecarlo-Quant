"""Causal H1 indicators + the selected entry rule.

Every value on bar t uses only information available at the CLOSE of bar t.
Entries act on the NEXT bar's open. Ported verbatim (logic-identical) from the
validated research engine so live signals match the backtest.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _ema(s, span):
    return s.ewm(span=span, adjust=False).mean()


def _rsi(close, period=14):
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


def _atr(df, period=14):
    h, l, c = df["high"], df["low"], df["close"]
    pc = c.shift(1)
    tr = pd.concat([(h - l), (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def market_state(df: pd.DataFrame, atr_period: int = 14) -> pd.DataFrame:
    """Add causal indicators. Input: OHLC frame indexed by time."""
    out = df[["open", "high", "low", "close"]].copy()
    out["ema20"] = _ema(out["close"], 20)
    out["ema50"] = _ema(out["close"], 50)
    out["rsi"] = _rsi(out["close"], 14)
    out["atr"] = _atr(out, atr_period)
    hi20 = out["high"].rolling(20).max().shift(1)
    lo20 = out["low"].rolling(20).min().shift(1)
    out["dist_hi_atr"] = (hi20 - out["close"]) / out["atr"]
    out["dist_lo_atr"] = (out["close"] - lo20) / out["atr"]
    out["trend_up"] = out["ema20"] > out["ema50"]
    return out.dropna(subset=["atr", "ema50", "dist_hi_atr", "dist_lo_atr"]).copy()


def mom_breakout_signal(state: pd.DataFrame, thr: float = 0.05) -> pd.DataFrame:
    """Long when price is within thr*ATR of the prior 20-bar high AND trend up;
    short symmetrically. Returns the state frame with long/short boolean columns."""
    state = state.copy()
    state["long"] = (state["dist_hi_atr"] <= thr) & state["trend_up"]
    state["short"] = (state["dist_lo_atr"] <= thr) & (~state["trend_up"])
    return state


SIGNALS = {"mom_breakout": mom_breakout_signal}


def compute_signals(df: pd.DataFrame, rule: str, params: dict,
                    atr_period: int = 14) -> pd.DataFrame:
    st = market_state(df, atr_period=atr_period)
    return SIGNALS[rule](st, **params)
