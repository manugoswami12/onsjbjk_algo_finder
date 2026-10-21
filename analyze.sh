#!/bin/sh
# Name the algorithm of a source file: ./analyze.sh path/to/program.py   (also .c, .lisp, .hs; several files allowed)
# Runs the whole pipeline (analyze.py). The first run learns TheAlgorithms once and keeps it in .cache/.
HERE=$(cd "$(dirname "$0")" && pwd)
if [ $# -eq 0 ]; then echo "usage: $0 FILE [FILE ...]   (Python .py, C .c, Common Lisp .lisp, Haskell .hs)"; exit 2; fi
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then echo "Python is not installed (see README section 1)"; exit 1; fi
if ! command -v swipl >/dev/null 2>&1; then echo "SWI-Prolog (swipl) is not installed or not on PATH (see README section 1)"; exit 1; fi
FILES=""
for f in "$@"; do
  case "$f" in /*) FILES="$FILES|$f" ;; *) FILES="$FILES|$(pwd)/$f" ;; esac
done
cd "$HERE" || exit 1
OLDIFS=$IFS; IFS='|'; set -- ${FILES#|}; IFS=$OLDIFS
PYTHONPATH=. exec "$PY" analyze.py "$@"
