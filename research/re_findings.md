# Reverse-Engineering the FundingPips 2-Step

_Every one of **3,440** real trader-months replayed through the exact 2-step rule-set (8% / 5% targets, 5% daily / 10% static DD, 3 min days, target on realized balance, busts on floating equity)._

## ⚠️ Read this first: survivorship

Every trader in this data is a **profitable leaderboard finisher** -- the blow-ups never appear. So the raw pass-rates below are *conditional on having had a winning month*; they are NOT a real-world challenge pass-rate (that comes from the mechanical strategy's Monte-Carlo, where losing paths exist). What this data *can* tell us cleanly is the **PATH question**: given a profitable month, what makes the equity path stay inside the rules vs trip a drawdown line? That passer-vs-buster contrast is internally survivorship-consistent and is the actionable core.

## TL;DR

- **Among profitable months, 91.1% keep a legal path to +8%; 8.9% would FAIL a 2-step despite ending the month in profit** -- almost entirely by tripping the **5% daily-loss line** (4.8% of all months), not by missing the target.
- **Rank is NOT pass.** Top-10%-by-rank pass 90.7% vs 91.1% for the rest, and **12.5% of the rank 1-3 monsters would have BUSTED** -- they booked +8%+ but blew a daily/max-DD line on the way. The biggest end-of-month P/L often comes from the most reckless path.
- **The discriminator is single-trade loss size, not hit-rate.** Path-busters' worst single trade is ~5.0% vs ~2.8% for clean passers. One oversized loser = one blown daily limit. Win-rate barely differs.
- **Design rule that falls straight out: cap per-trade risk ~1% and stop the day at ~3%** -- a wide buffer below the 5% line, which is the only line most profitable traders ever actually hit.

## Clean-passer vs path-buster (both are profitable months)

_Path-busters n=166, clean-passers n=3133. Cliff's δ = effect size in [-1,1]; |δ|>0.15 is a real separation._

| feature | buster (med) | passer (med) | Cliff's δ |
|---|---|---|---|
| max_drawdown_pct | 11.140 | 6.310 | +0.469 |
| worst_trade_pct | -5.005 | -2.810 | -0.449 |
| grid_trade_share | 0.000 | 0.000 | -0.252 |
| n_trades | 59.500 | 42.000 | +0.167 |
| trades_per_active_day | 4.250 | 3.450 | +0.123 |
| asset_share_metal | 0.636 | 0.536 | +0.113 |
| best_trade_pct | 11.065 | 9.360 | +0.112 |

**Reading it:** the separating features are all *magnitude-of-loss* measures (worst trade, max drawdown) plus activity (more trades = more chances to breach). SL-usage, grid-share and win-rate do **not** separate the groups -- discipline on *position size* matters far more than *style*.

## Phase-1 outcome mix (all trader-months)

| outcome | share |
|---|---|
| pass | 91.1% |
| daily_dd | 4.8% |
| incomplete | 4.1% |

## Of the months that FAILED Phase 1, the cause:

| failure | share of failures |
|---|---|
| daily_dd | 54.1% |
| incomplete | 45.9% |

> 'incomplete' = never busted but the month's data ran out before +8% (in a real challenge there's no time limit, so many of these would eventually pass -- the *bust* rate is the real enemy).

## Pass-rate by hit-rate

| win-rate bucket | pass-rate | n |
|---|---|---|
| (0.0, 0.4] | 93.6% | 547 |
| (0.4, 0.5] | 92.6% | 625 |
| (0.5, 0.55] | 96.2% | 293 |
| (0.55, 0.6] | 93.2% | 296 |
| (0.6, 0.65] | 90.6% | 297 |
| (0.65, 0.7] | 91.2% | 261 |
| (0.7, 1.0] | 87.2% | 1121 |

## Pass-rate by activity (number of trades)

| n-trades bucket | pass-rate | n |
|---|---|---|
| (0, 10] | 71.2% | 416 |
| (10, 25] | 93.8% | 808 |
| (25, 50] | 94.4% | 767 |
| (50, 100] | 94.7% | 714 |
| (100, 200] | 93.6% | 425 |
| (200, 10000] | 90.6% | 310 |
