"""Helper for writing file rules by hand (doc 04 section 17.5): which components of a label's files no other label of
TheAlgorithms/Python has.

usage: python ta_distinct.py CORPUS --index            abstracted relations of every corpus file -> benchmark/ta_signatures.json
       python ta_distinct.py CORPUS LABEL [LABEL ...]   the label's components found in no other label (smallest first)
       python ta_distinct.py CORPUS --propose LABEL ...  candidate hand_specific/2 clauses covering every file of the label
A component is a statement's relation with its variable names and the file's own function names abstracted away
(prolog/ta_signature.pl), so it is the same component in every spelling. The rule is then written by hand in
prolog/ta_file_rules.pl from one or two of them.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import learn_facts
import ta_corpus
from ta_corpus import ROOT

PROGRAM = ROOT / 'prolog' / 'ta_signature.pl'
INDEX = ROOT / 'benchmark' / 'ta_signatures.json'
ERRORS = (RuntimeError, OSError, ValueError, UnicodeDecodeError)


def signatures(path: Path) -> list[str]:
    kind, text = learn_facts.tree_facts(path)
    if not text.strip():
        return []
    return sorted({line.split('|', 1)[1] for line in learn_facts.swipl_facts('signature_main', PROGRAM, kind, text)
                   if line.startswith('SIG|')})


def index(corpus: Path, workers: int = 4):
    labels = ta_corpus.files(corpus)

    def one(rel):
        try:
            return rel, signatures(corpus / rel)
        except ERRORS:
            return rel, []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        out = dict(pool.map(one, sorted(labels)))
    INDEX.write_text(json.dumps(out, indent=0, sort_keys=True) + '\n', encoding='utf-8')
    print(f'{len(out)} files -> {INDEX}')


def distinct(corpus: Path, label: str, top: int = 12) -> list[tuple[str, list[str]]]:
    """[(component, files of the label having it)] for the components no file of another label has."""
    labels = ta_corpus.files(corpus)
    sigs = json.loads(INDEX.read_text(encoding='utf-8'))
    owners = defaultdict(set)
    for rel, ss in sigs.items():
        for s in ss:
            owners[s].add(labels[rel])
    mine = [rel for rel, lab in labels.items() if lab == label]
    found = defaultdict(list)
    for rel in mine:
        for s in sigs.get(rel, []):
            if owners[s] == {label}:
                found[s].append(rel)
    return sorted(found.items(), key=lambda kv: (-len(kv[1]), len(kv[0])))[:top]


TRIVIAL = ('var(v)', 'var(v)-other(string)', 'var(v)-var(v)', 'var(v)-int(0)', 'var(v)-int(1)', 'var(v)-list([])')


def structural(s: str) -> bool:
    """A component worth naming: an operation, a call or an element, not a bare constant assignment."""
    return s not in TRIVIAL and any(k in s for k in ('op(', 'call(', 'elem(', 'map(', 'filter(', 'concat(', 'cons('))


def cover(corpus: Path, label: str):
    """[(component, ...)] whose union covers every file of the label: single components owned by the label first
    (structural ones preferred), else a pair of components that together occur only in the label's files."""
    labels = ta_corpus.files(corpus)
    sigs = json.loads(INDEX.read_text(encoding='utf-8'))
    owners = defaultdict(set)
    for rel, ss in sigs.items():
        for s in ss:
            owners[s].add(labels[rel])
    files_of = defaultdict(set)
    for rel, ss in sigs.items():
        for s in ss:
            files_of[s].add(rel)
    mine = [rel for rel, lab in labels.items() if lab == label]
    chosen, left = [], set(mine)
    while left:
        best = None
        for rel in sorted(left):
            for s in sigs.get(rel, []):
                if owners[s] == {label}:
                    key = (len(files_of[s] & left), structural(s), -abs(len(s) - 60))
                    if best is None or key > best[0]:
                        best = (key, (s,), files_of[s] & left)
        if best is None:                              # no single component: a pair present only in the label's files
            rel = sorted(left)[0]
            ss = [s for s in sigs.get(rel, []) if structural(s)] or sigs.get(rel, [])
            for i, a in enumerate(ss):
                for b in ss[i + 1:]:
                    both = files_of[a] & files_of[b]
                    if {labels[r] for r in both} == {label}:
                        key = (len(both & left), -abs(len(a) + len(b) - 120))
                        if best is None or key > best[0]:
                            best = (key, (a, b), both & left)
        if best is None:
            return chosen, sorted(left)                # identical to another label's file in every component pair
        chosen.append(best[1])
        left -= best[2]
    return chosen, []


def propose(corpus: Path, label: str) -> str:
    """Candidate clauses of hand_specific/2 for the label (to be reviewed before they go in ta_file_rules.pl)."""
    chosen, left = cover(corpus, label)
    out = [f"% {label}"]
    for comps in chosen:
        body = ', '.join(f'has_rel(F, {c})' for c in comps)
        out.append(f"hand_specific(F, '{label}') :- {body}.")
    if left:
        out.append(f"% no component of {', '.join(left)} separates it from another label (identical logic)")
    return '\n'.join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('corpus', type=Path)
    p.add_argument('labels', nargs='*')
    p.add_argument('--index', action='store_true')
    p.add_argument('--propose', action='store_true', help='candidate file-rule clauses for the labels')
    a = p.parse_args()
    if a.index:
        index(a.corpus)
    if a.propose:
        for lab in a.labels:
            print(propose(a.corpus, lab))
        return
    for lab in a.labels:
        print(f'== {lab}')
        for s, rels in distinct(a.corpus, lab):
            print(f'  [{len(rels)}] {s[:220]}')


if __name__ == '__main__':
    main()
