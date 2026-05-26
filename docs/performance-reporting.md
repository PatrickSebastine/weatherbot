# Weatherbot Performance Reporting

Weatherbot uses standard Markdown reports for **Daily**, **Weekly**, and **Monthly** paper-trading reviews. The reports are generated from the append-only paper ledger and committed to GitHub for easy review over time.

## Schedule and UTC policy

- Daily report schedule: **00:05 UTC** every day.
- Daily report window: previous day from **00:00 UTC to 23:59 UTC**.
- Example: the 25 May 2026 daily report covers 00:00 UTC to 23:59 UTC on 25 May 2026 and is generated/pushed at 00:05 UTC on 26 May 2026.
- Cron expression: `5 0 * * * /home/cptre/weatherbot-prod/scripts/daily_report_push.sh`.

The push target is Patrick's standalone GitHub repo:

```bash
git push origin HEAD:prod-safety-refactor
```

If the scheduler uses local SAST time instead of UTC, schedule `5 2 * * *` so the job runs at **00:05 UTC**.

## Low resource execution

The scheduled push script runs with a low resource profile:

- serial execution; no parallel test or report work
- `flock` prevents overlapping report jobs
- `nice -n 10` lowers CPU priority
- `ionice -c2 -n7` lowers disk I/O priority
- BLAS/threading environment variables are pinned to `1`

## Commands

Generate the previous daily report manually:

```bash
python scripts/performance_report.py --period daily --ledger data/paper_trades.jsonl --log logs/run_paper.log --output-dir reports/performance
```

Generate weekly and monthly reports manually:

```bash
python scripts/performance_report.py --period weekly --ledger data/paper_trades.jsonl --output-dir reports/performance
python scripts/performance_report.py --period monthly --ledger data/paper_trades.jsonl --output-dir reports/performance
```

Run the low-resource daily generation + GitHub push script:

```bash
scripts/daily_report_push.sh
```

## Standard report template

Each Daily, Weekly, and Monthly report uses the same sections so performance is easy to compare:

1. Title and UTC period window
2. Mode and resource profile
3. Executive Summary
   - decisions
   - approved
   - rejected
   - fills
   - order rejections
   - ledger errors
   - runtime/log errors
4. Performance Metrics
   - approval rate
   - fill rate
   - average edge
   - total staked
   - realized PnL
   - open positions
5. Exposure by City
6. Runtime Error Summary, when runner tracebacks occurred in the UTC window
7. Review Notes

## Review cadence

- **Daily**: check bot health, fills, rejections, and errors.
- **Weekly**: compare approval/fill rates and exposure concentration.
- **Monthly**: decide whether to keep paper sizing, tighten rules, or prepare for the next graduation gate.
