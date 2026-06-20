# The 2-Step Playbook — How to Pass a FundingPips Evaluation

> A human-tradeable rulebook reverse-engineered from **301,472 real trades** by
> 3,440 leaderboard traders, then validated with an out-of-sample backtest and a
> Monte-Carlo of the actual 2-step rules. The live bot (`run.py` + `engine/`) and
> this playbook obey the **same** risk engine — trade it by hand or automate it,
> the limits are identical.

---

## 0. The one thing that matters

We replayed every one of 3,440 profitable trader-months through the exact 2-step
rules. The finding that drives everything below:

> **People do not fail a 2-step by missing the +8% / +5% target.
> They fail by letting ONE trade or ONE day lose too much and tripping a
> drawdown line.**

- Of profitable traders who *still* failed, the only real busts were on the **5% daily line** (~54% of failures; the rest merely ran out of data before +8% and, with no time limit, would likely have passed). Almost nobody fails by *missing the target.*
- **12.5% of the rank 1–3 P/L monsters would have BUSTED** a 2-step — their huge end-of-month profit came from a reckless path.
- The single feature separating clean passers from path-busters was **the size of their worst trade** (~−2.8% vs ~−5.0%). Win-rate, style, and grid-vs-no-grid did *not* matter.

**Therefore the entire edge of this playbook is risk control, not prediction.**
Trade a modest momentum edge, size tiny, and never give the daily/max line a chance.

---

## 1. The rules you are trading inside (FundingPips 2-Step)

| | Phase 1 | Phase 2 | Funded |
|---|---|---|---|
| Profit target | **+8%** | **+5%** | none |
| Max daily loss | 5% | 5% | 5% |
| Max overall loss | 10% **static** (fixed at 90% of start) | 10% static | 10% static |
| Min trading days | 3 | 3 | — |
| Time limit | none | none | none |
| Profit split | — | — | 80% (→100% on 30-day cycle) |

- **Daily loss** is measured from the *higher of your balance or equity at the start of the day*, and counts **floating** losses — an open position deep in the red can bust you before you close it.
- **Max loss is static** — the 90%-of-initial floor never moves up. Early profit does **not** buy you more room.

---

## 2. Your hard personal limits (well inside the firm's lines)

Set these and never override them. They are the calibrated buffers from the Monte-Carlo:

| Limit | Firm's hard line | **Your line** | Why |
|---|---|---|---|
| Risk per trade (Phase 1) | — | **0.75%** | sweet spot: ~88% sim pass, ~0% daily bust |
| Risk per trade (Phase 2) | — | **0.50%** | you only need +5%; protect the pass |
| Daily loss → STOP for the day | 5% | **3.0%** | a 2% cushion for slippage/gaps |
| Total drawdown → stand down, reset | 10% | **7%** | never trade into the wall |
| Max trades per day | — | **4** | more trades = more bust chances |
| Worst single trade | — | **≤ 1×R ≈ 0.75%** | the #1 buster is an oversized loser |

> At 0.5–0.75% risk, a *full day of four straight losers* costs only ~3% — you hit
> your own daily stop with the firm's line still 1.5–2% away. That gap is the
> whole strategy.

---

## 3. What to trade

**Primary instrument: Gold (XAU/USD), H1 timeframe.**

The data is blunt about this: a momentum edge that survives *both* halves of the
training period and the held-out test exists on **gold only**. The same simple
rules **lose** on FX majors and flip from winner-on-train to loser-on-test on the
indices (US500, DJ30) — classic over-fitting. Gold is also ~60% of all trades in
the dataset and trends/extends cleanly.

- **Trade gold as your core.** Add a second instrument (silver, an index) **only**
  if you have re-run the stability gate and it earns admission on
  *out-of-sample* data — not just because diversification sounds good.
- Avoid trading many correlated instruments at once: in a 2-step, correlated
  positions stack into one big floating loss and trip the daily line together.

---

## 4. The setup (entry)

**Momentum breakout, with the trend:**

- **Long:** price is making/retesting its **20-bar high** (within ~0.05×ATR of it)
  **and** the H1 trend is up (EMA20 > EMA50).
