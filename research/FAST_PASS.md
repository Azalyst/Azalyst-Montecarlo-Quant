# Fast-Pass (Aggressive) Mode — Trading Like the Monster Traders

The leaderboard's >100%/month "monster" traders reached the +8% Phase-1 target in a
**median of 2 days / 5 trades** — not by grinding, but by risking ~4× more per
trade and letting one position run to +44%. Crucially, they **never breached the
10% max-drawdown** (it's measured from *initial* balance, so a banked cushion sits
miles above the floor); the only rule that constrains the style is the **5% daily
loss ($5k of initial, fixed)**, which caps a single day's *loss* but never the
*gain*. That asymmetry is the whole edge.

Aggressive mode is the rule-correct version of that style.

## The configuration

| | Safe | **Aggressive (live)** |
|---|---|---|
| Per-trade risk | 0.75% / 0.50% | **1.25% / 0.85%** |
| Scale-in | no | **yes — add a tranche at +1R, combined stop → base entry** |
| Lock-in near target | half size | **none — let it run to target** |
| Time stop | 48 bars | **96 bars (let runners breathe)** |
| On bust | terminal | **auto-reset, log the attempt, keep trying** |
| Goal | high pass-rate | **pass FAST (1–2 weeks)** |

**Scale-in** is the monster mechanic: once a position is +1R in profit, add a
second tranche the same size and move the *combined* stop to the original entry —
the base tranche's profit funds the add, so the add rides on house money. One
runner can then carry the whole +8% in a single move.

## The frontier (out-of-sample, 4,000-path bootstrap)

| config | full-pass | bust | pass ≤2 wk | median trading-days |
|---|---|---|---|---|
| flat 0.75% (safe) | 88% | 6% | 13% | 26 |
| flat 1.75% | 55% | 36% | 71% | 7 |
| **scale-in 1.25%** | **66%** | **23%** | **67%** | **7** |

Scale-in at 1.25% **dominates** flat 1.75%: same ~7-trading-day speed, but higher
pass and lower bust — the house-money add concentrates the win without adding
downside. Silver was tested and **rejected** (its edge failed out-of-sample;
adding it collapses the pass rate — the monsters' silver use was survivorship).

## The honest numbers (read this)

The 66% modeled full-pass comes from a single out-of-sample window that was a
**strong gold up-trend** (+33%), bootstrapped — it cannot sample a choppy/ranging
gold market. After an adversarial regime haircut (≈0.6–0.7×):

- **Realistic per-attempt pass ≈ 40% in a normal trending year, ≤30% if gold is ranging.**
- The edge is concentrated in a few big trades (expectancy minus the top-5 trades
  ≈ 0.05R; one recent quarter was negative). It is a **trend-rider** — only deploy
  when gold is actually trending.
- **Budget 2–3 attempts.** Fee ≈ $529 for a $100k 2-step, refunded on the first
  payout; expected net cost to funded ≈ $700 over ~2.4 attempts, ~14 calendar days.

## When to use which

- **Aggressive** when the objective is to get funded *fast* and you accept buying
  a few attempts (and gold is trending).
- **Safe** the moment the objective flips to *keeping* the funded account — flip to
  0.75% and grind. Never exceed 2.0% risk; the 2.5% level is a cliff (83% bust).

_Backtests and Monte-Carlo describe the past; the future may differ. Not financial advice._
