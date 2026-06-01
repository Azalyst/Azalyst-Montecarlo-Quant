"""Trading-session windows and session liquidity levels.

NY windows are computed in America/New_York so they stay correct across DST.
Asia window (for the Ethereum Blueprint) follows the doc's ~00:00-08:00 UTC, with
the strategy's "first 2-3 hours" entry window = 00:00-03:00 UTC.
"""
from __future__ import annotations
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def now_utc() -> dt.datetime:
    return dt.datetime.now(tz=UTC)


def in_asia_entry_window(now: dt.datetime | None = None) -> bool:
    """First 3 hours of the Asia session: 00:00-03:00 UTC."""
    now = now or now_utc()
    return 0 <= now.hour < 3


def in_ny_killzone(now: dt.datetime | None = None) -> bool:
    """JadeCap prime window: 09:30-11:30 America/New_York."""
    now = now or now_utc()
    ny = now.astimezone(NY)
    mins = ny.hour * 60 + ny.minute
    return (9 * 60 + 30) <= mins <= (11 * 60 + 30)


def _slice(df: pd.DataFrame, start: dt.datetime, end: dt.datetime) -> pd.DataFrame:
    return df[(df.index >= start) & (df.index < end)]


def session_levels(df: pd.DataFrame, now: dt.datetime | None = None) -> dict:
    """PDH/PDL + Asian and London session highs/lows feeding today's NY session.

    Windows (America/New_York), per the JadeCap playbook:
      Asian  : D-1 20:00 -> D 03:00
      London : D 03:00   -> D 09:30
      PDH/PDL: previous full ET calendar day
    df must be intraday (5m/15m) UTC-indexed with enough history (>= 2 days).
    Returns {} if data is insufficient.
    """
    if df is None or df.empty:
        return {}
    now = now or now_utc()
    ny_now = now.astimezone(NY)
    d = ny_now.date()

    def ny_dt(date, h, m=0):
        return dt.datetime(date.year, date.month, date.day, h, m, tzinfo=NY).astimezone(UTC)

    prev = d - dt.timedelta(days=1)
    asian = _slice(df, ny_dt(prev, 20), ny_dt(d, 3))
    london = _slice(df, ny_dt(d, 3), ny_dt(d, 9, 30))
    pdh_window = _slice(df, ny_dt(prev, 0), ny_dt(d, 0))

    levels = {}
    if not pdh_window.empty:
        levels["PDH"] = float(pdh_window["high"].max())
        levels["PDL"] = float(pdh_window["low"].min())
    if not asian.empty:
        levels["asian_high"] = float(asian["high"].max())
        levels["asian_low"] = float(asian["low"].min())
    if not london.empty:
        levels["london_high"] = float(london["high"].max())
        levels["london_low"] = float(london["low"].min())
    return levels
