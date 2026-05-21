#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LEDGER="$ROOT_DIR/data/paper_trades.jsonl"
MAX_AGE_MINUTES=60
PROCESS_PATTERN="scripts/run_paper.sh|scripts/paper_trade.py"
STRICT_EXIT=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ledger)
      LEDGER="$2"
      shift 2
      ;;
    --max-age-minutes)
      MAX_AGE_MINUTES="$2"
      shift 2
      ;;
    --process-pattern)
      PROCESS_PATTERN="$2"
      shift 2
      ;;
    --strict-exit)
      STRICT_EXIT=true
      shift
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

now_epoch="$(date +%s)"
issues=()

if [[ ! -f "$LEDGER" ]]; then
  issues+=("ledger missing: $LEDGER")
else
  ledger_epoch="$(stat -c %Y "$LEDGER")"
  age_seconds=$((now_epoch - ledger_epoch))
  max_age_seconds=$((MAX_AGE_MINUTES * 60))
  if (( age_seconds >= max_age_seconds )); then
    age_minutes=$((age_seconds / 60))
    issues+=("ledger stale: ${age_minutes}m old, threshold ${MAX_AGE_MINUTES}m, path $LEDGER")
  fi
fi

runner_found=false
while read -r pid cmd; do
  [[ -z "${pid:-}" ]] && continue
  if [[ "$pid" == "$$" || "$cmd" == *"paper_watchdog.sh"* ]]; then
    continue
  fi
  runner_found=true
  break
done < <(pgrep -af "$PROCESS_PATTERN" || true)

if [[ "$runner_found" != "true" ]]; then
  issues+=("runner process missing: pattern $PROCESS_PATTERN")
fi

if (( ${#issues[@]} > 0 )); then
  echo "Weatherbot paper runner watchdog alert"
  printf -- '- %s\n' "${issues[@]}"
  if [[ "$STRICT_EXIT" == "true" ]]; then
    exit 1
  fi
  exit 0
fi

if [[ "$VERBOSE" == "true" ]]; then
  echo "Weatherbot paper runner watchdog OK"
fi
exit 0
