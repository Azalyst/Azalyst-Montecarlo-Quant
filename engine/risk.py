"""Phase-aware risk engine — the part that keeps the account funded.

The reverse-engineering verdict: people fail a 2-step by letting ONE trade or ONE
day lose too much (tripping the 5% daily line), not by missing the target. So
sizing is small and governed. Calibration (Monte-Carlo risk sweep): 0.5–0.75%
per trade -> ~88% full-pass, ~0% daily-bust.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    initial_balance: float
    phase1_risk: float          # fractions, e.g. 0.0075
    phase2_risk: float
    daily_loss_stop: float      # e.g. 0.03
    total_dd_brake: float       # e.g. 0.07
    max_trades_per_day: int
    lockin_band: float          # e.g. 0.015
    max_daily_loss: float       # hard, 0.05
    max_total_loss: float       # hard, 0.10
    p1_target: float            # 0.08
    p2_target: float            # 0.05

    @classmethod
    def from_yaml(cls, cfg: dict):
        a, r, s = cfg["account"], cfg["risk"], cfg["strategy"]
        return cls(
            initial_balance=a["size"],
            phase1_risk=r["phase1_risk_pct"] / 100,
            phase2_risk=r["phase2_risk_pct"] / 100,
            daily_loss_stop=r["daily_loss_stop_pct"] / 100,
            total_dd_brake=r["total_dd_brake_pct"] / 100,
            max_trades_per_day=int(r["max_trades_per_day"]),
            lockin_band=r["lockin_band_pct"] / 100,
            max_daily_loss=a["max_daily_loss_pct"] / 100,
            max_total_loss=a["max_overall_loss_pct"] / 100,
            p1_target=a["profit_target_p1_pct"] / 100,
            p2_target=a["profit_target_p2_pct"] / 100,
        )


@dataclass
class Sizing:
    allowed: bool
    reason: str
    risk_fraction: float = 0.0
    risk_amount: float = 0.0
    size_units: float = 0.0
    lots: float = 0.0


class RiskEngine:
    def __init__(self, rc: RiskConfig, lot_units: float = 100.0):
        self.rc = rc
        self.lot_units = lot_units

    # ---- hard rule lines (absolute equity) ----
    def daily_floor(self, day_anchor: float) -> float:
        return day_anchor - self.rc.max_daily_loss * self.rc.initial_balance

    def static_floor(self) -> float:
        return self.rc.initial_balance - self.rc.max_total_loss * self.rc.initial_balance

    def phase_target_balance(self, phase: str) -> float:
        t = self.rc.p2_target if phase == "phase2" else self.rc.p1_target
        if phase == "funded":
            return float("inf")
        return self.rc.initial_balance + t * self.rc.initial_balance

    def phase_risk(self, phase: str) -> float:
        return self.rc.phase1_risk if phase == "phase1" else self.rc.phase2_risk

    # ---- soft governors ----
    def can_trade(self, phase, balance, equity, day_anchor, trades_today):
        day_loss = (day_anchor - equity) / self.rc.initial_balance
        if day_loss >= self.rc.daily_loss_stop:
            return False, f"daily soft-stop ({day_loss*100:.1f}% >= {self.rc.daily_loss_stop*100:.1f}%)"
        if trades_today >= self.rc.max_trades_per_day:
            return False, "max trades/day reached"
        total_loss = (self.rc.initial_balance - equity) / self.rc.initial_balance
        if total_loss >= self.rc.total_dd_brake:
            return False, f"total-DD brake ({total_loss*100:.1f}% >= {self.rc.total_dd_brake*100:.1f}%)"
        return True, "ok"

    def size(self, phase, balance, equity, day_anchor, trades_today,
             stop_distance: float) -> Sizing:
        ok, why = self.can_trade(phase, balance, equity, day_anchor, trades_today)
        if not ok:
            return Sizing(False, why)
        if stop_distance <= 0:
            return Sizing(False, "invalid stop distance")

        frac = self.phase_risk(phase)
        target = self.phase_target_balance(phase)

        # lock-in: shrink within the lock-in band of the target
        if target != float("inf"):
            to_go = (target - balance) / self.rc.initial_balance
            if 0 < to_go <= self.rc.lockin_band:
                frac *= 0.5

        # throttle as we approach the daily soft-stop
        day_loss = max(0.0, (day_anchor - equity) / self.rc.initial_balance)
        room = self.rc.daily_loss_stop - day_loss
        if room < frac * 1.5:
            frac = max(0.0, room / 1.5)
        if frac <= 0:
            return Sizing(False, "no daily room for a full-risk trade")

        risk_amount = frac * balance
        size_units = risk_amount / stop_distance
        lots = size_units / self.lot_units
        return Sizing(True, "ok", frac, risk_amount, size_units, lots)
