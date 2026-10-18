"""TheAlgorithms/Python as a learning corpus (doc 04 section 17): one label per file, its stem.

  label(rel)   sorts/bubble_sort.py -> bubble_sort (project_euler/problem_001/sol1.py -> problem_001); package and
               test files carry no label
  group(lab)   the labels that name one algorithm: the files AP13's frozen key (polyglot_logic/benchmark/
               rosetta_truth.json) maps to one Rosetta task share a group (bubble_sort, bubble_sort_recursive);
               a numbered variant X_2 / X2 of a label X is in X's group; any other label is its own group
  BUILT        the built branches of the tree that name one algorithm, with the Rosetta task they are; the other
               normal branches (comparison_driven_reordering, euclid_like, ...) name a family, not an algorithm
The corpus is read only, never edited; the pinned commit is AP13's (e1a2a8b0).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ROSETTA_TRUTH = ROOT.parent / 'polyglot_logic' / 'benchmark' / 'rosetta_truth.json'
COMMIT = 'e1a2a8b016001309a73d5fec4818c35cca139795'
NOT_ALGORITHM = {'__init__', 'conftest', 'setup'}
BUILT = {'ackermann': 'Ackermann-function', 'knapsack_01': 'Knapsack-problem-0-1', 'caesar_cipher': 'Caesar-cipher',
         'matrix_multiplication': 'Matrix-multiplication', 'run_length_encoding': 'Run-length-encoding',
         'josephus': 'Josephus-problem', 'n_queens': 'N-queens-problem', 'leap_year': 'Leap-year',
         'lcs': 'Longest-common-subsequence', 'levenshtein': 'Levenshtein-distance',
         'roman_encode': 'Roman-numerals-Encode', 'towers_of_hanoi': 'Towers-of-Hanoi'}


def label(rel: str) -> str | None:
    stem = Path(rel).stem
    if stem in NOT_ALGORITHM or stem.startswith('test_') or stem.endswith('_test'):
        return None
    if re.fullmatch(r'sol\d+', stem):                 # project_euler/problem_001/sol1.py: the problem is the label
        return Path(rel).parent.name
    return stem


def files(corpus: Path) -> dict[str, str]:
    """{relative path: label} of the corpus' Python files that carry a label."""
    out = {}
    for p in sorted(corpus.rglob('*.py')):
        rel = p.relative_to(corpus).as_posix()
        if '.git' in p.parts or rel.startswith(('.github/', 'scripts/')):
            continue
        lab = label(rel)
        if lab:
            out[rel] = lab
    return out


def tasks() -> dict[str, list[str]]:
    """{Rosetta task: [corpus files]} of AP13's frozen key."""
    return json.loads(ROSETTA_TRUTH.read_text(encoding='utf-8'))['tasks']


def groups(labels=()) -> dict[str, str]:
    """{label: its group name}: the Rosetta task for the mapped files' labels; built branch names too; a numbered
    variant X_2 / X2 of a label X (TheAlgorithms numbers the variants of one algorithm: dijkstra_2, prims2) is X's."""
    out = {label(rel): task for task, rels in tasks().items() for rel in rels if label(rel)}
    out.update(BUILT)
    names = set(labels)
    for lab in sorted(names):
        m = re.fullmatch(r'(.+?)_?\d+', lab)
        if m and m.group(1) in names and lab not in out:
            out[lab] = out.get(m.group(1), m.group(1))
    return out


def group(lab: str, gs: dict[str, str]) -> str:
    return gs.get(lab, lab)
