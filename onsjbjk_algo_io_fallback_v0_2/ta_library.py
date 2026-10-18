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


def answers(path: Path) -> tuple[dict[str, tuple[str, str]], set[str]]:
    """({function: (library name, algorithm)} of the file's functions (or script) that are one library call,
    the names of the file's other functions, leaving out those passed to the call)."""
    lang = LANG.get(path.suffix)
    if lang is None:
        return {}, set()
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return {}, set()
    out, funcs, parts = {}, set(), set()
    for line in learn_facts.swipl_facts('library_main', PROGRAM, kind, text, lang):
        if line.startswith('LIB|'):
            _, fn, name, alg = line.split('|')
            out[fn] = (name, alg)
        elif line.startswith('FUNC|'):
            funcs.add(line.split('|', 1)[1])
        elif line.startswith('PART|'):              # passed to the call: part of it, not other code
            parts.add(line.split('|', 1)[1])
    return out, funcs - parts


def file_algorithm(found: dict[str, tuple[str, str]], funcs: set[str]) -> str | None:
    """The file's algorithm: one algorithm named, and every function of the file is a library call (a file with other
    code of its own, such as closest_pair_of_points with a sorted() helper, is that other code's algorithm). A function
    nested in a library-call function (natural_sort's key function) is part of that call."""
    algs = {a for _, a in found.values()}
    rest = {f for f in funcs if f not in found and not any(f.startswith(g + '.') for g in found)}
    return min(algs) if len(algs) == 1 and not rest else None


def algorithm(path: Path) -> str | None:
    return file_algorithm(*answers(path))
