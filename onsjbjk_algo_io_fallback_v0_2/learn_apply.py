"""Learning (doc 04): learn new algorithms from labelled files (anti-unified DCGs, prolog/learn_dcg.pl) and
apply them to unseen files of any language (prolog/learn_apply.pl). Deterministic; nothing is run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import learn_facts

PROLOG = Path(__file__).resolve().parent / 'prolog'
RULES = PROLOG / 'learned_rules.pl'


def learn(labelled: dict[Path, str | None], rules: Path = RULES) -> dict[Path, int]:
    """Write learned rules for every label from {file: label or None (negative)}; {file: streams}."""
    count, lines = {}, []
    for path, label in sorted(labelled.items()):
        try:
            found = learn_facts.streams(path)
        except (RuntimeError, OSError, ValueError, UnicodeDecodeError):
            found = []
        count[path] = len(found)
        lab = 'none' if label is None else label
        lines += [f"train({lab}, '{path.name}', {tokens})." for _, tokens in found]
    with tempfile.TemporaryDirectory(prefix='v02_learn_') as td:
        f = Path(td) / 'streams.pl'
        f.write_text(':- discontiguous train/3.\n' + '\n'.join(lines) + '\n', encoding='utf-8')
        learn_facts.env_run.swipl('learn_main', [PROLOG / 'learn_dcg.pl'], [str(f), str(rules)], timeout=3600)
    return count


def apply(path: Path, rules: Path = RULES) -> list[tuple[str, str, str]]:
    """[(function, label, rule)] of the learned rules that parse the file's root functions."""
    text = learn_facts.facts(path)
    if not text.strip():
        return []
    with tempfile.TemporaryDirectory(prefix='v02_apply_') as td:
        f = Path(td) / 'facts.pl'
        f.write_text(text, encoding='utf-8')
        lines = learn_facts.env_run.swipl('learn_apply_main', [PROLOG / 'learn_apply.pl'], [str(f), str(rules)])
    return [tuple(line.split('|')[1:]) for line in lines if line.startswith('LEARNED|')]
