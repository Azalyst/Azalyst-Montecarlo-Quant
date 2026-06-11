"""Strategy registry.

Each strategy module exposes:
    NAME: str
    generate(scfg, instruments, fetch, now) -> list[Signal]
where `fetch(inst_cfg, interval, bars) -> DataFrame` and `now` is tz-aware UTC.
"""
from . import ob

REGISTRY = {
    ob.NAME: ob,
}

# strategies whose open positions are managed with a break-even move at 1R
BREAKEVEN_STRATEGIES: set = set()
