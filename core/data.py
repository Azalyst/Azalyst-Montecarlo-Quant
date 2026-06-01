"""Market data layer.

FX / metals / index futures -> yfinance.
Crypto -> Bybit public REST (reliable on GitHub Actions; Binance is geo-blocked there),
          with a yfinance fallback.

Every fetch returns a pandas DataFrame indexed by tz-aware UTC timestamps with
lowercase columns: open, high, low, close, volume. Only *closed* bars are returned
(the still-forming last bar is dropped) so strategies never act on partial candles.
"""
from __future__ import annotations
import time
import warnings
import datetime as dt
from typing import Optional

import requests
import pandas as pd

warnings.filterwarnings("ignore")

_CACHE: dict = {}

# interval -> (yfinance interval, bybit interval, yfinance lookback period)
_INTERVAL_MAP = {
    "5m":  ("5m",  "5",   "5d"),
    "15m": ("15m", "15",  "1mo"),
    "1h":  ("60m", "60",  "3mo"),
    "4h":  ("60m", "240", "3mo"),   # yfinance: resample 1h -> 4h
    "1d":  ("1d",  "D",   "2y"),
}

_BYBIT_URL = "https://api.bybit.com/v5/market/kline"


def _to_utc(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    if idx.tz is None:
        return idx.tz_localize("UTC")
    return idx.tz_convert("UTC")


def _drop_forming_last_bar(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """Drop the final bar if it has not closed yet."""
    if df.empty:
        return df
    secs = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}[interval]
    now = pd.Timestamp.now(tz="UTC")
    last = df.index[-1]
    # a bar stamped at time T closes at T + interval; keep only if fully closed
    if (now - last).total_seconds() < secs:
        df = df.iloc[:-1]
    return df


def _fetch_yfinance(ticker: str, interval: str, bars: int) -> pd.DataFrame:
    import yfinance as yf
    yfi, _, period = _INTERVAL_MAP[interval]
    df = yf.download(ticker, period=period, interval=yfi,
                     progress=False, auto_adjust=True, threads=False)
    if df is None or len(df) == 0:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
    df.index = _to_utc(df.index)
    df = df.dropna()
    if interval == "4h":
        df = (df.resample("4h", label="left", closed="left")
                .agg({"open": "first", "high": "max", "low": "min",
                      "close": "last", "volume": "sum"})
                .dropna())
    return df.tail(bars + 5)


def _fetch_bybit(ticker: str, interval: str, bars: int) -> pd.DataFrame:
    _, byi, _ = _INTERVAL_MAP[interval]
    limit = min(max(bars + 5, 50), 1000)
    params = {"category": "spot", "symbol": ticker, "interval": byi, "limit": limit}
    for attempt in range(3):
        try:
            r = requests.get(_BYBIT_URL, params=params, timeout=15)
            r.raise_for_status()
            rows = r.json().get("result", {}).get("list", [])
            if not rows:
                return pd.DataFrame()
            # bybit returns newest-first: [start, open, high, low, close, volume, turnover]
            rows = rows[::-1]
            df = pd.DataFrame(rows, columns=["ts", "open", "high", "low", "close", "volume", "turnover"])
            df["ts"] = pd.to_datetime(df["ts"].astype("int64"), unit="ms", utc=True)
            df = df.set_index("ts")[["open", "high", "low", "close", "volume"]].astype(float)
            return df
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return pd.DataFrame()


def fetch_ohlc(inst: dict, interval: str, bars: int = 300) -> pd.DataFrame:
    """Fetch OHLC for one instrument config dict. Returns closed bars only."""
    key = (inst["ticker"], interval, bars)
    if key in _CACHE:
        return _CACHE[key]

    src = inst.get("source", "yfinance")
    df = pd.DataFrame()
    if src == "bybit":
        df = _fetch_bybit(inst["ticker"], interval, bars)
        if df.empty:  # fallback: yfinance crypto ticker like BTC-USD
            yf_ticker = inst["ticker"].replace("USDT", "-USD")
            df = _fetch_yfinance(yf_ticker, interval, bars)
    else:
        df = _fetch_yfinance(inst["ticker"], interval, bars)

    if not df.empty:
        df = _drop_forming_last_bar(df, interval)
        df = df[~df.index.duplicated(keep="last")].sort_index()

    _CACHE[key] = df
    return df


def clear_cache():
    _CACHE.clear()
