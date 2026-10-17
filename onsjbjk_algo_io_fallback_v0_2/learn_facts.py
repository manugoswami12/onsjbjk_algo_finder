"""Learning (doc 04), environment step: the neutral facts of a file in any language, and its tree nodes and
logic-flow token streams (prolog/tree_main.pl). Nothing is run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import compare_learners
import ecl_compile
import ecl_facts
import ecl_logic

compare_learners._ap13()
import cli  # AP13: tree-sitter lowerers (Python, C, Haskell, ...)
import env_run

PROLOG = Path(__file__).resolve().parent / 'prolog'
FLOW_MAIN = PROLOG / 'flow_main.pl'
TREE_MAIN = PROLOG / 'tree_main.pl'


def facts(path: Path) -> str:
    """Neutral facts: the ECL export for Common Lisp (facts after ecl_norm), AP13 cli otherwise."""
    if path.suffix == '.lisp':
        return ecl_logic.trace(path)[1]
    return cli.facts_text(path)[1]


def tree_facts(path: Path) -> tuple[str, str]:
    """(kind, facts) as the normal process loads them: ECL facts for Lisp (tree_main normalises them as
    ecl_main.pl does), AP13 lowerer facts otherwise."""
    if path.suffix == '.lisp':
        units = ecl_compile.ecl_units(path)
        return 'lisp', ecl_facts.facts_of(units) if any(units) else ''
    return 'ap13', cli.facts_text(path)[1]


def swipl_facts(goal: str, program: Path, kind: str, text: str, *args: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix='v02_tree_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text(text, encoding='utf-8')
        return env_run.swipl(goal, [program], [str(f), kind, *args])


def tree(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """([deepest family paths 'a>b>c'], [(root function, tokens)]) of the file; tokens stay Prolog text."""
    kind, text = tree_facts(path)
    if not text.strip():
        return [], []
    nodes, out = [], []
    for line in swipl_facts('tree_main', TREE_MAIN, kind, text):
        tag, name, rest = line.split('|', 2)
        if tag == 'NODE':
            nodes.append(rest)
        elif tag == 'STREAM':
            out.append((name, rest))
    return sorted(set(nodes)), out


def streams(path: Path) -> list[tuple[str, list]]:
    """[(root function, tokens)] of the file (round 2: the facts as they are, prolog/flow_main.pl)."""
    text = facts(path)
    if not text.strip():
        return []
    with tempfile.TemporaryDirectory(prefix='v02_flow_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text(text, encoding='utf-8')
        lines = env_run.swipl('flow_main', [FLOW_MAIN], [str(f)])
    out = []
    for line in lines:
        tag, name, tokens = line.split('|', 2)
        if tag == 'STREAM':
            out.append((name, tokens))
    return out
