# Azalyst FundingPips Signal Engine

Runs six trading strategies on a 15-minute cron, posts BUY/SELL signals to Discord
(pinging your user id), and **paper-trades every signal** under live FundingPips
rules so you have an exact, rule-safe trade to mirror and a running PnL record.

Account modelled: **$100,000**, max daily loss **$5,000**, max overall loss
**$10,000** (floor $90,000), challenge window **2026-06-01 → 2026-06-30**.
Risk per trade: **1%** ($1,000). All values configurable in `config.yaml`.

## Strategies

| Module | Source doc | Instruments | TF | Logic |
|---|---|---|---|---|
| `rsi` | RSI Strategy | EURUSD, GBPUSD, XAUUSD, NAS100, SP500, BTC, ETH | 1d | Classic 14/70-30 cross + 5×ATR stop; Filtered 200MA+5MA+RSI2<20 |
| `ema5` | 5 EMA Game Changer | EURUSD, GBPUSD, XAUUSD, NAS100 | 5m sell / 15m buy | Alert candle not touching 5 EMA → break → 1:3, 3-SL/day cap |
| `eth_blueprint` | Ethereum Blueprint | ETHUSD | 15m (4H bias) | Asia-session BOS in HTF-bias direction, SL@HL/LH, 1:2, break-even @1R |
| `smt_divergence` | SMT Divergence | BTC/ETH pair | 5m | Trade the asset that fails the correlated high/low, 1:2 |
| `jadecap` | JadeCap Liquidity | EURUSD, GBPUSD, NAS100, SP500 | 15m | NY-killzone sweep of session level + FVG/MSS confirm |
| `quantx` | QUANT-X | BTCUSD | 15m | 7-indicator / 4-agent consensus (≥3 agree), 1:2 |

### Faithful adaptations (noted, not hidden)
- **QUANT-X** describes an LLM (Mistral/Ollama) multi-agent system on a 4-second loop.
  A cron runner can't host the LLM, so the four agents are reproduced as deterministic
  rules over the same 7 indicators. Consensus gate (≥3 agree, Risk not HIGH) is kept.
- **RSI Filtered** uses a dynamic "close above 5MA" exit in the doc. Here it gets a
  structural stop (recent swing low) and a 1:2 target so risk is bounded for paper.
- **15m cron vs 5m setups**: each tick evaluates the latest *closed* bars. Fast
  intrabar 5m triggers between ticks can be missed — the tradeoff you chose for cost.
- Session gates honour the docs: Ethereum = first 3h of Asia (00:00–03:00 UTC);
  JadeCap = NY killzone 09:30–11:30 America/New_York (DST-aware).

## Risk engine
Position size = `risk_usd / stop_distance` so a stop-out loses exactly 1%. A trade is
**blocked** unless `realized_loss_today + worst-case open risk + this trade's risk`
stays inside the daily budget, and equity minus that worst case stays above the
$90k floor — so the FundingPips rules cannot break even if every open stop is hit.

## Data
- FX / metals / index futures → yfinance.
- Crypto → Bybit public REST (reliable on GitHub runners; Binance is geo-blocked
  there), with a yfinance fallback.
Only USD-PnL instruments are traded, so position sizing is exact.

## Setup
1. **Secret:** repo → Settings → Secrets and variables → Actions → new secret
   `DISCORD_WEBHOOK_URL` = your webhook URL. (Never commit it.)
2. The workflow runs every 15 min and commits `state/` + `reports/` back to the repo.
3. Manual run / test: Actions tab → *FundingPips Signals* → *Run workflow*
   (tick "test_discord" for a connectivity ping).

## Local use
```bash
pip install -r requirements.txt
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python run.py --dry-run      # evaluate + paper-trade, print instead of posting
python run.py --test-discord # send one test message
python run.py                # live tick
```
State lives in `state/` (account, positions, dedupe). PnL report in `reports/`.

## Disclaimer
Educational paper-trading tool. Signals are mechanical interpretations of the source
playbooks and are not financial advice. Past/backtested performance does not
guarantee future results.
