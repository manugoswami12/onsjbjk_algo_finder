"""The fallback, separate from the normal process: when the normal process gives a unit no v0.2
branch, prolog/fallback_main.pl reads the normal process's own output (ecl_logic.trace: the facts
after ecl_norm and its answers), follows the links between the file's functions and answers by the
DCG pattern rules of prolog/fallback_rules.pl. Nothing is recompiled and nothing is run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import ecl_logic

FALLBACK_MAIN = Path(__file__).resolve().parent / 'prolog' / 'fallback_main.pl'


def answers(export: str) -> dict[str, list[tuple[str, str]]]:
    """{Lisp function name: [(v0.2 branch, rule)]} from the earlier output."""
    out: dict[str, list[tuple[str, str]]] = {}
    if not export.strip():
        return out
    with tempfile.TemporaryDirectory(prefix='v02_fb_') as td:
        f = Path(td) / 'export.pl'
        f.write_text(export, encoding='utf-8')
        lines = ecl_logic.env_run.swipl('fallback_main', [FALLBACK_MAIN], [str(f)])
    for line in lines:
        tag, _, name, branch, rule = line.split('|')
        if tag == 'FALLBACK':
            out.setdefault(name.replace('_', '-'), []).append((branch, rule))
    return out
