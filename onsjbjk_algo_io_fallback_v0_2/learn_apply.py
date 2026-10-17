"""Learning (doc 04 section 14): learn new algorithms from labelled Python files as branches of the tree at the
node their logic reaches (prolog/learn_tree.pl), holding where a file there has their input->output
behaviour; apply them at a test file's deepest node (prolog/learn_apply.pl). Deterministic; nothing is run."""
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
    """Write the learned branches from {file: label or None (negative)}; {file: number of tree nodes}."""
    count, lines = {}, []
    for path, label in sorted(labelled.items()):
        try:
            found = learn_facts.nodes(path)
        except ERRORS:
            found = []
        count[path] = len(found)
        lines.append(f"train({'none' if label is None else label}, '{path.name}').")
        lines += [f"reach('{path.name}', {prolog_path(n)})." for n in found]
    with tempfile.TemporaryDirectory(prefix='v02_learn_') as td:
        f = Path(td) / 'reach.pl'
        f.write_text(':- discontiguous train/2, reach/2.\n' + '\n'.join(lines) + '\n', encoding='utf-8')
        learn_facts.env_run.swipl('learn_main', [PROLOG / 'learn_tree.pl'], [str(f), str(rules)], timeout=3600)
    return count


def apply(path: Path, rules: Path = RULES, io_labels=()):
    """([tree nodes of the file], [(node, label, rule)] of the learned branches holding at its deepest node,
    {labels with a learned branch there}, {the normal process's branches there}); io_labels: the training
    labels whose behaviour the file has."""
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return [], [], set(), set()
    with tempfile.TemporaryDirectory(prefix='v02_io_') as td:
        io = Path(td) / 'io.pl'
        io.write_text(''.join(f"io_equal('{lab}').\n" for lab in sorted(io_labels)), encoding='utf-8')
        lines = learn_facts.swipl_facts('learn_apply_main', PROLOG / 'learn_apply.pl', kind, text, str(rules), str(io))
    nodes = [line.split('|', 1)[1] for line in lines if line.startswith('NODE|')]
    branch_at = {line.split('|')[2] for line in lines if line.startswith('BRANCH_AT|')}
    normal = {line.split('|')[2] for line in lines if line.startswith('NORMAL|')}
    return nodes, [tuple(line.split('|')[1:]) for line in lines if line.startswith('LEARNED|')], branch_at, normal
