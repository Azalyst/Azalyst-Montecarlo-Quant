# Azalyst Montecarlo — Gold 2-Step Engine

A single, **Monte-Carlo-validated** momentum strategy paper-trading **one $100,000
FundingPips 2-step challenge** (Phase 1 **+8%** → Phase 2 **+5%**) live on GitHub
Actions, against the exact FundingPips drawdown rules.

Unlike a basket of hand-tuned setups, this is **one strategy the data actually
earned**: it was reverse-engineered from **301,472 real prop-firm trades**, kept
only where its edge survived both halves of a training window *and* a held-out
out-of-sample test, and sized by a 2-step Monte-Carlo.

📊 **Dashboard:** [azalyst.github.io/Azalyst-FundingPips-Signals](https://azalyst.github.io/Azalyst-FundingPips-Signals/)
&nbsp;·&nbsp; 📑 **Method:** [research/MASTER_REPORT.md](research/MASTER_REPORT.md)
&nbsp;·&nbsp; 📘 **Playbook:** [research/PLAYBOOK.md](research/PLAYBOOK.md)

> Repo named `Azalyst-FundingPips-Signals` for now — the system itself is
> **Azalyst Montecarlo**. Rename the repo freely; the code only references the
> system name (in `config.yaml`).

## How it works

| Layer | What |
|---|---|
| **Instrument** | Gold (XAU/USD H1) via yfinance `GC=F` — the *only* instrument whose edge survived out-of-sample. A single naive rule across 9 instruments loses money; FX & indices over-fit. |
| **Entry** | Momentum breakout — buy within 0.05·ATR of the prior 20-bar high in an uptrend (symmetric short). |
| **Exit** | 2·ATR initial stop → break-even at +1R → 3·ATR trailing stop → 48-bar time stop. (The winners' edge was in *exits*, not entries.) |
| **Sizing** | Phase-aware: **0.75%** risk/trade in Phase 1, **0.50%** in Phase 2. Calibrated by the Monte-Carlo: 0.5–0.75% ⇒ ~88% simulated full-pass, ~0% daily-bust. |
| **Risk engine** | Daily soft-stop at −3%, total stand-down at −7%, max 4 trades/day, half-size near the target — all well inside the firm's 5%/10% lines. |
| **Challenge** | Tracks one $100k account: realized balance vs target, floating equity vs the daily/static drawdown floors, ≥3 trading days, P1→P2→Funded transitions. |

## Why one strategy, not seven

The reverse-engineering finding (see `research/`): traders fail a 2-step on the
**5% daily line**, not the target — and **12.5% of the biggest winners would have
busted**. The separator between passers and busters is **worst-trade size**, not
style. So the whole edge is *risk control on one instrument with a real, OOS-proven
signal* — adding more strategies adds correlated bust risk, not return.

## Running

```bash
pip install -r requirements.txt

python run.py                 # one tick: fetch gold -> advance challenge -> dashboard -> alerts
python run.py --test-discord  # webhook connectivity test
python run.py --reset         # reset to a fresh Phase 1 account
```

Automated by `.github/workflows/signals.yml` (twice an hour; idempotent — only
newly-closed bars are processed). State persists in `state/challenge.json`; the
dashboard feed is `docs/status.json` (served by GitHub Pages from `/docs`).

**Discord alerts** (optional): set a repo secret `DISCORD_WEBHOOK_URL`. Without
it the engine runs fine and just logs.

## Layout

```
config.yaml                 instrument, rules, risk — all the knobs (verified, not guessed)
run.py                      the Action entry point (one tick)
engine/
  data.py                   live gold H1 via yfinance (closed bars only, UTC)
  indicators.py             causal market state + the momentum-breakout rule
  risk.py                   phase-aware sizing + daily/total governors
  challenge.py              the live 2-step paper-trade tracker (the heart)
  notify.py                 optional Discord alerts
  dashboard.py              writes docs/status.json
docs/index.html             the GitHub-Pages dashboard (reads status.json)
research/                   provenance: the deep analysis that produced this strategy
.github/workflows/          the cron
```

## Disclaimer

Educational paper-trading record built from a research project. Backtests and
Monte-Carlo describe the past (and a favourable gold regime); the future may
differ. **Not financial advice.**
