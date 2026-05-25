# Weatherbot

Weatherbot is a safety-first Polymarket weather-market research bot.

Current honest status: Demo runner uptime and ledger smoke test.

That means the default durable runner is useful for checking process uptime, ledger writes, reporting, watchdogs, and safety gates. It is not proof of profitable weather trading.

## Current operating modes

### Demo paper smoke test

The existing low-resource loop uses:

```bash
scripts/run_paper.sh
```

That wrapper currently calls `scripts/paper_trade.py --demo`. Demo mode uses deterministic synthetic markets and forecasts. Treat its reports as uptime/ledger smoke-test evidence only.

### Real-data dry-run paper scanner

A read-only real-data scanner is now available:

```bash
python scripts/paper_trade.py --real-data --config config/default.paper.json --ledger data/paper_trades.jsonl --bankroll 10 --no-telegram
```

It fetches real external inputs but still does dry-run paper trading only:

- Polymarket Gamma weather event fetcher
- Polymarket CLOB order book fetcher
- Open-Meteo forecast fetcher
- Market-to-station matching
- Stale/missing forecast filtering by city and event date
- Ledger output for decisions, fills, portfolio snapshots, and PnL events when resolutions are supplied by helper functions

Live mode is not wired. Do not treat this repo as live-trading ready.

## What must be proven before live trading

Do not consider live capital until real-data paper mode has at least:

- 100+ real paper decisions
- Real market prices
- Real weather forecasts
- Resolved outcomes
- Actual win rate
- Actual realized PnL
- Max drawdown
- Average edge versus actual outcome
- No duplicate overexposure
- Watchdog and reporting stability

## Repository layout

- `weatherbot/config.py` - config loading and safety validation
- `weatherbot/data/live.py` - read-only Gamma, CLOB, and Open-Meteo fetchers
- `weatherbot/data/polymarket.py` - Gamma/CLOB payload parsing
- `weatherbot/data/weather.py` - Open-Meteo normalization and forecast snapshots
- `weatherbot/scan.py` - market-to-forecast matching and paper scan orchestration
- `weatherbot/engine.py` - paper decision, EV, sizing, risk, and fill logging
- `weatherbot/portfolio.py` - rebuilds cash, positions, exposure, duplicate exposure, and PnL from the ledger
- `weatherbot/ledger.py` - append-only secret-safe JSONL ledger
- `scripts/paper_trade.py` - demo or real-data dry-run entrypoint
- `scripts/run_paper.sh` - current durable low-resource demo runner
- `scripts/paper_performance.py` - ledger summary
- `scripts/performance_report.py` - daily/weekly/monthly reports

## Legacy files

These files are retained for reference only and should not be treated as the current production path:

- `bot_v1.py` - legacy base bot
- `bot_v2.py` - legacy fuller bot prototype
- `config.json` - legacy config shape, not the current validated paper config

The current validated config is:

```bash
config/default.paper.json
```

## Installation

```bash
git clone https://github.com/PatrickSebastine/weatherbot
cd weatherbot
python3 -m pip install -r requirements.txt
```

On minimal Ubuntu/WSL systems without pip, install pytest from apt for local tests:

```bash
sudo apt-get install -y python3-pytest
```

## Tests

```bash
pytest -q
```

## Safety policy

- Paper mode only by default
- `execution.enable_live=false` required for paper runner
- CLOB helpers are read-only unless an external live client is deliberately injected elsewhere
- Ledger rejects secret-like payload fields
- Reports are only as truthful as the event source: demo data is smoke-test data, real-data paper mode is required for strategy assessment

## Disclaimer

This is not financial advice. Prediction markets carry real risk. Current repo status is pre-live research infrastructure, not a proven profitable trading system.
