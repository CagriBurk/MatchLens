#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p data/logs
exec 9>data/logs/update.lock
flock -n 9 || exit 0
{
  echo "=== $(date -Is)"
  .venv/bin/python -W ignore -m matchlens.update
} >> data/logs/update.log 2>&1
