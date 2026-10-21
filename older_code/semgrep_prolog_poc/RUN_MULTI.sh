#!/usr/bin/env bash
set -eu
cd "$(dirname "$0")"
python3 tools/run_demo.py --multi "$@"
