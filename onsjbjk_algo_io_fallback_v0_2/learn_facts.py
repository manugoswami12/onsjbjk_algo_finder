"""Learning (doc 04 section 14), environment step: the facts of a file as the normal process loads them, and
its tree nodes (prolog/tree_main.pl). Nothing is run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import compare_learners
import ecl_compile
import ecl_facts

compare_learners._ap13()
import cli  # AP13: tree-sitter lowerers (Python, C, Haskell, ...)
import env_run

TREE_MAIN = Path(__file__).resolve().parent / 'prolog' / 'tree_main.pl'


def tree_facts(path: Path) -> tuple[str, str]:
    """(kind, facts): ECL facts for Lisp (tree_main normalises them as ecl_main.pl does), AP13 lowerer facts
    otherwise."""
    if path.suffix == '.lisp':
        units = ecl_compile.ecl_units(path)
        return 'lisp', ecl_facts.facts_of(units) if any(units) else ''
    return 'ap13', cli.facts_text(path)[1]


def swipl_facts(goal: str, program: Path, kind: str, text: str, *args: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix='v02_tree_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text(text, encoding='utf-8')
        return env_run.swipl(goal, [program], [str(f), kind, *args])


def nodes(path: Path) -> list[str]:
    """The deepest family paths 'a>b>c' of the file's functions (the normal process's tree)."""
    kind, text = tree_facts(path)
    if not text.strip():
        return []
    return sorted({line.split('|', 2)[2] for line in swipl_facts('tree_main', TREE_MAIN, kind, text)
                   if line.startswith('NODE|')})
