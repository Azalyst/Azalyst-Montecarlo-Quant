"""Technical indicators and price-structure helpers (pandas/numpy)."""
from __future__ import annotations
import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(100.0)  # zero losses -> max strength


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return true_range(df).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def macd(series: pd.Series, fast=12, slow=26, signal=9):
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def session_vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP reset each UTC day."""
    tp = (df["high"] + df["low"] + df["close"]) / 3.0
    day = df.index.normalize()
    pv = (tp * df["volume"]).groupby(day).cumsum()
    vol = df["volume"].groupby(day).cumsum().replace(0, np.nan)
    return (pv / vol).fillna(tp)


def swing_points(df: pd.DataFrame, strength: int = 2):
    """Return (highs, lows) boolean Series marking confirmed swing pivots.

    A swing high at i needs `strength` lower highs on each side. Pivots are only
    confirmed `strength` bars later, so this never looks into the future.
    """
    h, l = df["high"].values, df["low"].values
    n = len(df)
    is_high = np.zeros(n, dtype=bool)
    is_low = np.zeros(n, dtype=bool)
    for i in range(strength, n - strength):
        window_h = h[i - strength:i + strength + 1]
        window_l = l[i - strength:i + strength + 1]
        if h[i] == window_h.max() and (window_h == h[i]).sum() == 1:
            is_high[i] = True
        if l[i] == window_l.min() and (window_l == l[i]).sum() == 1:
            is_low[i] = True
    return pd.Series(is_high, index=df.index), pd.Series(is_low, index=df.index)


def last_swings(df: pd.DataFrame, strength: int = 2, n: int = 3):
    """Most recent confirmed swing highs and lows as lists of (timestamp, price)."""
    hi, lo = swing_points(df, strength)
    highs = [(t, df.loc[t, "high"]) for t in df.index[hi]][-n:]
    lows = [(t, df.loc[t, "low"]) for t in df.index[lo]][-n:]
    return highs, lows


def bullish_fvg(df: pd.DataFrame, i: int) -> bool:
    """3-candle bullish fair value gap ending at index i (gap between i-2 high and i low)."""
    if i < 2:
        return False
    return df["low"].iloc[i] > df["high"].iloc[i - 2]


def bearish_fvg(df: pd.DataFrame, i: int) -> bool:
    if i < 2:
        return False
    return df["high"].iloc[i] < df["low"].iloc[i - 2]


def trend_structure(df: pd.DataFrame, strength: int = 3) -> str:
    """Classify HTF structure as 'bull', 'bear', or 'range' from last two swings."""
    highs, lows = last_swings(df, strength=strength, n=3)
    if len(highs) < 2 or len(lows) < 2:
        return "range"
    hh = highs[-1][1] > highs[-2][1]
    hl = lows[-1][1] > lows[-2][1]
    lh = highs[-1][1] < highs[-2][1]
    ll = lows[-1][1] < lows[-2][1]
    if hh and hl:
        return "bull"
    if lh and ll:
        return "bear"
    return "range"
