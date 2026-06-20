# Joint Two-Step Risk Calibration

The FundingPips challenge requires passing **both** phases — Phase 1 (+8%) **and**
Phase 2 (+5%). The objective is therefore the **joint** pass probability
`P(pass P1) × P(pass P2)`, not either phase alone. Per-trade R-multiples are
risk-invariant (`R = pnl / risk`), so one out-of-sample backtest's trade-day
distribution is replayed at every `(P1 risk, P2 risk)` pair through the exact
rule-set (day-block bootstrap, 4,000 paths each).

## Per-phase pass / bust vs risk

| risk | Phase 1 (+8%) pass | P1 bust | Phase 2 (+5%) pass | P2 bust |
|---|---|---|---|---|
| 0.40% | 85.1% | 0.5% | — | — |
| 0.50% | 89.3% | 1.2% | 95.0% | 1.6% |
| 0.60% | 90.5% | 3.0% | 95.3% | 2.6% |
| **0.75%** | **91.7%** | 6.2% | 93.8% | 5.7% |
| 0.90% | 90.5% | 8.7% | — | — |
| 1.00% | 87.6% | 11.9% | 89.9% | 10.0% |

## Joint objective — top combinations

| P1 risk | P2 risk | P1 pass | P2 pass | **full-pass (both)** | any-bust |
|---|---|---|---|---|---|
| 0.75% | 0.60% | 91.7% | 95.4% | **87.4%** | 8.7% |
| **0.75%** | **0.50%** | **91.7%** | **95.0%** | **87.1%** | **7.7%** |
| 0.60% | 0.50% | 90.4% | 95.0% | 85.9% | 4.5% |

## Decision

**P1 0.75% / P2 0.50%** — full-pass ~87% (the top combinations are all within
Monte-Carlo noise of each other). Phase-1 risk is kept modest and Phase-2 lower
still, because **bust risk compounds across two phases**: a Phase-1 bust ends the
attempt before Phase 2 is even reached, so minimising the Phase-1 bust rate
protects the joint pass more than squeezing the last point of single-phase pass
rate. A more conservative operator can drop to **0.60% / 0.50%** (≈86% full-pass,
but any-bust nearly halved to 4.5%).

> Caveat: these reflect a favourable gold-trend out-of-sample regime and are
> *if-the-edge-persists* figures, not guarantees.
