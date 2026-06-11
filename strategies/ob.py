"""Order Block strategy - ICT/SMC concept.

Detects order blocks on the 4h HTF (the last candle before a strong momentum
break), then enters on the 15m when price retraces into the OB zone with
confirmation. Uses ATR-based stops and 1:2 RR targets.
"""
from __future__ import annotations
import pandas as pd
from core.models import Signal
from core import indicators as ind

NAME = "ob"


def generate(scfg, instruments, fetch, now):
    out = []
    interval = scfg.get("interval", "15m")
    htf_interval = scfg.get("htf_interval", "4h")
    rr = scfg.get("rr_ratio", 2.0)
    ob_lookback = scfg.get("ob_lookback", 20)

    for sym in scfg.get("instruments", []):
        inst = instruments[sym]
        df_15m = fetch(inst, interval, bars=400)
        df_4h = fetch(inst, htf_interval, bars=200)
        if df_15m is None or len(df_15m) < 60:
            continue
        if df_4h is None or len(df_4h) < 10:
            continue

        # Find OB on 4h
        ob = _find_order_block(df_4h, ob_lookback)
        if ob is None:
            continue

        # Check for entry on 15m retrace into the OB
        sig = _check_entry_15m(sym, df_15m, ob, interval, rr)
        if sig:
            out.append(sig)

    return out


def _find_order_block(df_4h: pd.DataFrame, lookback: int = 20):
    """Find the most recent order block on the 4h chart.

    Bullish OB: A bearish candle (close < open) followed by a strong bullish candle
    that closes above the bearish candle's high. The OB zone is the bearish candle's
    high-low range.

    Bearish OB: A bullish candle (close > open) followed by a strong bearish candle
    that closes below the bullish candle's low. The OB zone is the bullish candle's
    high-low range.

    Only considers OBs from the last `lookback` candles.
    """
    recent = df_4h.tail(lookback)
    if len(recent) < 3:
        return None

    atr_val = float(ind.atr(df_4h, 14).iloc[-1])
    if atr_val <= 0:
        return None

    # Scan from most recent backwards
    closes = recent["close"].values
    opens = recent["open"].values
    highs = recent["high"].values
    lows = recent["low"].values
    volumes = recent["volume"].values

    n = len(recent)
    for i in range(n - 2, 0, -1):
        # Bullish OB: candle i is bearish, candle i+1 is bullish and breaks above i's high
        c_i_close = float(closes[i])
        c_i_open = float(opens[i])
        c_i_high = float(highs[i])
        c_i_low = float(lows[i])
        c_i_vol = float(volumes[i])

        c_next_close = float(closes[i + 1])
        c_next_open = float(opens[i + 1])
        c_next_high = float(highs[i + 1])
        c_next_low = float(lows[i + 1])

        # Bullish OB
        if c_i_close < c_i_open and c_next_close > c_next_open:
            # Momentum candle closes above the OB candle's high
            if c_next_close > c_i_high:
                # Candle body must have at least 30% of ATR for significance
                body = abs(c_next_close - c_next_open)
                if body > atr_val * 0.3:
                    ob_high = c_i_high
                    ob_low = c_i_low
                    ob_mid = (ob_high + ob_low) / 2
                    bar = df_4h.index[i].isoformat()
                    return {
                        "type": "bullish",
                        "ob_high": ob_high,
                        "ob_low": ob_low,
                        "ob_mid": ob_mid,
                        "atr": atr_val,
                        "bar": bar,
                    }

        # Bearish OB
        if c_i_close > c_i_open and c_next_close < c_next_open:
            if c_next_close < c_i_low:
                body = abs(c_next_close - c_next_open)
                if body > atr_val * 0.3:
                    ob_high = c_i_high
                    ob_low = c_i_low
                    ob_mid = (ob_high + ob_low) / 2
                    bar = df_4h.index[i].isoformat()
                    return {
                        "type": "bearish",
                        "ob_high": ob_high,
                        "ob_low": ob_low,
                        "ob_mid": ob_mid,
                        "atr": atr_val,
                        "bar": bar,
                    }

    return None


def _check_entry_15m(sym: str, df_15m: pd.DataFrame, ob: dict,
                     interval: str, rr: float):
    """Check if the 15m chart shows a retrace into the OB for entry.

    Long: Price retraces into the bullish OB zone. Entry at the OB high.
    Stop at OB low - 0.5 ATR. Target at entry + rr * (entry - stop).

    Short: Price retraces into the bearish OB zone. Entry at the OB low.
    Stop at OB high + 0.5 ATR. Target at entry - rr * (stop - entry).
    """
    atr15 = float(ind.atr(df_15m, 14).iloc[-1])
    if atr15 <= 0:
        return None

    recent = df_15m.tail(5)
    last_close = float(df_15m["close"].iloc[-1])
    last_low = float(df_15m["low"].iloc[-1])
    last_high = float(df_15m["high"].iloc[-1])

    if ob["type"] == "bullish":
        # Price must have touched into the OB zone in recent bars
        if last_low <= ob["ob_high"] and last_close > ob["ob_low"]:
            entry = ob["ob_high"]
            stop = ob["ob_low"] - atr15 * 0.3
            target = entry + rr * (entry - stop)
            bar = df_15m.index[-1].isoformat()
            return Signal(
                NAME, sym, "BUY", round(entry, 5),
                round(stop, 5), round(target, 5), interval, bar,
                note=f"OB bullish: retrace into {ob['ob_low']:.5f}-{ob['ob_high']:.5f}",
            )
    else:
        if last_high >= ob["ob_low"] and last_close < ob["ob_high"]:
            entry = ob["ob_low"]
            stop = ob["ob_high"] + atr15 * 0.3
            target = entry - rr * (stop - entry)
            bar = df_15m.index[-1].isoformat()
            return Signal(
                NAME, sym, "SELL", round(entry, 5),
                round(stop, 5), round(target, 5), interval, bar,
                note=f"OB bearish: retrace into {ob['ob_low']:.5f}-{ob['ob_high']:.5f}",
            )

    return None
