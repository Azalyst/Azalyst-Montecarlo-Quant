"""Live market data — gold H1 via yfinance (GC=F).

Reliable on GitHub Actions, no API key. Returns a DataFrame indexed by tz-aware
UTC timestamps with lowercase columns open/high/low/close/volume, and only
*closed* bars (the still-forming last bar is dropped) so the engine never acts on
a partial candle. Gold futures (GC=F) track spot to within a few dollars and the
strategy is scale-invariant (ATR-relative), so this is a faithful live proxy for
the broker XAU/USD the strategy was validated on.
"""
from __future__ import annotations

import time
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

# our interval -> (yfinance interval, lookback period)
_MAP = {
    "1h": ("60m", "3mo"),
    "4h": ("60m", "3mo"),
    "1d": ("1d", "2y"),
}
_SECS = {"1h": 3600, "4h": 14400, "1d": 86400}


def _to_utc(idx) -> pd.DatetimeIndex:
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")


def _drop_forming(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    if df.empty:
        return df
    now = pd.Timestamp.now(tz="UTC")
    if (now - df.index[-1]).total_seconds() < _SECS[interval]:
        df = df.iloc[:-1]
    return df


def fetch_gold(ticker: str = "GC=F", interval: str = "1h", bars: int = 400,
               retries: int = 3) -> pd.DataFrame:
    """Fetch closed gold candles. Retries to ride out yfinance flakiness on CI."""
    import yfinance as yf
    yfi, period = _MAP[interval]
    last_err = None
    for attempt in range(retries):
        try:
            df = yf.download(ticker, period=period, interval=yfi,
                             progress=False, auto_adjust=True, threads=False)
            if df is not None and len(df):
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df = df.rename(columns=str.lower)[["open", "high", "low", "close", "volume"]]
                df.index = _to_utc(df.index)
                df = df.dropna()
                if interval == "4h":
                    df = (df.resample("4h", label="left", closed="left")
                            .agg({"open": "first", "high": "max", "low": "min",
                                  "close": "last", "volume": "sum"}).dropna())
                df = _drop_forming(df, interval)
                df = df[~df.index.duplicated(keep="last")].sort_index()
                return df.tail(bars)
        except Exception as e:  # network / rate-limit
            last_err = e
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"gold fetch failed after {retries} tries: {last_err}")


if __name__ == "__main__":
    df = fetch_gold()
    print(f"gold H1: {len(df)} closed bars, {df.index.min()} -> {df.index.max()}")
    print(df.tail(3).to_string())
