"""FundingPips rule engine + position sizing.

The gate enforces the rules so they cannot be broken even if every open stop is hit:
a new trade is rejected unless
    realized_loss_today + worst_case_open_risk + new_trade_risk  <=  daily_budget
and
    equity - worst_case_open_risk - new_trade_risk  >=  overall_floor
"""
from __future__ import annotations
import datetime as dt
from .state import Book


class FundingPipsRules:
    def __init__(self, cfg: dict):
        a = cfg["account"]
        r = cfg["risk"]
        self.account_size = float(a["size"])
        self.max_daily_loss = float(a["max_daily_loss"])
        self.max_overall_loss = float(a["max_overall_loss"])
        self.profit_target_pct = float(a.get("profit_target_pct", 8.0))
        self.reset_hour = int(a["daily_reset_utc_hour"])
        self.start = dt.date.fromisoformat(a["challenge_start"])
        self.end = dt.date.fromisoformat(a["challenge_end"])
        self.risk_pct = float(r["risk_per_trade_pct"])
        self.buffer = float(r["safety_buffer"])
        self.max_leverage = float(r.get("max_leverage", 30))

    # ---- challenge window ----
    def within_challenge(self, now: dt.datetime) -> bool:
        return self.start <= now.date() <= self.end

    # ---- FundingPips "server day" key (for the daily-loss reset) ----
    def server_day(self, now: dt.datetime) -> str:
        shifted = now - dt.timedelta(hours=self.reset_hour)
        return shifted.date().isoformat()

    # ---- sizing ----
    def risk_usd(self) -> float:
        return self.account_size * self.risk_pct / 100.0

    def size_position(self, stop_distance: float, value_per_point: float, lot_units: int):
        """Return (units, lots) sized so a stop-out loses exactly risk_usd."""
        if stop_distance <= 0:
            return 0.0, 0.0
        units = self.risk_usd() / (stop_distance * value_per_point)
        lots = units / lot_units
        return units, lots

    def validate_trade(self, sig, inst: dict, units: float) -> tuple[bool, str]:
        """Reject noise-tight stops and over-leveraged sizes before opening."""
        min_stop = float(inst.get("min_stop", 0.0))
        if sig.stop_distance < min_stop:
            return False, f"stop {sig.stop_distance:g} < min {min_stop:g} (noise filter)"
        # notional in USD ~ units * price (exact for fx/metal/crypto; index is $/pt CFD)
        if inst.get("asset") in ("fx", "metal", "crypto"):
            notional = units * sig.entry
            if notional > self.max_leverage * self.account_size:
                lev = notional / self.account_size
                return False, f"notional ${notional:,.0f} = {lev:.0f}x > {self.max_leverage:g}x cap"
        return True, "ok"

    # ---- limits ----
    @property
    def overall_floor(self) -> float:
        return self.account_size - self.max_overall_loss   # $90,000

    @property
    def pass_threshold(self) -> float:
        # balance at/above this = challenge PASSED (e.g. +8% -> $108,000)
        return self.account_size * (1.0 + self.profit_target_pct / 100.0)

    def daily_budget(self) -> float:
        return self.max_daily_loss * self.buffer

    def overall_budget_equity(self) -> float:
        # usable floor with safety buffer
        return self.account_size - self.max_overall_loss * self.buffer

    def gate(self, acc: Book, worst_case_open: float, new_risk: float,
             now: dt.datetime) -> tuple[bool, str]:
        if acc.status != "active":
            return False, f"account {acc.status}"
        if not self.within_challenge(now):
            return False, "outside challenge window"

        realized_loss_today = max(0.0, -acc.daily_realized_pnl)
        if realized_loss_today + worst_case_open + new_risk > self.daily_budget():
            return False, (f"daily-loss gate: used ${realized_loss_today:,.0f} + open risk "
                           f"${worst_case_open:,.0f} + trade ${new_risk:,.0f} "
                           f"> budget ${self.daily_budget():,.0f}")

        if acc.equity - worst_case_open - new_risk < self.overall_budget_equity():
            return False, (f"max-loss gate: equity ${acc.equity:,.0f} - open ${worst_case_open:,.0f} "
                           f"- trade ${new_risk:,.0f} < floor ${self.overall_budget_equity():,.0f}")
        return True, "ok"
