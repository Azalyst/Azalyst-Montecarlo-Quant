# Azalyst-Montecarlo-Quant

Azalyst Montecarlo Quant is a systematic prop-firm trading engine that converts the
behaviour of thousands of real funded traders into a single, statistically
validated strategy. Rather than stacking discretionary setups, it reverse-engineers
**what actually passes a two-step evaluation** from a corpus of **301,472 real
prop-firm trades**, isolates the one edge that survives out-of-sample, and sizes it
with a Monte-Carlo of the exact challenge rules.

The platform runs a fully autonomous, serverless pipeline — live market data →
causal signal → phase-aware risk → paper-traded challenge → institutional
dashboard — entirely on GitHub Actions, with no broker dependency and no
manual intervention.

**Live Dashboard:** [azalyst.github.io/Azalyst-Montecarlo-Quant](https://azalyst.github.io/Azalyst-Montecarlo-Quant/)
&nbsp;·&nbsp; **Method:** [research/MASTER_REPORT.md](research/MASTER_REPORT.md)
&nbsp;·&nbsp; **Playbook:** [research/PLAYBOOK.md](research/PLAYBOOK.md)

## The Azalyst Montecarlo Edge

- **Evidence-Derived Strategy**: Every one of 301,472 leaderboard trades is replayed
  through the exact FundingPips two-step rule-set. The finding is decisive — traders
  fail on the **5% daily-loss line, not the profit target**, and the discriminator
  between passers and busters is single-trade loss size, not hit-rate or style. The
  entire engine is built around that result.
- **Out-of-Sample Instrument Gating**: A single rule across nine instruments loses;
  the edge is gold-specific. A stability gate admits an instrument only if its
  expectancy is positive across **both halves of the training window** — which is
  why over-fit indices (US500, DJ30) are rejected *before* the held-out test, where
  they later collapse. Currently only **gold (XAU/USD H1)** clears the bar.
- **Monte-Carlo-Calibrated Sizing**: Per-trade risk is not guessed. A two-step
  pass-rate Monte-Carlo locates the sizing frontier: **0.50–0.75% risk per trade →
  ~88% simulated full-pass with ~0% daily-bust**, collapsing above ~1.5%.
- **Phase-Aware Risk Governance**: Sizing tightens by phase (0.75% Phase 1 / 0.50%
  Phase 2), with a daily soft-stop at −3%, a total stand-down at −7%, a four-trade
  daily cap, and automatic half-sizing into the target — every limit a deliberate
  buffer inside the firm's 5%/10% lines.
- **Execution Realism**: Next-bar entry on closed bars only, ATR-based stops with a
  break-even lock and trailing exit, realistic round-trip costs, and one position at
  a time. Backtest behaviour and live behaviour are bar-for-bar identical.

## The Strategy

| Layer | Specification |
|---|---|
| **Instrument** | Gold (XAU/USD H1) via yfinance `GC=F` — the only instrument with a train-and-test-consistent edge. |
| **Entry** | Momentum breakout: long within 0.05·ATR of the prior 20-bar high in an uptrend (symmetric short). Next-bar open. |
| **Exit** | 2·ATR initial stop → break-even at +1R → 3·ATR trailing stop → 48-bar time stop. The winners' edge was in exits, not entries. |
| **Sizing** | 0.75% (Phase 1) / 0.50% (Phase 2) of balance per trade, stop-distance-derived. |
| **Challenge** | One $100k account: realized balance vs target, floating equity vs the 5% daily / 10% static floors, ≥3 trading days, P1 (+8%) → P2 (+5%) → Funded. |

## Architecture

```
 ╔══════════════════════════════════════════════════════════════════╗
 ║                  AZALYST MONTECARLO QUANT                         ║
 ║          gold 2-step · free data · paper-traded · autonomous     ║
 ╚══════════════════════════════════════════════════════════════════╝

         ┌── CRON ──┐
         │ 2×/hour  │  GitHub Actions (idempotent: only new closed bars)
         └────┬─────┘
              ▼
 ┌────────────────────────┐
 │ DATA   engine/data.py  │  yfinance GC=F · H1 · closed bars only · UTC
 └───────────┬────────────┘
             ▼
 ┌────────────────────────┐
 │ SIGNAL engine/         │  causal EMA/RSI/ATR · 20-bar breakout
 │        indicators.py   │  entry = signal[t-1] → open[t]   (no look-ahead)
 └───────────┬────────────┘
             ▼
 ┌──────────────────────────────────────────┐
 │ RISK   engine/risk.py                    │
 │  phase risk 0.75 / 0.50 %                 │
 │  daily soft-stop −3% · DD brake −7%       │
 │  lock-in near target · 4 trades/day cap   │
 └───────────────────┬──────────────────────┘
                     ▼
 ┌──────────────────────────────────────────┐
 │ CHALLENGE engine/challenge.py            │
 │  target on realized balance (+ ≥3 days)   │
 │  bust on floating equity (5% / 10% static)│
 │  P1 (+8%) → P2 (+5%) → FUNDED transitions │
 └───────────────────┬──────────────────────┘
                     ▼
        ┌────────────┴────────────┐
        ▼                         ▼
 ┌──────────────┐         ┌────────────────────┐
 │ DISCORD      │         │ DASHBOARD          │
 │ (optional)   │         │ docs/ · GitHub Pages│
 └──────────────┘         └────────────────────┘
```

## Method & Validation

- **Reverse-engineering** (`research/`): 3,440 trader-months replayed through the
  two-step rules; the survivorship-robust signal is the passer-vs-buster contrast.
- **Train/test discipline**: rules and every parameter chosen on TRAIN
  (≤ 2025-06-30); the held-out TEST window is touched once. Out-of-sample result on
  gold: **profit factor 1.46, +27.5% return, 7.5% maximum drawdown** — under the
  10% static limit, the necessary condition for a two-step.
- **Monte-Carlo**: day-block bootstrap of the out-of-sample trade distribution
  through the exact rule-set, plus a per-trade-risk sweep, yields the ~88%
  full-pass figure at 0.5–0.75% risk.

## System Scope and Limitations

- Designed as a quantitative research simulation (paper trading), not a live broker
  integration. Orders are fully specified but not routed.
- Gold-only by design: the data does not support a stable mechanical edge on FX or
  indices for these rules. The engine is multi-instrument; the stability gate is
  re-run as instruments earn admission.
- The ~88% pass-rate reflects a strong gold-trend regime in the out-of-sample
  window and is an *if-the-edge-persists* figure, not a guarantee.
- Free-data only (yfinance). A sustained data outage skips the tick cleanly and the
  next cron recovers — state is never corrupted.

## Running

```bash
pip install -r requirements.txt

python run.py                 # one tick: fetch gold → advance challenge → dashboard → alerts
python run.py --test-discord  # webhook connectivity test
python run.py --reset         # reset to a fresh Phase 1 account
```

Automated by `.github/workflows/signals.yml` (twice hourly). State persists in
`state/challenge.json`; the dashboard feed is `docs/status.json` (GitHub Pages from
`/docs`). Discord alerts are optional via a repo secret `DISCORD_WEBHOOK_URL`.

## License

MIT

> Educational paper-trading record derived from a research project. Backtests and
> Monte-Carlo describe the past; the future may differ. Not financial advice.
