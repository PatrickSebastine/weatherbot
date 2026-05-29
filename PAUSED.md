# Weatherbot Project Pause Notice

Status: PAUSED / DISABLED
Date: 2026-05-29
Owner: Patrick / Lynx AI
Workspace: `/home/cptre/weatherbot-prod`

## Decision

Weatherbot is paused and disabled.

Reason: the project is currently not producing enough reliable value to justify more troubleshooting, credit usage, or token spend. The practical decision is to stop all scheduled execution and preserve the repo as a frozen research artifact.

## What is stopped

The following Hermes cron jobs were paused on 2026-05-29:

| Job ID | Name | Script | Previous schedule |
|---|---|---|---|
| `3865d426994a` | Weatherbot daily performance report push | `weatherbot_daily_report_push.sh` | `5 2 * * *` |
| `488c8bc3e2b0` | Weatherbot paper runner watchdog | `paper_watchdog.sh` | `20,50 * * * *` |
| `3a83120331d8` | Weatherbot real-data paper runner | `weatherbot_real_paper_once.sh` | `15,45 * * * *` |

No Weatherbot tmux sessions or active OS processes were found during the pause check.

## Operational rule

Do not restart Weatherbot, its scheduled jobs, or any live/paper trading loops unless Patrick explicitly decides to reopen the project.

If reopened later, do not jump straight into troubleshooting. First create a short restart plan that answers:

1. What specific problem is worth solving?
2. What evidence shows the project can produce income or useful trading edge?
3. What token/credit budget is acceptable?
4. What stop condition prevents another open-ended debugging loop?
5. Which cron jobs should be resumed, if any?

## Current safe state

- Live trading remains unsupported.
- Scheduled paper runs are paused.
- Scheduled performance report pushes are paused.
- Existing reports and code are kept for reference only.
- This repo should be treated as archived unless the project is explicitly reopened.
