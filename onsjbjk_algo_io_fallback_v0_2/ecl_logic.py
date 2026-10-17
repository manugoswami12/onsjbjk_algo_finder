"""Prolog step: ECL facts -> prolog/ecl_main.pl (ecl_norm.pl, then the unchanged AP13 v3 roles and
families, then family_to_v02.pl) -> the v0.2 branch of every Lisp function. Never runs the program."""
from __future__ import annotations

import tempfile
from pathlib import Path

import compare_learners
import ecl_compile
import ecl_facts

compare_learners._ap13()
import env_run  # AP13 tools: swipl, stderr = failure

ECL_MAIN = Path(__file__).resolve().parent / 'prolog' / 'ecl_main.pl'
NOCODE = '<nocode>'


def run(goal: str, facts: str) -> list[str]:
    with tempfile.TemporaryDirectory(prefix='v02_eclp_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text(facts, encoding='utf-8')
        return env_run.swipl(goal, [ECL_MAIN], [str(f)])


def families(path: Path) -> dict[str, list[tuple[str, str]]]:
    """{Lisp function name: [(family path, v0.2 branch or 'none')]} for every defun of the file."""
    return trace(path)[0]


def trace(path: Path) -> tuple[dict[str, list[tuple[str, str]]], str]:
    """The normal answer and its output for the fallback (ecl_export: facts after ecl_norm + answers)."""
    out: dict[str, list[tuple[str, str]]] = {}
    units = ecl_compile.ecl_units(path)
    if not any(units):
        return out, ''
    facts = ecl_facts.facts_of(units)
    export = '\n'.join(run('ecl_export', facts)) + '\n'
    for line in run('ecl_main', facts):
        if line == 'NOCODE':                      # no algorithm of its own in the file (ecl_main.pl)
            out[NOCODE] = []
            continue
        tag, _, name, fam, branch = line.split('|')
        if tag == 'FAMILY':
            out.setdefault(name.replace('_', '-'), []).append((fam, branch))
    return out, export
