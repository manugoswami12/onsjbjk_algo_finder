"""Library-name fallback (doc 04 section 18.1), kept separate from the pipeline: a program whose computation is one
library call (math.factorial(n), sorted(xs), (gcd a b), qsort) is named by the library's algorithm, from the table in
prolog/library_names.pl. Nothing runs: the rule reads AP13's normal form.
"""
from __future__ import annotations

from pathlib import Path

import learn_facts
from ta_corpus import ROOT

PROGRAM = ROOT / 'prolog' / 'library_names.pl'
ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError, RecursionError, SyntaxError)
LANG = {'.py': 'python', '.hs': 'haskell', '.c': 'c', '.lisp': 'lisp'}


def answers(path: Path) -> dict[str, tuple[str, str]]:
    """{function: (library name, algorithm)} of the file's functions (or script) that are one library call."""
    lang = LANG.get(path.suffix)
    if lang is None:
        return {}
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return {}
    out = {}
    for line in learn_facts.swipl_facts('library_main', PROGRAM, kind, text, lang):
        if line.startswith('LIB|'):
            _, fn, name, alg = line.split('|')
            out[fn] = (name, alg)
    return out


def algorithm(path: Path) -> str | None:
    """The one algorithm the file's library calls name, else None (none, or two different ones)."""
    algs = {a for _, a in answers(path).values()}
    return min(algs) if len(algs) == 1 else None
