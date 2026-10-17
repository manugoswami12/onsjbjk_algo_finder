"""Learning (doc 04), environment step: the neutral facts of a file in any language, and the logic-flow
token streams of its root functions (prolog/flow_main.pl). Nothing is run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import compare_learners
import ecl_logic

compare_learners._ap13()
import cli  # AP13: tree-sitter lowerers (Python, C, Haskell, ...)
import env_run

FLOW_MAIN = Path(__file__).resolve().parent / 'prolog' / 'flow_main.pl'


def facts(path: Path) -> str:
    """Neutral facts: the ECL export for Common Lisp (facts after ecl_norm), AP13 cli otherwise."""
    if path.suffix == '.lisp':
        return ecl_logic.trace(path)[1]
    return cli.facts_text(path)[1]


def streams(path: Path) -> list[tuple[str, list]]:
    """[(root function, tokens)] of the file; the tokens stay Prolog text (re-read by Prolog only)."""
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
