# Weatherbot Paper Trading Setup

## Project pause notice

Weatherbot paper trading is paused as of 2026-05-29. Do not start the tmux loop, one-shot runner, watchdog, or Telegram reporting unless Patrick explicitly reopens the project.

The previous instructions below are retained for historical reference only.

This runbook keeps execution in **paper** mode only. It writes simulated decisions and fills to `data/paper_trades.jsonl` so we can test the full risk/strategy/order path and measure performance before any live trading.

## Safety settings

Use `config/default.paper.json` for paper runs:

- `mode`: `paper`
- `execution.enable_live`: `false`
- `execution.dry_run`: `true`
- `trading.max_bet`: `$1.00`
- `trading.min_edge`: `15%`
- `trading.max_spread`: `$0.02`

Do not put private keys, API secrets, or wallet seed material in the paper ledger.

## Run a local demo paper trade

From the repo root:

```bash
python scripts/paper_trade.py --demo --ledger data/paper_trades.jsonl --bankroll 10 --no-telegram
```

Expected output includes:

- `Weatherbot Paper Trading Run`
- `Scanned`
- `Matched`
- `Approved`
- `Filled`
- the path to `data/paper_trades.jsonl`

The demo uses in-memory NYC, Chicago, and Miami weather markets and forecasts, then appends `decision` and `paper_fill` events to the ledger.

## Durable real-data paper runner

The durable runner defaults to `--real-data` and writes to a fresh `data/paper_trades.jsonl` ledger. Start the loop in a persistent `tmux` session and write logs to disk:

```bash
mkdir -p logs
tmux new-session -d -s weatherbot-paper 'cd /home/cptre/weatherbot-prod && WEATHERBOT_LOOP_SECONDS=900 scripts/run_paper.sh >> logs/run_paper.log 2>&1'
```

Inspect it with:

```bash
tmux list-sessions
tail -n 80 logs/run_paper.log
```

Watchdog check:

```bash
scripts/paper_watchdog.sh --ledger data/paper_trades.jsonl --max-age-minutes 60
```

## One-shot scheduled real-data run

For cron/scheduler use, run exactly one cycle:

```bash
scripts/weatherbot_real_paper_once.sh >> logs/run_paper.log 2>&1
```

## Measure paper performance

```bash
python scripts/paper_performance.py --ledger data/paper_trades.jsonl
```

This reports:

- decisions
- approved / rejected counts
- fills and order rejections
- approval rate
- fill rate
- average modeled edge
- total paper stake
- realized PnL, when `daily_pnl` events exist
- open paper positions

## Daily monitoring

The existing daily monitor can also read the same paper ledger:

```bash
python scripts/daily_report.py --ledger data/paper_trades.jsonl --no-telegram
```

For Telegram delivery, configure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`, then run without `--no-telegram` and with `--telegram`.

## Promotion rule

Stay in paper mode until the ledger shows enough sample size to judge:

- stable approval/fill rate
- no unexpected order rejections
- no secret-like fields in ledger output
- acceptable drawdown and realized PnL once markets resolve
- operator kill switch tested

Only after paper results are reviewed should any config move toward live; `execution.enable_live` must remain `false` for all paper testing.
