#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
export WEATHERBOT_ONCE=true
export WEATHERBOT_COMMAND="${WEATHERBOT_COMMAND:-}"
exec scripts/run_paper.sh
