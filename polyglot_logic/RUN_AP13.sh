#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
command -v swipl >/dev/null 2>&1 || { echo "AP13_ERROR: swipl not on PATH"; exit 2; }
exec python3 tools/cli.py "$@"
