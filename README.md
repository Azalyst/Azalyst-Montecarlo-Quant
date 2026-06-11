# Azalyst OB Challenge — FundingPips Signal Engine

**Order Block (OB) strategy** running a live simulated $100,000 FundingPips prop-firm
challenge. ICT/SMC order block detection on the 4H timeframe, entries on the 15M
retrace into the OB zone.

📊 **Dashboard:** [azalyst.github.io/Azalyst-FundingPips-Signals](https://azalyst.github.io/Azalyst-FundingPips-Signals/)

## Challenge Structure

| Phase | Target | Loss Limits |
|---|---|---|
| Phase 1 | +8% ($108,000) | $5,000 daily / $10,000 max |
| Phase 2 | +5% ($105,000) | $5,000 daily / $10,000 max |

The dashboard tracks **days to pass** each phase in real time.

## Strategy — Order Block (OB)

- **HTF (4H):** Detects order blocks — the last candle before a strong momentum breakout
- **Entry (15M):** Price retraces into the OB zone with confirmation
- **Stop:** Beyond the OB boundary + ATR buffer
- **Target:** 1:2 risk-reward
- **Risk:** 1% per trade

### Instruments

EURUSD, GBPUSD, XAUUSD, NAS100, SP500, BTCUSD, ETHUSD

Data sources: yfinance (FX/metals/indices) + Bybit (crypto).

## Running

```bash
# Install
pip install -r requirements.txt

# Single tick (cron/manual)
python run.py

# Dry run (no Discord alerts)
python run.py --dry-run

# Test Discord connectivity
python run.py --test-discord

# Reset to fresh challenge
python reset.py
```

Automated via GitHub Actions every 15 minutes (`.github/workflows/signals.yml`).

## Dashboard

The dashboard auto-refreshes from `docs/status.json` every 60s. Open
`docs/index.html` locally or visit the GitHub Pages URL above.

## Disclaimer

Educational paper-trading record. Signals are mechanical interpretations and are
not financial advice. Past and simulated performance does not guarantee future results.
