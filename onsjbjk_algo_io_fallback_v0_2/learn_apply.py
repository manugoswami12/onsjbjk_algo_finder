"""Learning (doc 04 section 8): learn new algorithms from labelled Python files as new branches of the tree,
at the node their logic reaches (prolog/learn_dcg.pl), and apply them to unseen files of any language,
deepest reached node first (prolog/learn_apply.pl). Deterministic; nothing is run."""
from __future__ import annotations

import tempfile
from pathlib import Path

import learn_facts

PROLOG = Path(__file__).resolve().parent / 'prolog'
RULES = PROLOG / 'learned_tree.pl'
ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError)


def prolog_path(node: str) -> str:
    return '[' + ','.join(f"'{p}'" for p in node.split('>') if p) + ']'


def learn(labelled: dict[Path, str | None], rules: Path = RULES) -> dict[Path, int]:
    """Write learned branches for every label from {file: label or None (negative)}; {file: streams}."""
    count, lines = {}, []
    for path, label in sorted(labelled.items()):
        try:
            nodes, found = learn_facts.tree(path)
        except ERRORS:
            nodes, found = [], []
        count[path] = len(found)
        lab = 'none' if label is None else label
        lines += [f"train({lab}, '{path.name}', {tokens})." for _, tokens in found]
        lines += [f"reach('{path.name}', {prolog_path(n)})." for n in nodes]
    with tempfile.TemporaryDirectory(prefix='v02_learn_') as td:
        f = Path(td) / 'streams.pl'
        f.write_text(':- discontiguous train/3, reach/2.\n' + '\n'.join(lines) + '\n', encoding='utf-8')
        learn_facts.env_run.swipl('learn_main', [PROLOG / 'learn_dcg.pl'], [str(f), str(rules)], timeout=3600)
    return count


def apply(path: Path, rules: Path = RULES) -> tuple[list[str], list[tuple[str, str, str]]]:
    """([tree nodes of the file], [(node, label, rule)] of the learned branches that hold, deepest node first)."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return [], []
    lines = learn_facts.swipl_facts('learn_apply_main', PROLOG / 'learn_apply.pl', kind, text, str(rules))
    nodes = [line.split('|', 1)[1] for line in lines if line.startswith('NODE|')]
    return nodes, [tuple(line.split('|')[1:]) for line in lines if line.startswith('LEARNED|')]