- **Short:** price is making/retesting its **20-bar low** and the trend is down
  (EMA20 < EMA50).
- Enter on the **next bar's open** after the signal bar closes. Never anticipate.

You will be **wrong ~62% of the time** — that is fine and expected. The winners run
~2R while the losers are cut at ~1R, so the math works *only if you never let a
single loser exceed 1R.*

---

## 5. The trade management (exit — this is where the edge actually lives)

The reverse-engineering of the original winners showed their edge was in **exits,
not entries**: cut losers fast, let winners run. Mechanically:

1. **Initial stop:** 2×ATR from entry. Size the position so this stop = your risk %
   (Section 2). This is non-negotiable — the stop defines the size, not vice-versa.
2. **Break-even:** once price is +1R in your favour, move the stop to entry. Now the
   trade cannot lose.
3. **Trail:** trail the stop at 3×ATR behind price. Let it run; do **not** set a tight
   fixed take-profit (the winners used fixed TPs *less* than the field).
4. **Time stop:** if the trade hasn't worked in ~2 trading days (48 H1 bars), close it.
   Dead trades tie up risk budget.

---

## 6. Position sizing — do the arithmetic every time

```
risk_$         = account_balance × risk_%            (0.75% P1, 0.50% P2)
stop_distance  = 2 × ATR(H1)                          (in price units)
size (lots)    = risk_$ / (stop_distance × $_per_point_per_lot)
```

Gold: 1 standard lot = 100 oz, so $1 move = $100/lot.

**Per-trade risk by account size:**

| Account | 0.50% (P2) | 0.75% (P1) |
|---|---|---|
| $5,000 | $25 | $37.50 |
| $10,000 | $50 | $75 |
| $25,000 | $125 | $187.50 |
| $50,000 | $250 | $375 |
| $100,000 | $500 | $750 |

*Worked example ($100k, Phase 1, gold ATR = $20):* stop = 2×$20 = $40 → risk/lot =
$40 × 100 = $4,000 → size = $750 / $4,000 = **0.19 lots**. If ATR doubles, your size
**halves** automatically — that is how you keep risk constant across regimes.

---

## 7. Phase-by-phase tactics

**Phase 1 (need +8%):**
- Risk 0.75%/trade. At ~0.26R expectancy and a few trades a day, +8% typically
  arrives in a few weeks — there is **no time limit, so never rush**.
- Hit your 3% daily stop? Close the platform. Tomorrow is a fresh daily anchor.
- Within ~1.5% of +8%? **Halve your size.** Do not let a final loser undo a pass.

**Phase 2 (need +5%):**
- Drop to 0.50%/trade. The target is smaller and the *only* job is to not bust.
- Same setup, same stops, just smaller. Patience beats aggression here every time.

**Funded:**
- Keep Phase-2 sizing (0.50%). Drawdown rules are identical and now it is **real
  money** with an 80% split. Consistency of withdrawals > heroics.

---

## 8. Daily routine / checklist

1. **Before the session:** note start-of-day balance/equity → that is today's daily
   anchor. Your daily stop = anchor − 3% of *initial* balance.
2. **On each signal:** confirm trend filter → compute stop (2×ATR) → compute size
   from risk % → place entry + stop together. No stop, no trade.
3. **Manage:** move to break-even at +1R; trail at 3×ATR; honour the time stop.
4. **Circuit breakers:** down 3% today → **done for the day.** Down 7% total →
   **stand down, review, don't trade.**
5. **Near target:** within 1.5% → half size; at target with ≥3 trading days → **stop
   and bank the phase.**

---

## 9. The "never" list (every one of these is a documented buster)

- ❌ Never move or widen a stop away from price.
- ❌ Never add to a loser / martingale / grid into drawdown (one bad sequence = bust).
- ❌ Never risk more than 1% on a single trade, ever — the worst-trade size *is* the failure mode.
- ❌ Never trade after hitting your 3% daily stop "to make it back."
- ❌ Never hold a pile of correlated positions into a news spike.
- ❌ Never trade to a deadline — there is no time limit; variance is the only enemy.

---

_This playbook is a research deliverable, not financial advice. Backtests and
simulations describe the past and a favourable gold regime; the future may differ.
Demo it first._
