#!/usr/bin/env bash
# Compatibility wrapper for Hermes cron jobs that reference this stable script name.
# Delegates to the maintained daily report push script.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/daily_report_push.sh" "$@"
