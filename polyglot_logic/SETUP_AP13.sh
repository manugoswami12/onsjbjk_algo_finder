#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m pip install -r requirements.txt
python3 tools/cli.py prefetch
mkdir -p store
[ -d store/TheAlgorithms_Python ] || git clone -q https://github.com/TheAlgorithms/Python.git store/TheAlgorithms_Python
git -C store/TheAlgorithms_Python checkout -q e1a2a8b0
python3 tools/rosetta_eval.py --store store --rosetta store/rosetta
